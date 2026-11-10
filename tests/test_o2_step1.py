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
                      and node.value.id not in ("state", "ms")):
                    # state.<旗标> 合法；ms.<旗标> 只允许出现在 modify_save.py 的
                    # re-export 语义里（而 ast.Name 已挡裸引用，此处挡
                    # `something_else.FLAG` 形态的意外访问）
                    offenders.append(f"{rel}:{node.lineno}: "
                                     f"{node.value.id}.{node.attr}（非 state/ms 前缀）")
        self.assertEqual(
            offenders, [],
            "旗标纪律违规（from-import/global/裸引用 = stale-read 陷阱，"
            "研讨会2/01 修订 1）——请改写为 state.X 模块属性形式：\n"
            + "\n".join(offenders))

    def test_state_module_owns_all_flags(self):
        for name in sorted(FLAGS):
            self.assertTrue(hasattr(state, name), f"state.py 缺旗标 {name}")


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


if __name__ == "__main__":
    unittest.main()
