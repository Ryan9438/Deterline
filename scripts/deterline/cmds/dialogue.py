"""对话域命令（O2 步 5：从 modify_save.py 1:1 平移）。

strg（Dialogue Editor）+ textdata + SCR_TEXT 搜索 + quest + batch-textdata
（域归属按方案 §1.2 dialogue 项；batch 原物理位置在 door 区块，归对话域）。
跨模块一律模块属性形式：utmt./rooms_data./file0./config./errors.
（运行时查找——_run_utmt 经 utmt.X，dual_patch_utmt 双路径拦截保 mock 可见）。
"""

import io
import json
import re
import sys
from pathlib import Path

from .. import config, errors, file0, rooms_data, utmt

def cmd_strg_list(game_file: Path, limit: int, offset: int, hex_mode: bool) -> None:
    if offset == 0:
        csx = '''ScriptMessage("COUNT:" + Data.Strings.Count);'''
        out = utmt._run_utmt(csx, game_file, save=False)
        for line in utmt._parse_msg(out):
            if line.startswith("COUNT:"):
                print(f"Total strings: {line.split(':', 1)[1]}")
                break
        print(f"{'Index':>6} | Content")
        print("-" * 80)

    if limit > 0:
        csx = f'''
for (int i = {offset}; i < Math.Min(Data.Strings.Count, {offset + limit}); i++) {{
    ScriptMessage("[" + i + "] " + Data.Strings[i].Content);
}}
'''
        out = utmt._run_utmt(csx, game_file, save=False)
        for line in utmt._parse_msg(out):
            print(line)


def cmd_strg_get(game_file: Path, key: int) -> None:
    csx = f'''ScriptMessage("[" + {key} + "] " + Data.Strings[{key}].Content);'''
    out = utmt._run_utmt(csx, game_file, save=False)
    for line in utmt._parse_msg(out):
        print(line)


def cmd_strg_set(game_file: Path, key: int, value: str) -> None:
    utmt._validate_ascii_text(value, "对话文本")
    esc = utmt._csx_escape(value)
    csx = f'''
var old = Data.Strings[{key}].Content;
Data.Strings[{key}].Content = "{esc}";
ScriptMessage("[{key}] " + old + " → " + Data.Strings[{key}].Content);
'''
    out = utmt._run_utmt(csx, game_file, save=True)
    for line in utmt._parse_msg(out):
        print(line)


def cmd_strg_add(game_file: Path, value: str) -> None:
    utmt._validate_ascii_text(value, "对话文本")
    esc = utmt._csx_escape(value)
    csx = f'''
var s = Data.Strings.MakeString("{esc}");
var idx = Data.Strings.IndexOf(s);
ScriptMessage("NEW_INDEX:" + idx);
ScriptMessage("Content: " + Data.Strings[idx].Content);
'''
    out = utmt._run_utmt(csx, game_file, save=True)
    for line in utmt._parse_msg(out):
        print(line)


def cmd_strg_delete(game_file: Path, key: int) -> None:
    csx = f'''
var old = Data.Strings[{key}].Content;
Data.Strings.RemoveAt({key});
ScriptMessage("Deleted [" + {key} + "]: " + old);
'''
    out = utmt._run_utmt(csx, game_file, save=True)
    for line in utmt._parse_msg(out):
        print(line)


def cmd_strg_replace(game_file: Path, old: str, new_val: str) -> None:
    oe = utmt._csx_escape(old)
    ne = utmt._csx_escape(new_val)
    csx = f'''
int count = 0;
for (int i = 0; i < Data.Strings.Count; i++) {{
    if (Data.Strings[i].Content == "{oe}") {{
        Data.Strings[i].Content = "{ne}";
        ScriptMessage("Replaced [" + i + "]: " + "{oe}" + " → " + "{ne}");
        count++;
    }}
}}
ScriptMessage("DONE:" + count + " replacements");
'''
    out = utmt._run_utmt(csx, game_file, save=True)
    for line in utmt._parse_msg(out):
        if line.startswith("DONE:"):
            n = line.split(":", 1)[1].split()[0]
            print(f"已替换 {n} 处")
        else:
            print(line)


def cmd_strg_search(game_file: Path, query: str, limit: int) -> None:
    esc = utmt._csx_escape(query)
    csx = f'''
int found = 0;
for (int i = 0; i < Data.Strings.Count && found < {limit}; i++) {{
    if (Data.Strings[i].Content.IndexOf("{esc}", StringComparison.OrdinalIgnoreCase) >= 0) {{
        ScriptMessage("[" + i + "] " + Data.Strings[i].Content);
        found++;
    }}
}}
ScriptMessage("FOUND:" + found);
'''
    out = utmt._run_utmt(csx, game_file, save=False)
    printed = 0
    found_total = None
    for line in utmt._parse_msg(out):
        if line.startswith("FOUND:"):
            found_total = int(line.split(":", 1)[1])
            label = f" (仅显示前 {limit} 个)" if found_total > limit else ""
            print(f"找到 {found_total} 个匹配 '{query}'{label}")
        else:
            print(line)
            printed += 1
    if found_total == 0:
        print(f"警告: search-strings 无匹配: '{query}'", file=sys.stderr)
        print("      未找到目标——禁止编造名称或结果；请如实报告失败。", file=sys.stderr)
        sys.exit(utmt.NO_MATCH_EXIT_CODE)


def cmd_textdata_search(game_file: Path, query: str, limit: int) -> None:
    """Search for keys in the textdata_en map."""
    esc = utmt._csx_escape(query)
    csx = f'''
try {{
    string gml = GetDecompiledText(Data.Code.ByName("gml_Script_textdata_en"));
    var lines = gml.Split(new[] {{ "\\r\\n", "\\r", "\\n" }}, StringSplitOptions.None);
    int found = 0;
    for (int i = 0; i < lines.Length && found < {limit}; i++) {{
        if (lines[i].IndexOf("{esc}", StringComparison.OrdinalIgnoreCase) >= 0) {{
            ScriptMessage(lines[i]);
            found++;
        }}
    }}
    if (found == 0) {{
        ScriptMessage("(no matches)");
    }}
}} catch (Exception ex) {{
    ScriptMessage("ERROR: " + ex.Message);
}}
'''
    out = utmt._run_utmt(csx, game_file, save=False)
    lines = utmt._parse_msg(out)
    for line in lines:
        if line.startswith("ERROR:"):
            print(line, file=sys.stderr)
        else:
            print(line)
    print("⚠️  注意: 本列表按文件行序输出，key 编号 ≠ 台词顺序。", file=sys.stderr)
    print("    列表里第一行 ≠ '第一句对话'。确定台词顺序请反编译引用这些 key 的", file=sys.stderr)
    print("    对象事件代码，看 global.msg[N] = scr_gettext(\"key\") 的先后（见 SKILL.md）。", file=sys.stderr)
    utmt._fail_if_no_match(lines, "search-textdata", query)


def _validate_facechoice(face: int) -> None:
    if face not in config.FACE_CHOICES:
        choices = ", ".join(f"{k}={v}" for k, v in config.FACE_CHOICES.items())
        print(f"警告: facechoice={face} 超出有效范围 (0-9)", file=sys.stderr)
        print(f"  可用: {choices}", file=sys.stderr)


def _inject_face_control(value: str, face: int, emotion: int) -> str:
    """Prepend \\F{face}\\E{emotion} control codes to dialogue text."""
    if face < 0 or face > 9:
        return value
    if face == 0:
        return value  # no face
    return f"\\F{face}\\E{emotion}{value}"


def cmd_textdata_add(game_file: Path, key: str, value: str,
                     face: int = 0, emotion: int = 0) -> None:
    """Add a new key-value pair to the textdata_en map.

    This modifies gml_Script_textdata_en to append a new ds_map_add line.
    The value is also added to the STRG table.
    """
    _validate_facechoice(face)
    value = _inject_face_control(value, face, emotion)
    utmt._validate_ascii_text(value, f"对话条目 '{key}'")
    if "\\C" in value:
        print("⚠️  该文本含 \\C 选择框标记——若由 Step 代码触发，分支处理必须替换", file=sys.stderr)
        print("    global.msg[0] 为不含 \\C 的文本，否则 obj_choicer 的 scr_msgup 会", file=sys.stderr)
        print("    重新复制本文本导致选择框循环重弹。建议用 npc-choice 命令一键生成。", file=sys.stderr)
    if not any(value.rstrip("\n\r ").endswith(s) for s in ["/", "/%%", "%%%", "\\C ", "\\C", "/%"]):
        print("警告: 对话文本应使用标准格式结尾", file=sys.stderr)
        print("  中间页: 以 / 结尾", file=sys.stderr)
        print("  末页: 以 /%% 结尾", file=sys.stderr)
        print("  选择: 以 \\C 结尾", file=sys.stderr)

    esc_key = utmt._csx_escape(key)
    esc_val = utmt._csx_escape(value)

    v_key = utmt._csx_verbatim_escape(key)
    v_val = utmt._csx_verbatim_escape(value)
    # Single round trip: MakeString into STRG + append ds_map_add line to textdata_en.
    code_csx = f'''
try {{
    var s = Data.Strings.MakeString("{esc_val}");
    int strg_idx = Data.Strings.IndexOf(s);
    ScriptMessage("STRG_INDEX:" + strg_idx);

    string gml = GetDecompiledText(Data.Code.ByName("gml_Script_textdata_en"));
    if (gml.IndexOf(@"ds_map_add(global.text_data_en, ""{v_key}"", ") >= 0) {{
        ScriptMessage("WARN: Key '" + "{esc_key}" + "' already exists, skipping (use delete-textentry first)");
        return;
    }}
    gml = gml.TrimEnd() + "\\r\\n" + @"ds_map_add(global.text_data_en, ""{v_key}"", ""{v_val}"");";

    CodeImportGroup importGroup = new(Data)
    {{
        MainThreadAction = MainThreadAction
    }};
    importGroup.QueueReplace(Data.Code.ByName("gml_Script_textdata_en"), gml);
    importGroup.Import();
    ScriptMessage("OK: Added textdata entry '" + "{esc_key}" + "' (STRG idx " + strg_idx + ")");
}} catch (Exception ex) {{
    ScriptMessage("ERROR: " + ex.Message);
}}
'''
    out = utmt._run_utmt(code_csx, game_file, save=True)
    for line in utmt._parse_msg(out):
        if line.startswith("ERROR:"):
            print(line, file=sys.stderr)
        elif line.startswith("WARN:"):
            print(line, file=sys.stderr)
        elif line.startswith("OK:"):
            print(line)


def cmd_guided_add_dialogue(game_file: Path, key: str, text: str,
                            face: int = 0, emotion: int = 0) -> None:
    """Guided dialogue creation — prints structured step-by-step progress.
    
    Designed for Agent use. Each step validates and reports success/failure.
    Maps to the "加对话" questionnaire module (QUESTIONNAIRE_WORKFLOW.md §2).
    """
    steps = [
        ("Step 1/4", "文本 key", key, lambda: utmt._csx_escape(key)),
        ("Step 2/4", "对话内容", text, lambda: (utmt._validate_ascii_text(text, "对话"), text)),
        ("Step 3/4", "头像角色", f"{config.FACE_CHOICES.get(face, '?')} ({face})", lambda: _validate_facechoice(face)),
        ("Step 4/4", "头像表情", f"{config.SANS_EMOTIONS.get(emotion, '?')} ({emotion})", lambda: None),
    ]
    for tag, label, val, validate in steps:
        try:
            validate()
            print(f"  {tag} {label}: {val} ✅")
        except (errors.ValidationError, errors.DeterlineError) as e:
            print(f"  {tag} {label}: ❌ {e}")
            return

    print(f"  → 执行 add-textentry...")
    cmd_textdata_add(game_file, key, text, face=face, emotion=emotion)
    print(f"  ✅ 对话条目 '{key}' 已添加")
    print(f"  💡 参考: 用 search-textdata --value \"{key}\" --file data_win 验证")


def cmd_textdata_delete(game_file: Path, key: str) -> None:
    """Delete a key-value pair from the textdata_en map.

    This searches for ds_map_add(global.text_data_en, "key", ...) and removes the line.
    """
    v_key = utmt._csx_verbatim_escape(key)
    esc_key = utmt._csx_escape(key)
    csx = f'''
try {{
    string gml = GetDecompiledText(Data.Code.ByName("gml_Script_textdata_en"));
    string search = @"ds_map_add(global.text_data_en, ""{v_key}"", ";
    var lines = gml.Split(new[] {{ "\\r\\n", "\\r", "\\n" }}, StringSplitOptions.None);
    System.Text.StringBuilder sb = new System.Text.StringBuilder();
    int removed = 0;
    for (int i = 0; i < lines.Length; i++) {{
        if (lines[i].TrimStart().StartsWith(search)) {{
            removed++;
        }} else {{
            if (sb.Length > 0) sb.Append("\\r\\n");
            sb.Append(lines[i]);
        }}
    }}
    if (removed == 0) {{
        ScriptMessage("ERROR: No entry found for key '{esc_key}'");
        return;
    }}
    string newGml = sb.ToString();
    CodeImportGroup importGroup = new(Data)
    {{
        MainThreadAction = MainThreadAction
    }};
    importGroup.QueueReplace(Data.Code.ByName("gml_Script_textdata_en"), newGml);
    importGroup.Import();
    ScriptMessage("OK: Removed " + removed + " entry(s) for '" + "{esc_key}" + "'");
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


def cmd_textdata_update(game_file: Path, key: str, value: str,
                        face: int = 0, emotion: int = 0) -> None:
    """Update the text of an EXISTING key in the textdata_en map (idempotent).

    Replaces the value of the ds_map_add(global.text_data_en, "key", ...) line
    in gml_Script_textdata_en. Errors if the key does not exist.
    """
    _validate_facechoice(face)
    value = _inject_face_control(value, face, emotion)
    utmt._validate_ascii_text(value, f"对话条目 '{key}'")
    if "\\C" in value:
        print("⚠️  该文本含 \\C 选择框标记——若由 Step 代码触发，分支处理必须替换", file=sys.stderr)
        print("    global.msg[0] 为不含 \\C 的文本，否则 obj_choicer 的 scr_msgup 会", file=sys.stderr)
        print("    重新复制本文本导致选择框循环重弹。建议用 npc-choice 命令一键生成。", file=sys.stderr)
    if not any(value.rstrip("\n\r ").endswith(s) for s in ["/", "/%%", "%%%", "\\C ", "\\C", "/%"]):
        print("警告: 对话文本应使用标准格式结尾", file=sys.stderr)
        print("  中间页: 以 / 结尾", file=sys.stderr)
        print("  末页: 以 /%% 结尾", file=sys.stderr)
        print("  选择: 以 \\C 结尾", file=sys.stderr)

    v_key = utmt._csx_verbatim_escape(key)
    v_val = utmt._csx_verbatim_escape(value)
    esc_key = utmt._csx_escape(key)
    csx = f'''
try {{
    string gml = GetDecompiledText(Data.Code.ByName("gml_Script_textdata_en"));
    string search = @"ds_map_add(global.text_data_en, ""{v_key}"", ";
    string newLine = @"ds_map_add(global.text_data_en, ""{v_key}"", ""{v_val}"");";
    var lines = gml.Split(new[] {{ "\\r\\n", "\\r", "\\n" }}, StringSplitOptions.None);
    int updated = 0;
    for (int i = 0; i < lines.Length; i++) {{
        if (lines[i].TrimStart().StartsWith(search)) {{
            int indent = lines[i].Length - lines[i].TrimStart().Length;
            lines[i] = new string(' ', indent) + newLine;
            updated++;
        }}
    }}
    if (updated == 0) {{
        ScriptMessage("ERROR: No entry found for key '{esc_key}' (use add-textentry first)");
        return;
    }}
    string newGml = string.Join("\\r\\n", lines);
    CodeImportGroup importGroup = new(Data)
    {{
        MainThreadAction = MainThreadAction
    }};
    importGroup.QueueReplace(Data.Code.ByName("gml_Script_textdata_en"), newGml);
    importGroup.Import();
    ScriptMessage("OK: Updated " + updated + " entry(s) for '" + "{esc_key}" + "'");
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


def cmd_search_sctext(game_file: Path, query: str, limit: int) -> None:
    """Search for cases in SCR_TEXT that contain a given text."""
    esc = utmt._csx_escape(query)
    csx = f'''
try {{
    string gml = GetDecompiledText(Data.Code.ByName("gml_Script_SCR_TEXT"));
    var lines = gml.Split(new[] {{ "\\r\\n", "\\r", "\\n" }}, StringSplitOptions.None);
    int found = 0;
    string curCase = "";
    for (int i = 0; i < lines.Length && found < {limit}; i++) {{
        string trimmed = lines[i].Trim();
        if (trimmed.StartsWith("case ")) curCase = trimmed;
        if (trimmed.IndexOf("{esc}", StringComparison.OrdinalIgnoreCase) >= 0) {{
            ScriptMessage("--- [" + curCase + "] ---");
            int ctxStart = Math.Max(0, i - 2);
            int ctxEnd = Math.Min(lines.Length - 1, i + 2);
            for (int j = ctxStart; j <= ctxEnd; j++) {{
                ScriptMessage("  " + lines[j]);
            }}
            found++;
        }}
    }}
    if (found == 0) ScriptMessage("(no matches)");
}} catch (Exception ex) {{
    ScriptMessage("ERROR: " + ex.Message);
}}
'''
    out = utmt._run_utmt(csx, game_file, save=False)
    lines = utmt._parse_msg(out)
    for line in lines:
        if line.startswith("ERROR:"):
            print(line, file=sys.stderr)
        else:
            print(line)
    utmt._fail_if_no_match(lines, "search-sctext", query)


def cmd_quest_init(save_dir: Path, flag_idx: int = config.FLAG_CUSTOM_START) -> None:
    """Reset a quest flag to initial state (0)."""
    if not (0 <= flag_idx <= config.FLAG_INDEX_MAX):
        raise errors.ValidationError(f"flag 索引 {flag_idx} 超出范围")
    f0 = save_dir / "file0"
    if not f0.exists():
        raise errors.NotFoundError(f"file0 不存在: {f0}")
    name, nums = file0._parse_file0(f0)
    file0_idx = 29 + flag_idx
    if file0_idx >= len(nums):
        raise errors.ValidationError(f"flag[{flag_idx}] 越界")
    old = nums[file0_idx]
    nums[file0_idx] = 0
    file0._write_file0(f0, name, nums)
    print(f"✓ flag[{flag_idx}]: {old} → 0 (已重置为初始状态)")


def cmd_quest_status(save_dir: Path) -> None:
    """Show status of custom quest flags."""
    f0 = save_dir / "file0"
    if not f0.exists():
        raise errors.NotFoundError(f"file0 不存在: {f0}")
    _, nums = file0._parse_file0(f0)
    for flag_idx in (config.FLAG_CUSTOM_START, config.FLAG_CUSTOM_END):
        file0_idx = 29 + flag_idx
        val = nums[file0_idx] if file0_idx < len(nums) else "?"
        label = f"flag[{flag_idx}]"
        desc = ""
        if flag_idx == config.FLAG_CUSTOM_START:
            desc = " (自定义状态机: 0=未开始, 1+=阶段)"
        elif flag_idx == config.FLAG_CUSTOM_END:
            desc = " (备用)"
        print(f"  {label} = {val}{desc}")
    # Try to find nearby unused flags
    unused = []
    for fi in range(0, config.FLAG_INDEX_MAX + 1):
        idx = 29 + fi
        if idx < len(nums) and nums[idx] == 0:
            unused.append(fi)
    print(f"  空闲 flag 索引: {len(unused)} 个 (0-{config.FLAG_INDEX_MAX})")
    if unused:
        print(f"  例: {unused[:10]}{'...' if len(unused) > 10 else ''}")


def cmd_batch_textdata(game_file: Path, json_path: str,
                       face: int = 0, emotion: int = 0) -> None:
    """Batch import dialogue entries from a JSON file.

    JSON format: [{"key": "...", "text": "..."}, ...]
    """
    p = Path(json_path)
    if not p.exists():
        raise errors.NotFoundError(f"文件不存在: {json_path}")
    try:
        with open(str(p), "r", encoding="utf-8") as f:
            entries = json.load(f)
    except (json.JSONDecodeError, Exception) as e:
        raise errors.ValidationError(f"JSON 解析失败: {e}")
    
    if not isinstance(entries, list):
        raise errors.ValidationError("JSON 必须是数组格式")
    
    for entry in entries:
        key = entry.get("key", "")
        text = entry.get("text", "")
        entry_face = entry.get("face", face)
        entry_emotion = entry.get("emotion", emotion)
        if not key or not text:
            print(f"跳过无效条目: {entry}", file=sys.stderr)
            continue
        _validate_facechoice(entry_face)
        text = _inject_face_control(text, entry_face, entry_emotion)
        print(f"  → {key}...", end="", flush=True)
        cmd_textdata_add(game_file, key, text, face=0, emotion=0)
        print()

    print(f"✓ 批量导入完成: {len(entries)} 条")
