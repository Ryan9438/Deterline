"""运行旗标单点（O2 修订 1，研讨会2/01 §2.1）。

一轮审计的 P0 根因是全局旗标散布三个"相距 6000 行"的角落（定义 L79-92、
赋值 main() L7100-7112、消费 _run_utmt L318）。拆包后这些旗标天然跨模块，
必须单点。迁移期**不做**旗标改 dataclass/参数注入的优化——保持模块级变量
语义（state.X 模块属性读写），行为零变化。

读写纪律：一切访问走 `state.X` 模块属性形式（运行时查找）。
禁止 `from .state import SANDBOX_ACTIVE`（导入时快照，写入丢失——这正是
state.py 存在的原因）。tests/test_o2_step1.py 以 AST 扫描强制本纪律。
"""

from pathlib import Path

SANDBOX_ACTIVE = False
SANDBOX_ORIGINAL: Path | None = None
COMMIT_ACTIVE = False     # V2: --commit 时为 True（写真实文件 + Steam 同步）
NO_STEAM_SYNC = False     # V2: --no-steam-sync 时为 True（即使 --commit 也不同步 Steam）
AUTO_SNAPSHOT = False     # 实验前自动 .bak 时间戳备份（--auto-snapshot）
ALLOW_CJK = False   # C3a: --allow-cjk 时为 True（放行 CJK，配合中文字体注入 C3b）
_UTMT_CLI_PATH: str | None = None   # _find_utmt_cli 的解析缓存
WORKSPACE: str | None = None  # Named experiment selected for this CLI invocation.
PREVIEW = False  # Validate and describe edit plans without committing them.
