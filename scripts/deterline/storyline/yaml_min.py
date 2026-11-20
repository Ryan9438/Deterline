"""yaml_min——安全 YAML 子集解析器（12 计划 C2）。

stdlib-only；只支持确定性子集，其余显式拒绝（fail-closed）：
注释（引号内 # 不算）、块映射、块序列、标量（引号串/int/bool/null/裸词）。
拒绝：tab 缩进、锚点 &、别名 *、标签 !、多文档 ---、流式 {} []、重复键。
"""

import re

_INT = re.compile(r"^-?\d+$")


class YamlMinError(ValueError):
    """解析拒绝（fail-closed）——消息带行号。"""


def _strip_comment(line):
    """去行注释：# 在引号外才算注释。"""
    in_s = in_d = False
    for i, ch in enumerate(line):
        if ch == "'" and not in_s:
            in_s = not in_s
        elif ch == '"' and not in_s:
            in_d = not in_d
        elif ch == "#" and not in_s and not in_d:
            return line[:i].rstrip()
    return line.rstrip()


def _parse_scalar(raw):
    """标量：引号串 / int / bool / null / 裸词字符串（不展开）。"""
    raw = raw.strip()
    if raw == "" or raw in ("~", "null", "Null", "NULL"):
        return None
    if raw in ("true", "True"):
        return True
    if raw in ("false", "False"):
        return False
    if _INT.match(raw):
        return int(raw)
    if len(raw) >= 2 and raw.startswith("'") and raw.endswith("'"):
        return raw[1:-1].replace("''", "'")
    if len(raw) >= 2 and raw.startswith('"') and raw.endswith('"'):
        return raw[1:-1]
    return raw


def _check_forbidden(line, line_no):
    """fail-closed：子集外语法一律拒绝（消息带行号）。"""
    body = line.lstrip()
    # 值级锚点/别名：键后的值以 & 或 * 开头（含裸值与引号前的位置）
    after_key = line.split(":", 1)
    value_part = after_key[1].strip() if len(after_key) == 2 else ""
    if value_part.startswith("&") or body.startswith("&"):
        raise YamlMinError(f"YAML 第 {line_no} 行: 锚点（&）不支持")
    if value_part.startswith("*") or body.startswith("*"):
        raise YamlMinError(f"YAML 第 {line_no} 行: 别名（*）不支持")
    if body.startswith("!"):
        raise YamlMinError(f"YAML 第 {line_no} 行: 标签不支持")
    if body.startswith("---"):
        raise YamlMinError(f"YAML 第 {line_no} 行: 多文档（---）不支持")
    if "{" in body or "}" in body:
        raise YamlMinError(f"YAML 第 {line_no} 行: 流式映射不支持")
    if "[" in body or "]" in body:
        raise YamlMinError(f"YAML 第 {line_no} 行: 流式序列不支持")
    indent_part = line[: len(line) - len(line.lstrip())]
    if "\t" in indent_part:
        raise YamlMinError(f"YAML 第 {line_no} 行: tab 缩进不支持")


def _split_map(content, line_no):
    """把 'key: value' 内容切成 (key, rest)；非映射行返回 None。"""
    m = re.match(r"^([^:]+):( |$)", content)
    if not m:
        return None
    key = m.group(1).strip()
    if not key:
        raise YamlMinError(f"YAML 第 {line_no} 行: 空键")
    return key, content[m.end():].strip()


def parse(text):
    """解析子集文本 → dict/list/标量。栈式构造，重复键 fail-closed。"""
    items = []          # (indent, kind, payload, line_no)
    for no, raw in enumerate(text.splitlines(), 1):
        if not raw.strip():
            continue
        _check_forbidden(raw, no)
        body = _strip_comment(raw).rstrip()
        if not body.strip():
            continue
        indent = len(body) - len(body.lstrip(" "))
        content = body.strip()
        if content.startswith("- ") or content == "-":
            payload = content[2:].strip() if len(content) > 1 else ""
            items.append((indent, "seq", payload, no))
        else:
            split = _split_map(content, no)
            if split is None:
                items.append((indent, "scalar", content, no))
            else:
                items.append((indent, "map", split, no))
    if not items:
        return {}

    # 栈式构造：栈帧 = [indent, container]
    root = None
    stack = []          # 每帧: {"indent", "kind", "container", "key"}
    for indent, kind, payload, line_no in items:
        if kind == "scalar":
            raise YamlMinError(
                f"YAML 第 {line_no} 行: 顶层裸标量不支持（文档必须是映射）")
        # 回退栈：只弹比当前缩进更深的帧（同缩进 = 兄弟层，保留）
        while stack and indent < stack[-1]["indent"]:
            stack.pop()
        if not stack:
            if root is not None:
                raise YamlMinError(
                    f"YAML 第 {line_no} 行: 顶层出现第二个文档结构")
            if kind == "seq":
                raise YamlMinError(
                    f"YAML 第 {line_no} 行: 顶层必须是映射（storyline 合同）")
            root = {}
            stack.append({"indent": indent, "kind": "map",
                          "container": root, "key": None})
        frame = stack[-1]
        if indent > frame["indent"]:
            # 子块：map 帧挂到待填键；序列嵌套块 v1 拒绝
            if frame["kind"] == "map":
                if frame["key"] is None:
                    raise YamlMinError(f"YAML 第 {line_no} 行: 子块缺父键")
                child = [] if kind == "seq" else {}
                frame["container"][frame["key"]] = child
                stack.append({"indent": indent,
                              "kind": "seq" if kind == "seq" else "map",
                              "container": child, "key": None})
                frame = stack[-1]
            else:
                raise YamlMinError(
                    f"YAML 第 {line_no} 行: 序列内映射不支持（v1 标量序列）")
        if kind == "map":
            key, rest = payload
            if key in frame["container"]:
                raise YamlMinError(f"YAML 第 {line_no} 行: 重复键 '{key}'")
            if rest:
                frame["container"][key] = _parse_scalar(rest)
            else:
                frame["container"][key] = {}   # 占位：子块填充或 null
            frame["key"] = key
        else:  # seq（v1：仅标量序列）
            if frame["kind"] != "seq":
                # R13 P2-1：`a:\n- x` 同缩进序列落到 map 帧——曾 AttributeError
                # 裸栈逃逸；按合同 fail-closed 显式拒绝
                raise YamlMinError(
                    f"YAML 第 {line_no} 行: 映射键下不允许同缩进序列项"
                    "（序列须更深一级缩进）")
            if not payload:
                raise YamlMinError(
                    f"YAML 第 {line_no} 行: 序列项空载荷/嵌套块不支持")
            if _split_map(payload, line_no) is not None:
                raise YamlMinError(
                    f"YAML 第 {line_no} 行: 序列内映射不支持（v1 标量序列）")
            frame["container"].append(_parse_scalar(payload))
    # 清理占位：空 dict 若无子块填入 → null
    def _cleanup(node):
        if isinstance(node, dict):
            for k in list(node):
                v = node[k]
                if isinstance(v, dict):
                    if not v:
                        node[k] = None
                    else:
                        _cleanup(v)
        elif isinstance(node, list):
            for i, v in enumerate(node):
                if isinstance(v, dict):
                    if not v:
                        node[i] = None
                    else:
                        _cleanup(v)
    _cleanup(root)
    return root
