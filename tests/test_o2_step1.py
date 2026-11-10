"""O2 步 1 包纪律警戒线（研讨会2/01 §2.2 步 1 + 风险 #1/#9）。

三项 AST/活绑定警戒线，防拆包期与拆包后两类静默失效：

1. 旗标只经 state.X 模块属性读写——from-import 快照绑定会让 state 侧写入
   与本模块读数静默分叉（stale-read 陷阱，_run_utmt 读到永远 False =
   沙箱/v2 写入安全全线失效）。AST 扫描：旗标名只允许出现在
   ImportFrom 别名（兼容 re-export）与 `state.X` 属性访问里。
2. 包内相对导入只允许导模块（`from . import x`），不允许导符号
   （`from .x import y`）——后者是导入时绑定，mock/旗标写入全部失效
   （研讨会2/01 风险 #1 铁律的静态强制）。
3. shim re-export 是活绑定——ms.* 与 deterline.* 语义对象同一（identity），
   防止有人复制出第二真相源（风险 #9）。
"""

import ast
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"

sys.path.insert(0, str(SCRIPTS))

import modify_save as ms  # noqa: E402
import deterline.config as config  # noqa: E402
import deterline.errors as errors  # noqa: E402
import deterline.paths as paths  # noqa: E402
import deterline.state as state  # noqa: E402

FLAGS = {
    "SANDBOX_ACTIVE", "SANDBOX_ORIGINAL", "COMMIT_ACTIVE",
    "NO_STEAM_SYNC", "AUTO_SNAPSHOT", "ALLOW_CJK", "_UTMT_CLI_PATH",
}


def _iter_package_files():
    files = [SCRIPTS / "modify_save.py"]
    pkg = SCRIPTS / "deterline"
    if pkg.is_dir():
        files.extend(sorted(pkg.glob("**/*.py")))
    return [f for f in files if f.exists() and "__pycache__" not in f.parts]


def _module_exists(base: Path, dotted: str) -> bool:
    """deterline 包内是否存在模块/子包 dotted（'cmds.room' 等）。"""
    rel = dotted.replace(".", "/")
    return (base / f"{rel}.py").exists() or (base / rel / "__init__.py").exists()


class TestFlagAccessViaStateOnly(unittest.TestCase):
    """纪律 1：旗标名只能以 ImportFrom 别名（re-export）或 state.X 出现。"""

    def test_no_bare_flag_names_outside_state(self):
        offenders = []
        for f in _iter_package_files():
            rel = f.relative_to(REPO)
            if f.name == "state.py" and f.parent.name == "deterline":
                continue  # 旗标本体定义点
            tree = ast.parse(f.read_text(encoding="utf-8"), filename=str(f))
            for node in ast.walk(tree):
                if isinstance(node, ast.Global) and set(node.names) & FLAGS:
                    offenders.append(f"{rel}:{node.lineno}: global {node.names}")
                elif isinstance(node, ast.Name) and node.id in FLAGS:
                    offenders.append(f"{rel}:{node.lineno}: 裸引用 {node.id}")
                elif (isinstance(node, ast.Attribute) and node.attr in FLAGS
                      and isinstance(node.value, ast.Name)
                      and not (node.value.id == "state"
                               or (node.value.id == "ms"
                                   and f.name == "modify_save.py"))):
                    # state.<旗标> 合法；ms.<旗标> 只允许出现在 modify_save.py
                    # （复核 P2-3：按文件白名单放行，deterline/** 内一律禁止——
                    # 防止包内出现 ms.* 读写而不报警）
                    offenders.append(f"{rel}:{node.lineno}: "
                                     f"{node.value.id}.{node.attr}（非 state 前缀/ms shim）")
        self.assertEqual(
            offenders, [],
            "旗标纪律违规（from-import/global/裸引用 = stale-read 陷阱，"
            "研讨会2/01 修订 1）——请改写为 state.X 模块属性形式：\n"
            + "\n".join(offenders))

    def test_state_module_owns_all_flags(self):
        for name in sorted(FLAGS):
            self.assertTrue(hasattr(state, name), f"state.py 缺旗标 {name}")

    def test_tests_never_touch_flags_via_ms(self):
        """复核 P2-5：tests/ 不得出现 ms.<旗标>——旗标单点化后 patch ms.* 是
        静默失效的假保护（兼容面提取器还会把它"合法化"进清单）。"""
        offenders = []
        pat = None
        import re as _re
        pat = _re.compile(
            r"(?<![A-Za-z])ms\.(" + "|".join(sorted(FLAGS)) + r")\b")
        for f in (Path(__file__).resolve().parent).glob("test_*.py"):
            for i, l in enumerate(f.read_text(encoding="utf-8").split("\n"), 1):
                m = pat.search(l)
                if m:
                    offenders.append(f"{f.name}:{i}: {m.group(0)}")
        self.assertEqual(
            offenders, [],
            "tests/ 出现 ms.<旗标> 引用——patch/断言必须指向 deterline.state "
            "（canonical 单点），ms 侧是快照 re-export，写了不生效：\n"
            + "\n".join(offenders))


class TestPackageImportDiscipline(unittest.TestCase):
    """纪律 2：包内相对导入只导模块，不导符号。"""

    def test_relative_imports_are_module_only(self):
        offenders = []
        for f in _iter_package_files():
            if f.parent == SCRIPTS:
                continue  # modify_save.py 是包外 shim，允许 from-import
            rel = f.relative_to(REPO)
            tree = ast.parse(f.read_text(encoding="utf-8"), filename=str(f))
            for node in ast.walk(tree):
                if not (isinstance(node, ast.ImportFrom) and node.level >= 1):
                    continue
                # 解析基准：level=1 → deterline/<...当前目录>；向上回溯 level-1 层
                anchor = f.parent
                for _ in range(node.level - 1):
                    anchor = anchor.parent
                targets = []
                if node.module:
                    targets.append(node.module)  # from .x import y：y 必须是模块
                for alias in node.names:
                    if node.module:
                        targets.append(f"{node.module}.{alias.name}")
                    else:
                        targets.append(alias.name)  # from . import x
                for t in targets:
                    if not _module_exists(anchor, t):
                        offenders.append(
                            f"{rel}:{node.lineno}: from {'.' * node.level}"
                            f"{node.module or ''} import {t}（目标不是模块——"
                            f"符号导入=导入时绑定，违反复核铁律）")
        self.assertEqual(offenders, [], "\n".join(offenders))


class TestShimReexportsAreLiveBindings(unittest.TestCase):
    """纪律 3：shim re-export 与包内语义对象 identity 一致。"""

    def test_flags_reexport_same_object(self):
        for name in ("SANDBOX_ACTIVE", "SANDBOX_ORIGINAL", "COMMIT_ACTIVE",
                     "NO_STEAM_SYNC", "AUTO_SNAPSHOT", "ALLOW_CJK"):
            self.assertIs(getattr(ms, name), getattr(state, name),
                          f"ms.{name} 与 state.{name} 不同一——shim 出现第二真相源")

    def test_rooms_never_imported_or_bare_outside_rooms_data(self):
        """步 2 复核 P2-1 前瞻加固：ROOMS 是重绑定型全局（_load_rooms 换 dict
        对象）——任何 from-import 快照都会指向旧 dict（stale-dict 陷阱）。
        禁止 rooms_data.py 之外的任何 ROOMS 导入/裸名；ms 不得持有 ROOMS
        属性（读者一律 rooms_data.ROOMS 模块属性）。"""
        offenders = []
        for f in _iter_package_files():
            rel = f.relative_to(REPO)
            if f.name == "rooms_data.py" and f.parent.name == "deterline":
                continue
            tree = ast.parse(f.read_text(encoding="utf-8"), filename=str(f))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    if node.names and node.names[0].name == "*":
                        offenders.append(f"{rel}:{node.lineno}: 星号导入"
                                         f"（绕过符号级警戒线，一并拒绝）")
                    for a in node.names:
                        if a.name == "ROOMS" or a.asname == "ROOMS":
                            offenders.append(f"{rel}:{node.lineno}: "
                                             f"from-import ROOMS as {a.asname or a.name}")
                elif isinstance(node, ast.Import):
                    for a in node.names:
                        if a.name.endswith(".ROOMS") or a.asname == "ROOMS":
                            offenders.append(f"{rel}:{node.lineno}: "
                                             f"import {a.name} as {a.asname or a.name}")
                elif isinstance(node, ast.Name) and node.id == "ROOMS":
                    offenders.append(f"{rel}:{node.lineno}: 裸名 ROOMS")
        self.assertEqual(
            offenders, [],
            "ROOMS 只能经 rooms_data.ROOMS 模块属性访问（stale-dict 陷阱，"
            "步 2 复核 P2-1）：\n" + "\n".join(offenders))

    def test_ms_does_not_hold_rooms_binding(self):
        self.assertFalse(hasattr(ms, "ROOMS"),
                         "ms 不得 re-export ROOMS（重绑定型全局的快照绑定 = 陷阱）")

    def test_ms_flags_come_from_import_not_literal(self):
        """复核 P2-2：assertIs 对 False/None 单例恒真，挡不住 shim 手写
        `SANDBOX_ACTIVE = False` 字面量第二真相源。AST 断言：ms 的 7 个旗标
        名必须全部来自 `from deterline.state import ...` 别名，且模块级不得
        有对旗标的赋值节点。"""
        tree = ast.parse((SCRIPTS / "modify_save.py").read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if (isinstance(node, ast.ImportFrom)
                    and (node.module or "").endswith("deterline.state")
                    and node.level == 0):
                imported.update(a.name for a in node.names)
        # 期望 re-export 集合 = 兼容面 6 旗标；_UTMT_CLI_PATH 无兼容消费者
        # （ms 内一律 state._UTMT_CLI_PATH），不在 re-export 集合
        required = FLAGS - {"_UTMT_CLI_PATH"}
        missing = required - imported
        self.assertEqual(missing, set(),
                         f"ms 未从 deterline.state 导入旗标: {sorted(missing)}——"
                         f"旗标只能经 re-export，不得手写第二真相源")
        assigns = [ast.unparse(n.targets[0]) for n in tree.body
                   if isinstance(n, ast.Assign)
                   and any(isinstance(t, ast.Name) and t.id in FLAGS for t in n.targets)]
        self.assertEqual(assigns, [],
                         f"ms 模块级出现旗标赋值（字面量第二真相源）: {assigns}")

    def test_leaves_reexport_same_object(self):
        for mod, names in (
            (errors, ("DeterlineError", "ValidationError", "NotFoundError")),
            (config, ("FLAG_INDEX_MAX", "FLAG_CUSTOM_START", "FLAG_CUSTOM_END",
                      "FACE_CHOICES", "SANS_EMOTIONS", "DISTANCE_TRIGGER",
                      "QUEST_STATE_INIT", "ROOM_BG_WARNING")),
            (paths, ("find_save_dir", "find_game_data_file",
                     "backup_file", "list_backups")),
        ):
            for name in names:
                self.assertIs(getattr(ms, name), getattr(mod, name),
                              f"ms.{name} 与包内 {mod.__name__}.{name} 不同一")

    def test_ms_state_attribute_is_canonical_module(self):
        self.assertIs(ms.state, state)

    def test_no_double_qualified_module_refs(self):
        """步 6 复核 P1-1：过限定（rooms_data.rooms_data.ROOMS）——1:1 校验器
        对旧侧已带前缀的行存在对称剥离盲区，此处以静态扫描兜底。"""
        import re as _re
        mods = ("state", "errors", "config", "paths", "utmt", "rooms_data",
                "inifile", "file0", "save_cmds", "dialogue", "code", "room",
                "npc", "door", "sprite", "verify", "cjk")
        pat = _re.compile(r"\b(" + "|".join(mods) + r")\s*\.\s*(" + "|".join(mods) + r")\b")
        offenders = []
        for f in _iter_package_files():
            rel = f.relative_to(REPO)
            for i, l in enumerate(f.read_text(encoding="utf-8").split("\n"), 1):
                m = pat.search(l)
                if m and "#" not in l.split(m.group(0))[0]:
                    offenders.append(f"{rel}:{i}: {m.group(0)}")
        self.assertEqual(offenders, [],
                         "过限定模块引用（双重前缀，运行时 AttributeError）：\n"
                         + "\n".join(offenders))

    def test_room_list_runs(self):
        """步 6 复核 P1-1(c)：room-list 零测试覆盖曾让 P0 双重前缀漏网（无
        UTMT 依赖，纯 rooms_data 域）——补最小冒烟。"""
        import io as _io
        import contextlib as _ctxlib
        buf = _io.StringIO()
        with _ctxlib.redirect_stdout(buf):
            ms.cmd_room_list("")  # noqa: 无法 import 前的防御——ms 兼容面即测点
        out = buf.getvalue()
        self.assertIn("房间", out)
        self.assertGreater(len(out.strip().splitlines()), 10, "244 房间列表应输出多行")

    def test_shim_is_import_only(self):
        """O2 步 10 终态守卫（风险 #9）：shim 顶层只许 import/re-export +
        包引导 If + __main__ 守卫——零 def/class/赋值逻辑。"""
        tree = ast.parse((SCRIPTS / "modify_save.py").read_text(encoding="utf-8"))
        for n in tree.body:
            if isinstance(n, (ast.FunctionDef, ast.ClassDef)):
                self.fail(f"shim 顶层出现 {type(n).__name__}——实现必须留在包内")
            if isinstance(n, ast.If):
                src = ast.unparse(n.test)
                self.assertTrue(
                    "_HERE not in sys.path" in src or '__name__' in src,
                    f"shim 顶层出现未知 If：{src[:60]}——shim 只许包引导/入口守卫")
            if isinstance(n, ast.Assign):
                # 唯一豁免：包引导自举 _HERE（复核 P1-1 的实现本体）
                tid = n.targets[0].id if (len(n.targets) == 1
                                          and isinstance(n.targets[0], ast.Name)) else None
                ok = tid in ("_HERE", "__version__")  # 自举 + 外部兼容版本号
                if not ok:
                    self.fail(f"shim 顶层出现赋值 {ast.unparse(n)[:60]}——"
                              f"第二真相源（A8 风险 #9）")


class TestCliSsot(unittest.TestCase):
    """步 10 终态守卫：cli.py 的 ACTION_CHOICES 与 dispatch 分支双向一致。

    room-list P0 的教训：冷路径无测试覆盖时，写错前缀要等运行时才炸——
    至少让"每个 action 都有分支"成为静态事实。"""

    def test_every_action_has_dispatch_branch(self):
        import ast as _ast
        src = (SCRIPTS / "deterline" / "cli.py").read_text(encoding="utf-8")
        tree = _ast.parse(src)
        # ACTION_CHOICES 模块级字面量
        choices = None
        for n in tree.body:
            if (isinstance(n, ast.Assign) and len(n.targets) == 1
                    and isinstance(n.targets[0], ast.Name)
                    and n.targets[0].id == "ACTION_CHOICES"):
                choices = [_ast.literal_eval(e) for e in n.value.elts]
        self.assertIsNotNone(choices, "cli.py 缺 ACTION_CHOICES")
        # dispatch 分支里的字符串比较 args.action == "xxx"
        branches = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare):
                for side in (node.left, *node.comparators):
                    if isinstance(side, ast.Constant) and isinstance(side.value, str):
                        branches.add(side.value)  # Eq 形态：args.action == "x"
                    elif isinstance(side, ast.Tuple):
                        branches.update(
                            e.value for e in side.elts
                            if isinstance(e, ast.Constant) and isinstance(e.value, str))
                        # In 形态：args.action in ("x", "y")（共享分支）
        missing = [a for a in choices if a not in branches]
        self.assertEqual(missing, [],
                         f"ACTION_CHOICES 中无 dispatch 分支的 action（冷路径）: {missing}")


if __name__ == "__main__":
    unittest.main()
