"""Deterline — UNDERTALE 存档与游戏数据修改工具包。

O2 拆包（研讨会2/01 §2.1）：scripts/modify_save.py 逐步拆入本包。
分层（单向）：errors/config/state ← paths/utmt/rooms_data/inifile/file0 ← cmds/* ← cli。

包内纪律（研讨会2/01 风险 #1/#4 铁律）：
- 跨模块引用一律模块属性形式（`from . import state` 后写 `state.SANDBOX_ACTIVE`，
  运行时查找）——禁止 `from .state import SANDBOX_ACTIVE` 式导入时绑定，
  否则测试 patch 与旗标写入全部静默失效。
- 唯一例外：无内部依赖的叶子（errors/config/state 本体）。

__version__ 单点：test_docs_lint 优先读本文件（O2-step0 地雷 #3）。
"""

__version__ = "2.4.4"
