"""GML 代码编辑域命令（O2 步 5：从 modify_save.py 1:1 平移）。

code 六命令 + 注入三胞胎（_append/_prepend + _replace_code_entry/
_replace_step_code）+ search-vars + create-script + handler-extract +
set-derived（域归属按依赖序：其依赖的 cmd_file0_set 在 file0 层、
_get_decompiled_code/cmd_code_replace 与其同域——方案"file0 半边"在
步 2 复核时按分层规则整体归入本域）。
跨模块一律模块属性形式：utmt./file0./errors.
"""

import difflib
import os
import sys
import tempfile
from pathlib import Path

from .. import errors, file0, utmt

def cmd_code_list(game_file: Path, limit: int, offset: int) -> None:
    csx = f'''
ScriptMessage("COUNT:" + Data.Code.Count);
for (int i = {offset}; i < Math.Min(Data.Code.Count, {offset + limit}); i++) {{
    ScriptMessage("[" + i + "] " + Data.Code[i].Name.Content);
}}
'''
    out = utmt._run_utmt(csx, game_file, save=False)
    for line in utmt._parse_msg(out):
        if line.startswith("COUNT:"):
            print(f"Total code entries: {line.split(':', 1)[1]}")
            print(f"{'Index':>6} | Code Name")
            print("-" * 80)
        else:
            print(line)


def cmd_code_decompile(game_file: Path, code_name: str, limit: int = 0, search: str = "") -> None:
    esc = utmt._csx_escape(code_name)
    esc_search = utmt._csx_escape(search)
    filter_lines = "" if not search else f'''
    ScriptMessage("SEARCH:" + "{esc_search}");
    for (int i = 0; i < lines.Length && found < {limit}; i++) {{
        if (lines[i].IndexOf("{esc_search}", StringComparison.OrdinalIgnoreCase) >= 0) {{
            ScriptMessage("  [" + i + "] " + lines[i]);
            found++;
        }}
    }}
    if (found == 0) ScriptMessage("  (no matches)");
    return;
'''
    csx = f'''
var code = Data.Code.ByName("{esc}");
if (code == null) {{
    ScriptMessage("ERROR: Code entry not found: {esc}");
    return;
}}
if (code.ParentEntry != null) {{
    ScriptMessage("SKIP: child entry of " + code.ParentEntry.Name.Content + ", decompile parent instead");
    return;
}}
try {{
    string gml = GetDecompiledText(code);
    var lines = gml.Split(new[] {{ "\\r\\n", "\\r", "\\n" }}, StringSplitOptions.None);
    int total = lines.Length;
    int max = {limit};
    if (max <= 0) max = total;
    int found = 0;
    {filter_lines}
    if (max <= 0) max = total;
    ScriptMessage("LINES:" + total + ":" + (max < total ? max.ToString() : total.ToString()));
    int end = Math.Min(max, total);
    for (int i = 0; i < end; i++) {{
        ScriptMessage(lines[i]);
    }}
}} catch (Exception ex) {{
    ScriptMessage("ERROR: " + ex.Message);
}}
'''
    out = utmt._run_utmt(csx, game_file, save=False)
    for line in utmt._parse_msg(out):
        if line.startswith("ERROR:"):
            print(line, file=sys.stderr)
        elif line.startswith("SKIP:"):
            print(line, file=sys.stderr)
        elif line.startswith("LINES:"):
            parts = line.split(":")
            total = parts[1]
            shown = parts[2] if len(parts) > 2 else total
            truncated = int(shown) < int(total)
            label = f" (仅显示前 {shown} 行)" if truncated else ""
            print(f"--- 共 {total} 行{label} ---")
            if truncated:
                print(f"提示: 用 --limit 0 查看全部 {total} 行；用 --search \"文本\" 只看匹配行。")
        else:
            print(line)


def _decompile_to_lines(game_file: Path, code_name: str) -> list[str] | None:
    """Decompile a code entry and return lines as list[str] (multi-line safe)."""
    esc = utmt._csx_escape(code_name)
    csx = f'''
var code = Data.Code.ByName("{esc}");
if (code == null) {{
    ScriptMessage("ERROR: not found");
    return;
}}
try {{
    string gml = GetDecompiledText(code);
    var lines = gml.Split(new[] {{ "\\r\\n", "\\r", "\\n" }}, StringSplitOptions.None);
    for (int i = 0; i < lines.Length; i++) {{
        ScriptMessage("GML_LINE:" + i + ":" + lines[i]);
    }}
    ScriptMessage("GML_COUNT:" + lines.Length);
}} catch (Exception ex) {{
    ScriptMessage("ERROR: " + ex.Message);
}}
'''
    out = utmt._run_utmt(csx, game_file, save=False)
    lines_out = utmt._parse_msg(out)
    count_line = next((l for l in lines_out if l.startswith("GML_COUNT:")), None)
    if count_line is None:
        err = [l for l in lines_out if l.startswith("ERROR:")]
        if err:
            print(err[0], file=sys.stderr)
        return None
    total = int(count_line.split(":")[1])
    line_map: dict[int, str] = {}
    for l in lines_out:
        if l.startswith("GML_LINE:"):
            _, idx_str, rest = l.split(":", 2)
            line_map[int(idx_str)] = rest
    return [line_map[i] for i in range(total)]


def _get_decompiled_code(game_file: Path, code_name: str) -> str | None:
    """Decompile a code entry and return its full source text."""
    lines = _decompile_to_lines(game_file, code_name)
    return None if lines is None else "\n".join(lines)


def _print_diff(name: str, old: str, new: str) -> None:
    """Print a simple diff between old and new GML code."""
    old_lines = old.splitlines()
    new_lines = new.splitlines()
    print(f"--- {name} (old)")
    print(f"++ GML  (new)")
    # Simple line-by-line diff
    import difflib
    for line in difflib.unified_diff(old_lines, new_lines, n=2,
                                       fromfile=f"old/{name}", tofile=f"new/{name}"):
        print(line)


def cmd_code_replace(game_file: Path, code_name: str, value: str, value_is_file: bool = False, show_diff: bool = False, dry_run: bool = False) -> None:
    """Replace an entire code entry with new GML content.

    value can be:
    - GML source code directly (value_is_file=False)
    - Path to a .gml file (value_is_file=True)
    """
    esc = utmt._csx_escape(code_name)
    gml = utmt._csx_escape(value)

    if value_is_file:
        p = Path(value)
        if not p.exists():
            raise errors.NotFoundError(f"文件不存在: {value}")
        gml = p.read_text(encoding="utf-8")

    if show_diff or dry_run:
        old_code = _get_decompiled_code(game_file, code_name)
        if old_code is not None:
            _print_diff(code_name, old_code, gml)

    if dry_run:
        print("(dry-run: 未写入任何修改)")
        return

    if value_is_file:
        esc_gml = utmt._csx_verbatim_escape(gml)
        csx = f'''
var code = Data.Code.ByName("{esc}");
if (code == null) {{
    ScriptMessage("ERROR: Code entry not found: {esc}");
    return;
}}
if (code.ParentEntry != null) {{
    ScriptMessage("SKIP: child entry, replace parent instead");
    return;
}}
try {{
    CodeImportGroup importGroup = new(Data)
    {{
        MainThreadAction = MainThreadAction
    }};
    importGroup.QueueReplace(code, @"{esc_gml}");
    importGroup.Import();
    ScriptMessage("OK: Replaced " + "{esc}");
}} catch (Exception ex) {{
    ScriptMessage("ERROR: " + ex.Message);
}}
'''
    else:
        csx = f'''
var code = Data.Code.ByName("{esc}");
if (code == null) {{
    ScriptMessage("ERROR: Code entry not found: {esc}");
    return;
}}
if (code.ParentEntry != null) {{
    ScriptMessage("SKIP: child entry, replace parent instead");
    return;
}}
try {{
    CodeImportGroup importGroup = new(Data)
    {{
        MainThreadAction = MainThreadAction
    }};
    importGroup.QueueReplace(code, "{gml}");
    importGroup.Import();
    ScriptMessage("OK: Replaced " + "{esc}");
}} catch (Exception ex) {{
    ScriptMessage("ERROR: " + ex.Message);
}}
'''
    out = utmt._run_utmt(csx, game_file, save=True)
    for line in utmt._parse_msg(out):
        if line.startswith("ERROR:"):
            print(line, file=sys.stderr)
        elif line.startswith("SKIP:"):
            print(line, file=sys.stderr)
        elif line.startswith("OK:"):
            print(line)
        else:
            print(line)


def cmd_code_find_replace(game_file: Path, code_name: str, old: str, new_val: str,
                          show_diff: bool = False, dry_run: bool = False) -> None:
    """Find and replace text within a decompiled code entry, then recompile.

    Uses Python-side string replacement (not QueueFindReplace) to avoid
    CSX escaping issues. Writes modified GML to a temp file.
    """
    gml_lines = _decompile_to_lines(game_file, code_name)
    if gml_lines is None:
        return
    
    gml = "\n".join(gml_lines)
    
    # Do the replacement
    replaced_count = gml.count(old)
    if replaced_count == 0:
        print(f"错误: 未找到匹配: '{old}'", file=sys.stderr)
        print(f"代码 {code_name} 的反编译内容如下 (前 10 行 / 后 5 行):", file=sys.stderr)
        for i, ln in enumerate(gml_lines[:10]):
            print(f"  {i+1:>4}: {ln[:120]}", file=sys.stderr)
        if len(gml_lines) > 15:
            print(f"  ... (共 {len(gml_lines)} 行)", file=sys.stderr)
            for i, ln in enumerate(gml_lines[-5:]):
                print(f"  {len(gml_lines)-4+i:>4}: {ln[:120]}", file=sys.stderr)
        # Fuzzy match suggestion
        import difflib
        all_text = "\n".join(gml_lines)
        words = all_text.replace("{", " ").replace("}", " ").replace("(", " ").replace(")", " ").replace(";", " ").replace("\n", " ").split()
        close = difflib.get_close_matches(old, words, n=3, cutoff=0.3)
        if close:
            print(f"您是否想找: {close}", file=sys.stderr)
        print("提示: 反编译输出的格式可能与源码不同（缩进、花括号位置等）。", file=sys.stderr)
        print("      先用 decompile-code 查看实际格式，再调整 --old 的值。", file=sys.stderr)
        raise errors.NotFoundError(f"未找到匹配: '{old}'")
    
    new_gml = gml.replace(old, new_val)

    if show_diff or dry_run:
        _print_diff(code_name, gml, new_gml)

    if dry_run:
        print(f"(dry-run: 匹配 {replaced_count} 处，未写入任何修改)")
        return

    # Write to temp file and use replace-code
    with tempfile.NamedTemporaryFile(mode='w', suffix='.gml', delete=False, encoding='utf-8') as f:
        f.write(new_gml)
        temp_path = f.name
    
    try:
        # Use the file-path mode of replace-code
        cmd_code_replace(game_file, code_name, temp_path, value_is_file=True)
        print(f"已替换 {replaced_count} 处")
    finally:
        Path(temp_path).unlink(missing_ok=True)


def _load_gml_value(value: str, value_is_file: bool) -> str:
    """Load GML source from a direct string or a .gml file path."""
    if not value_is_file:
        return value
    p = Path(value)
    if not p.exists():
        raise errors.NotFoundError(f"文件不存在: {value}")
    return p.read_text(encoding="utf-8")


def cmd_code_append(game_file: Path, code_name: str, value: str,
                    value_is_file: bool = False) -> None:
    """Append GML code to the end of an existing code entry (reliable version)."""
    value = _load_gml_value(value, value_is_file)
    esc = utmt._csx_escape(code_name)
    verb = utmt._csx_verbatim_escape(value)
    csx = f'''
var code = Data.Code.ByName("{esc}");
if (code == null) {{
    ScriptMessage("ERROR: Code entry not found: {esc}");
    return;
}}
if (code.ParentEntry != null) {{
    ScriptMessage("SKIP: child entry, use parent instead");
    return;
}}
try {{
    string existingGml = GetDecompiledText(code);
    string newGml = existingGml + "\\n" + @"{verb}";
    CodeImportGroup importGroup = new(Data)
    {{
        MainThreadAction = MainThreadAction
    }};
    importGroup.QueueReplace(code, newGml);
    importGroup.Import();
    ScriptMessage("OK: Appended to " + "{esc}" + " (len " + newGml.Length + ")");
}} catch (Exception ex) {{
    ScriptMessage("ERROR: " + ex.Message);
}}
'''
    out = utmt._run_utmt(csx, game_file, save=True)
    for line in utmt._parse_msg(out):
        if line.startswith("ERROR:"):
            print(line, file=sys.stderr)
        elif line.startswith("SKIP:"):
            print(line, file=sys.stderr)
        elif line.startswith("OK:"):
            print(line)
        else:
            print(line)


def cmd_code_prepend(game_file: Path, code_name: str, value: str,
                     value_is_file: bool = False) -> None:
    """Prepend GML code to the beginning of an existing code entry."""
    value = _load_gml_value(value, value_is_file)
    esc = utmt._csx_escape(code_name)
    verb = utmt._csx_verbatim_escape(value)
    csx = f'''
var code = Data.Code.ByName("{esc}");
if (code == null) {{
    ScriptMessage("ERROR: Code entry not found: {esc}");
    return;
}}
if (code.ParentEntry != null) {{
    ScriptMessage("SKIP: child entry, use parent instead");
    return;
}}
try {{
    CodeImportGroup importGroup = new(Data)
    {{
        MainThreadAction = MainThreadAction
    }};
    importGroup.QueuePrepend(code, @"{verb}");
    importGroup.Import();
    ScriptMessage("OK: Prepended to " + "{esc}");
}} catch (Exception ex) {{
    ScriptMessage("ERROR: " + ex.Message);
}}
'''
    out = utmt._run_utmt(csx, game_file, save=True)
    for line in utmt._parse_msg(out):
        if line.startswith("ERROR:"):
            print(line, file=sys.stderr)
        elif line.startswith("SKIP:"):
            print(line, file=sys.stderr)
        elif line.startswith("OK:"):
            print(line)
        else:
            print(line)


# 游戏在两处把 HP/AT/DF 从 LV 重算，必须同时改写这两处才能真正固定数值。
DERIVED_TARGET_SCRIPTS: list[str] = [
    "gml_Object_obj_battlecontroller_Create_0",
    "gml_Script_scr_levelup",
]


def _patch_stat_assignments(code: str, var: str, value: int) -> tuple[str, int]:
    """Rewrite every `global.<var> = ...;` assignment to a fixed literal.

    Matches both the LV-derived formula (e.g. `16 + (global.lv * 4)`) and a
    previously locked literal (e.g. `50`), so the operation is idempotent and
    re-lockable. Returns (new_code, number_of_replacements).
    """
    import re
    pattern = re.compile(rf"global\.{re.escape(var)}\s*=\s*[^;\n]*;")
    return pattern.subn(f"global.{var} = {value};", code)


def cmd_set_derived(save_dir: Path, game_file: Path, key: str, value: str) -> None:
    """Set a stat in file0 AND patch the game so it is not recomputed from LV.

    HP/AT/DF are derived from LV by scr_levelup and obj_battlecontroller_Create_0,
    so writing file0 alone is transient. This command rewrites those two scripts
    to hardcode the requested value.
    """
    upper = key.upper()
    if upper not in file0.DERIVED_STAT_VARS:
        raise errors.ValidationError(f"set-derived 仅支持 HP / MAXHP / AT / DF，收到: '{key}'")
    try:
        val = int(value)
    except ValueError:
        raise errors.ValidationError(f"值须为整数: {value}")
    if val < 0:
        raise errors.ValidationError(f"值不能为负: {val}")

    var = file0.DERIVED_STAT_VARS[upper]
    file0_key = "MAXHP" if var == "maxhp" else var.upper()

    print(f"🔧 固定 {upper} = {val}（file0 + 游戏脚本）")
    print(f"   注意: 这会永久改写 game.ios 的 {', '.join(DERIVED_TARGET_SCRIPTS)}，"
          f"对所有存档生效。用 undo --value data_win 可恢复。")

    # 1) 写入 file0（读档时立即生效）
    file0.cmd_file0_set(save_dir, file0_key, str(val), warn_derived=False)

    # 2) 改写游戏脚本，阻止进战斗/升级时按 LV 重算
    patched = 0
    for code_name in DERIVED_TARGET_SCRIPTS:
        code = _get_decompiled_code(game_file, code_name)
        if code is None:
            print(f"   ⚠️ 找不到脚本 {code_name}，跳过", file=sys.stderr)
            continue
        new_code, n = _patch_stat_assignments(code, var, val)
        if n == 0:
            print(f"   ⚠️ {code_name} 中没有 global.{var} 赋值，跳过", file=sys.stderr)
            continue
        cmd_code_replace(game_file, code_name, new_code)
        patched += n
        print(f"   ✓ {code_name}: 改写 {n} 处 global.{var}")

    if patched == 0:
        raise RuntimeError("未能改写任何脚本，游戏仍会按 LV 重算该属性")
    print(f"✓ {upper} 已固定为 {val}（共改写 {patched} 处）")


def cmd_search_vars(game_file: Path, query: str, limit: int) -> None:
    """Search for a variable name across all decompiled code entries."""
    esc = utmt._csx_escape(query)
    csx = f'''
int found = 0;
int totalCodes = Data.Code.Count;
ScriptMessage("SCANNING:" + totalCodes);
for (int ci = 0; ci < totalCodes && found < {limit}; ci++) {{
    try {{
        string gml = GetDecompiledText(Data.Code[ci]);
        if (gml.IndexOf("{esc}", StringComparison.OrdinalIgnoreCase) >= 0) {{
            string name = Data.Code[ci].Name.Content;
            // Extract first matching line
            var lines = gml.Split(new[] {{ "\\r\\n", "\\r", "\\n" }}, StringSplitOptions.None);
            for (int li = 0; li < lines.Length; li++) {{
                if (lines[li].IndexOf("{esc}", StringComparison.OrdinalIgnoreCase) >= 0) {{
                    ScriptMessage("[" + ci + "] " + name + ": " + lines[li].Trim());
                    break;
                }}
            }}
            found++;
        }}
    }} catch {{ }}
}}
if (found == 0) {{
    ScriptMessage("(no matches)");
}}
'''
    out = utmt._run_utmt(csx, game_file, save=False)
    lines = utmt._parse_msg(out)
    for line in lines:
        if line.startswith("SCANNING:"):
            total = line.split(":", 1)[1]
            print(f"Scanning {total} code entries...")
        else:
            print(line)
    utmt._fail_if_no_match(lines, "search-vars", query)


def cmd_create_script(game_file: Path, code_name: str, value: str, value_is_file: bool = False) -> None:
    """Create a new code entry (script) with given GML content.

    If the name follows the convention gml_Object_{name}_{event}_{subtype},
    the script is automatically linked to the object's event.
    Use gml_Script_{name} for new reusable scripts.
    """
    esc_name = utmt._csx_escape(code_name)
    gml_source = value

    if value_is_file:
        p = Path(value)
        if not p.exists():
            raise errors.NotFoundError(f"文件不存在: {value}")
        gml_source = p.read_text(encoding="utf-8")

    esc_gml = utmt._csx_verbatim_escape(gml_source)
    csx = f'''
try {{
    var existing = Data.Code.ByName("{esc_name}");
    if (existing != null) {{
        ScriptMessage("WARN:EXISTS:" + existing.Name.Content);
    }}
    CodeImportGroup importGroup = new(Data)
    {{
        AutoCreateAssets = true,
        MainThreadAction = MainThreadAction
    }};
    importGroup.QueueReplace("{esc_name}", @"{esc_gml}");
    importGroup.Import();
    ScriptMessage("OK: Created/replaced " + "{esc_name}");
}} catch (Exception ex) {{
    ScriptMessage("ERROR: " + ex.Message);
}}
'''
    out = utmt._run_utmt(csx, game_file, save=True)
    for line in utmt._parse_msg(out):
        if line.startswith("ERROR:"):
            print(line, file=sys.stderr)
        elif line.startswith("WARN:EXISTS:"):
            print(f"警告: 代码 '{code_name}' 已存在，将覆盖", file=sys.stderr)
        elif line.startswith("OK:"):
            print(line)


DETECTED_PATTERNS: list[tuple[str, str]] = [
    ("global.choice != -1", "选择框结果处理 (实验 5/7)"),
    ("global.flag[510]", "自定义 flag 510"),
    ("global.flag[511]", "自定义 flag 511"),
    ("ini_write_real", "存档写入 (实验 5)"),
    ("ossafe_savedata_save", "存档保存 (实验 5)"),
    ("global.msc = -1", "对话系统覆盖 (实验 7)"),
    ('msg[0] = "', "自定义对话消息"),
    ("scr_msgup", "手动消息更新"),
]


def cmd_handler_extract(game_file: Path, apply: bool = False) -> None:
    """Analyze and optionally extract custom logic from obj_time_Step_2."""
    CODE_NAME = "gml_Object_obj_time_Step_2"
    HANDLER_STEP = "gml_Object_obj_deterline_handler_Step_0"
    HANDLER_CREATE = "gml_Object_obj_deterline_handler_Create_0"

    lines = _decompile_to_lines(game_file, CODE_NAME)
    if lines is None:
        print(f"错误: 无法反编译 {CODE_NAME}", file=sys.stderr)
        return

    print(f"--- 分析 {CODE_NAME} ---")
    print(f"总行数: {len(lines)}")

    # Single-pass O(n) scan
    matched_lines: set[int] = set()
    for i, ln in enumerate(lines):
        for pattern, desc in DETECTED_PATTERNS:
            if pattern in ln:
                matched_lines.add(i)

    if not matched_lines:
        print("\n未检测到已知的自定义注入模式。代码可能是干净的。")
        print("代码前 15 行:")
        for i, ln in enumerate(lines[:15]):
            print(f"  {i+1:>4}: {ln[:120]}")
        return

    # Print diagnostics with context
    for pattern, desc in DETECTED_PATTERNS:
        count = sum(1 for ln in lines if pattern in ln)
        if count > 0:
            print(f"\n  [{pattern}]  {desc} ({count} 处)")
            for i, ln in enumerate(lines):
                if pattern in ln:
                    start = max(0, i - 1)
                    end = min(len(lines), i + 2)
                    for j in range(start, end):
                        marker = "→" if j == i else " "
                        if j not in matched_lines or j == i:
                            print(f"    {marker} {j+1:>4}: {ln[:120]}")

    print(f"\n--- 诊断结果 ---")
    print(f"检测到 {len(matched_lines)} 行涉及自定义逻辑")

    if not apply:
        print(f"\n使用 --apply 可提取自定义逻辑到独立对象:")
        print(f"  1. 创建 {HANDLER_STEP} — 包含检测到的代码")
        print(f"  2. 创建 {HANDLER_CREATE} — 初始化 handler 状态")
        print(f"  3. 清理 {CODE_NAME} — 移除注入的自定义代码")
        print(f"  4. 将 obj_deterline_handler 生成到需要的房间")
        return

    # ── --apply: 真正提取 matched_lines 到 handler ──
    sorted_matched = sorted(matched_lines)

    # Extract: group consecutive matched lines into blocks
    blocks: list[list[int]] = []
    current: list[int] = []
    for idx in sorted_matched:
        if not current or idx == current[-1] + 1:
            current.append(idx)
        else:
            blocks.append(current)
            current = [idx]
    if current:
        blocks.append(current)

    # Build handler Step code from extracted blocks
    handler_parts: list[str] = []
    handler_parts.append("// Deterline extracted handler (from obj_time_Step_2)")
    handler_parts.append("// Runs every step via obj_deterline_handler")
    handler_parts.append("if (!variable_global_exists(\"deterline_handler_active\")) {")
    handler_parts.append("    global.deterline_handler_active = true;")
    handler_parts.append("")
    for block in blocks:
        handler_parts.append(f"    // Extracted block (lines {block[0]+1}-{block[-1]+1})")
        for idx in block:
            handler_parts.append(f"    {lines[idx]}")
        handler_parts.append("")
    handler_parts.append("    global.choice = -1;")
    handler_parts.append("}")
    handler_text = "\n".join(handler_parts)

    # Build clean obj_time_Step_2 (skip matched lines)
    clean_lines = [ln for i, ln in enumerate(lines) if i not in matched_lines]
    clean_text = "\n".join(clean_lines).strip()
    if not clean_text:
        clean_text = "// obj_time_Step_2 — cleaned by handler-extract"

    # Inject both into game
    esc_handler = utmt._csx_escape(HANDLER_STEP)
    esc_create = utmt._csx_escape(HANDLER_CREATE)
    esc_orig = utmt._csx_escape(CODE_NAME)
    verb_handler = utmt._csx_verbatim_escape(handler_text)
    verb_create = utmt._csx_verbatim_escape(
        "global.deterline_handler_active = true;"
    )
    verb_clean = utmt._csx_verbatim_escape(clean_text)

    csx = f'''
try {{
    CodeImportGroup importGroup = new(Data)
    {{
        AutoCreateAssets = true,
        MainThreadAction = MainThreadAction
    }};
    importGroup.QueueReplace("{esc_handler}", @"{verb_handler}");
    importGroup.QueueReplace("{esc_create}", @"{verb_create}");
    importGroup.QueueReplace("{esc_orig}", @"{verb_clean}");
    importGroup.Import();
    ScriptMessage("OK: Created " + "{esc_handler}");
    ScriptMessage("OK: Created " + "{esc_create}");
    ScriptMessage("OK: Cleaned " + "{esc_orig}");
}} catch (Exception ex) {{
    ScriptMessage("ERROR: " + ex.Message);
}}
'''
    out = utmt._run_utmt(csx, game_file, save=True)
    for line in utmt._parse_msg(out):
        if line.startswith("ERROR:"):
            print(line, file=sys.stderr)
        elif line.startswith("OK:"):
            print(line)

    extracted_count = len(sorted_matched)
    print(f"\n已完成: 提取 {extracted_count} 行到 handler，清理了原代码。")
    print(f"将 obj_deterline_handler 生成到需要的房间:")
    print(f"  spawn-obj --value <room> --key obj_deterline_handler --x 0 --y 0 --file data_win")


def _prepend_to_code(game_file: Path, code_name: str, value: str) -> None:
    """Prepend GML to a code entry using QueueReplace (reliable)."""
    esc = utmt._csx_escape(code_name)
    verb = utmt._csx_verbatim_escape(value)
    csx = f'''
var code = Data.Code.ByName("{esc}");
if (code == null) {{
    ScriptMessage("ERROR: Code entry not found: {esc}");
    return;
}}
try {{
    string existingGml = GetDecompiledText(code);
    string newGml = @"{verb}" + "\\n" + existingGml;
    CodeImportGroup importGroup = new(Data)
    {{
        MainThreadAction = MainThreadAction
    }};
    importGroup.QueueReplace(code, newGml);
    importGroup.Import();
    ScriptMessage("OK: Prepended to " + "{esc}");
}} catch (Exception ex) {{
    ScriptMessage("ERROR: " + ex.Message);
}}
'''
    out = utmt._run_utmt(csx, game_file, save=True)
    for line in utmt._parse_msg(out):
        if line.startswith("ERROR:"):
            print(line, file=sys.stderr)
        elif line.startswith("OK:"):
            print(line)


def _append_to_code(game_file: Path, code_name: str, value: str) -> None:
    """Append GML to a code entry using QueueReplace (reliable)."""
    esc = utmt._csx_escape(code_name)
    verb = utmt._csx_verbatim_escape(value)
    csx = f'''
var code = Data.Code.ByName("{esc}");
if (code == null) {{
    ScriptMessage("ERROR: Code entry not found: {esc}");
    return;
}}
if (code.ParentEntry != null) {{
    ScriptMessage("SKIP: child entry, use parent instead");
    return;
}}
try {{
    string existingGml = GetDecompiledText(code);
    string newGml = existingGml + "\\n" + @"{verb}";
    CodeImportGroup importGroup = new(Data)
    {{
        MainThreadAction = MainThreadAction
    }};
    importGroup.QueueReplace(code, newGml);
    importGroup.Import();
    ScriptMessage("OK: Appended to " + "{esc}" + " (len " + newGml.Length + ")");
}} catch (Exception ex) {{
    ScriptMessage("ERROR: " + ex.Message);
}}
'''
    out = utmt._run_utmt(csx, game_file, save=True)
    for line in utmt._parse_msg(out):
        if line.startswith("ERROR:"):
            print(line, file=sys.stderr)
        elif line.startswith("SKIP:"):
            print(line, file=sys.stderr)
        elif line.startswith("OK:"):
            print(line)


def _replace_step_code(game_file: Path, code_name: str, instance_id: int, new_block: str) -> None:
    """Replace a Step event's code, keeping only lines not owned by this instance's
    previous injected trigger (guarded by `if (id == N)`)."""
    lines = _decompile_to_lines(game_file, code_name)
    if lines is None:
        return
    kept: list[str] = []
    skip_block = False
    depth = 0
    for ln in lines:
        stripped = ln.strip()
        if f"if (id == {instance_id})" in stripped:
            skip_block = True
            depth = 0
            continue
        if skip_block:
            for ch in stripped:
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
            if depth <= 0:
                skip_block = False
            continue
        kept.append(ln)
    new_gml = "\n".join(kept).rstrip() + "\n" + new_block
    _replace_code_entry(game_file, code_name, new_gml)


def _replace_code_entry(game_file: Path, code_name: str, gml_source: str) -> None:
    """Replace a code entry's full GML via QueueReplace."""
    esc = utmt._csx_escape(code_name)
    verb = utmt._csx_verbatim_escape(gml_source)
    csx = f'''
var code = Data.Code.ByName("{esc}");
if (code == null) {{
    ScriptMessage("ERROR: Code entry not found: {esc}");
    return;
}}
try {{
    CodeImportGroup importGroup = new(Data)
    {{
        MainThreadAction = MainThreadAction
    }};
    importGroup.QueueReplace(code, @"{verb}");
    importGroup.Import();
    ScriptMessage("OK: Replaced " + "{esc}" + " (len " + @"{verb}".Length + ")");
}} catch (Exception ex) {{
    ScriptMessage("ERROR: " + ex.Message);
}}
'''
    out = utmt._run_utmt(csx, game_file, save=True)
    for line in utmt._parse_msg(out):
        if line.startswith("ERROR:"):
            print(line, file=sys.stderr)
        elif line.startswith("OK:"):
            print(line)
