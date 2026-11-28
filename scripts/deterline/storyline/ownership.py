"""双补丁组合：资源所有权与合并计划（16 号计划包 26/27）。

从 v2 计划提取资源所有权声明（房间实例槽/对象事件脚本/字符串键/flag/
字体配置），两计划间分类：
- **mergeable**：可加性资源（同一房间新增不同实例等）——顺序无关；
- **shared-script**：双方都会改写的共享可变资源（同对象 Step/Create/
  Alarm、门模板脚本、字体管线脚本、对象变量）——只能在**同一合成构建**
  内合并（顺序拼接两份追加会叠写；合成构建 = 一次生成、一次闸门）；
- **exclusive**：同一资源被两补丁声明（同 text key / 同 flag / 同
  patch_id / 同 cjk 载体不兼容）——拒绝，须改定义。

合成定义（compose_definitions）：两份 v2 定义 → 单一合成定义
（id/别名加 `<patch>__` 前缀防跨定义碰撞；执行序 = patch_id 字典序内的
各自声明序——**输入顺序无关**（包 27 验收：调换输入产生同一计划）；
cjk 期望值不一致 → 拒绝（同一构建的 typer/字体管线只有一套））。
"""

import copy

__all__ = ["extract_ownership", "compare_ownership", "compose_definitions"]


def _pkg():
    """运行时取本包模块（跨模块引用一律运行时属性查找——包纪律，同 commands）。"""
    import sys as _sys
    return _sys.modules[__package__]


def _claim(kind: str, ident: str, cls: str, note: str = "") -> dict:
    return {"kind": kind, "id": ident, "class": cls, "note": note}


def extract_ownership(plan: dict) -> dict:
    """计划 → 所有权声明集（纯函数；节选自 plan 的声明层字段）。

    cls 语义：mergeable（可加性）/ shared-script（共享可变——仅合成构建）
    / exclusive（独占声明）。
    """
    claims: list[dict] = []
    pid = plan["patch_id"]
    claims.append(_claim("patch", pid, "exclusive", "patch_id 独占"))
    # 房间实例槽：可加性（同房多实例不互斥）
    for alias, room in plan["rooms"].items():
        claims.append(_claim("room_inst", room["name"], "mergeable",
                             f"rooms.{alias} 新增实例"))
    # npc 对象事件脚本：共享可变（同对象的 Step/Create/Alarm 被多补丁追加）
    seen_obj: set[str] = set()
    for op in plan["ops"]:
        if op["op"] != "npc":
            continue
        obj = op["npc"]["object"]
        if obj in seen_obj:
            continue
        seen_obj.add(obj)
        for ev in ("Step_0", "Create_0"):
            claims.append(_claim(
                "object_script", f"gml_Object_{obj}_{ev}", "shared-script",
                f"对象 {obj} 的事件脚本被追加"))
        if op["npc"].get("native"):
            claims.append(_claim(
                "object_script", f"gml_Object_{obj}_Alarm_0",
                "shared-script", "原生交互 Alarm_0 守卫"))
        claims.append(_claim("var", f"{obj}:deterline_state",
                             "shared-script", "对象变量注册"))
        # 字符串键：独占（键名含 patch_id——跨补丁天然不撞，同补丁必撞）
        suffix = ("_choice", "_yes", "_no") if op["npc"]["choice"] else ("",)
        for sfx in suffix:
            claims.append(_claim(
                "text", f"det_{pid}_{op['ref']}{sfx}", "exclusive",
                f"npc {op['ref']} 文本键"))
    # 门模板：共享可变（共享 obj_deterline_door + 分支脚本）
    if any(op["op"] == "door" for op in plan["ops"]):
        for ev in ("Create_0", "Step_0"):
            claims.append(_claim(
                "object_script", f"gml_Object_obj_deterline_door_{ev}",
                "shared-script", "门模板共享对象"))
        claims.append(_claim("object_script", "gml_Script_deterline_door_back",
                             "shared-script", "门返回脚本"))
    # flag：独占声明（同 flag = 冲突）
    if plan.get("flag", {}).get("id") is not None:
        claims.append(_claim("flag", str(plan["flag"]["id"]), "exclusive",
                             "flag 声明"))
    # 字体管线：共享可变（cjk 时改共享脚本与字形表）
    if plan.get("cjk"):
        claims.append(_claim("font", "fnt_ja_maintext", "shared-script",
                             "CJK 字形表"))
        for sc in ("gml_Script_scr_setfont",
                   "gml_Script_scr_preload_textures"):
            claims.append(_claim("object_script", sc, "shared-script",
                                 "CJK 字体管线脚本"))
    claims.append(_claim("code", "gml_Script_textdata_en", "shared-script",
                         "文本表共享脚本"))
    return {"patch_id": pid, "claims": claims}


def compare_ownership(a: dict, b: dict) -> dict:
    """两计划所有权冲突表（包 26）：分类 + 所涉声明 + 处理建议。"""
    if a["patch_id"] == b["patch_id"]:
        return {"conflicts": [{
            "class": "exclusive",
            "kind": "patch", "id": a["patch_id"],
            "parties": [a["patch_id"], b["patch_id"]],
            "advice": "两个定义 patch_id 相同——更换其一（文本键/回执/"
                      "目录均按 patch_id 隔离）"}],
            "mergeable": False}
    key_a = {(c["kind"], c["id"]): c for c in a["claims"]}
    key_b = {(c["kind"], c["id"]): c for c in b["claims"]}
    shared: dict[tuple, dict] = {}
    mergeable: list[dict] = []
    exclusive: list[dict] = []
    for k in sorted(set(key_a) & set(key_b)):
        ca, cb = key_a[k], key_b[k]
        rec = {"class": "", "kind": k[0], "id": k[1],
               "parties": [a["patch_id"], b["patch_id"]]}
        if "exclusive" in (ca["class"], cb["class"]):
            rec["class"] = "exclusive"
            rec["advice"] = ("同一资源被两补丁独占声明——更换其一"
                             "（flag 用区/文本键命名）")
            exclusive.append(rec)
        elif "shared-script" in (ca["class"], cb["class"]):
            rec["class"] = "shared-script"
            shared[k] = rec
        else:
            rec["class"] = "mergeable"
            mergeable.append(rec)
    shared_list = [shared[k] for k in sorted(shared)]
    return {
        "conflicts": exclusive + shared_list,
        "mergeable": not exclusive,
        "shared_script": shared_list,
        "additive": mergeable,
        "advice": ("" if exclusive else
                   ("无独占冲突；共享可变资源（对象脚本/字体/文本表）只能"
                    "经同一合成构建合并——顺序两次构建会叠写（闸门会拒）"
                    if shared_list else "完全独立：可分别构建与撤销")),
    }


def compose_definitions(a: dict, b: dict) -> dict:
    """两份 v2 定义 → 合成定义（包 27；输入顺序无关）。

    - cjk 期望不一致 → 拒绝（单一构建只有一套 typer/字体管线）；
    - flag_id 双方皆声明且不同 → 拒绝（一补丁一旗标声明；缺省方允许）；
    - rooms 别名按 `<patch>__` 前缀合并；npcs/doors id 同规则；
    - order = patch_id 字典序内各自原声明序（**与命令行参数顺序无关**）。
    """
    for d in (a, b):
        if d.get("_version") != "v2":
            raise _pkg().StorylineError("合成仅支持 v2 定义（v1 走原路径）")
    if bool(a.get("cjk")) != bool(b.get("cjk")):
        raise _pkg().StorylineError(
            f"合成拒绝：cjk 期望不一致（{a['patch_id']}={bool(a.get('cjk'))} "
            f"vs {b['patch_id']}={bool(b.get('cjk'))}）——同一构建只有一套 "
            "typer/字体管线；请统一 cjk 声明后重试")
    fa, fb = a.get("flag_id"), b.get("flag_id")
    if fa is not None and fb is not None and fa != fb:
        raise _pkg().StorylineError(
            f"合成拒绝：双方均声明 flag（{fa} vs {fb}）——一补丁一旗标声明；"
            "去掉一方声明或统一后重试")
    first, second = sorted((a, b), key=lambda d: d["patch_id"])
    merged = {
        "schema": "deterline.storyline/v2",
        "_version": "v2",
        "patch_id": f"{first['patch_id']}+{second['patch_id']}",
        "cjk": bool(first.get("cjk")),
        "rooms": {}, "npcs": {}, "doors": {}, "order": [],
    }
    if fa is not None or fb is not None:
        merged["flag_id"] = fa if fa is not None else fb
    # 跨定义实例坐标重叠（同房同坐标 = 互斥；不同坐标 = 可加性）
    def _positions(d: dict) -> set[tuple]:
        pos = set()
        for nid, spec in (d.get("npcs") or {}).items():
            pos.add((d["rooms"][spec["room"]], spec["x"], spec["y"]))
        for _did, spec in (d.get("doors") or {}).items():
            pos.add((d["rooms"][spec["from"]], spec["x"], spec["y"]))
        return pos
    overlap = _positions(a) & _positions(b)
    if overlap:
        raise _pkg().StorylineError(
            f"合成拒绝：两补丁在相同房间相同坐标放置实例 {sorted(overlap)}"
            "——实例坐标互斥；请错开坐标或人工合并定义")
    for d in (first, second):
        p = d["patch_id"]
        alias_map: dict[str, str] = {}
        for alias, name in d["rooms"].items():
            new_alias = f"{p}__{alias}"
            alias_map[alias] = new_alias
            merged["rooms"][new_alias] = name
        npc_ids: dict[str, str] = {}
        for nid, spec in (d.get("npcs") or {}).items():
            new_id = f"{p}__{nid}"
            npc_ids[nid] = new_id
            spec = copy.deepcopy(spec)
            spec["room"] = alias_map[spec["room"]]
            merged["npcs"][new_id] = spec
        door_ids: dict[str, str] = {}
        for did, spec in (d.get("doors") or {}).items():
            new_id = f"{p}__{did}"
            door_ids[did] = new_id
            spec = copy.deepcopy(spec)
            spec["from"] = alias_map[spec["from"]]
            spec["to"] = alias_map[spec["to"]]
            merged["doors"][new_id] = spec
        for ref in d["order"]:
            kind, _, oid = ref.partition(":")
            table = npc_ids if kind == "npc" else door_ids
            merged["order"].append(f"{kind}:{table[oid]}")
    merged["_composed_of"] = [first["patch_id"], second["patch_id"]]
    return merged
