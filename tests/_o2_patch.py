"""O2 拆包过渡期 dual-patch 助手（步 3 引入，研讨会2/01 风险 #1）。

单一 mock 同时挂两个 patch 点：
  - ms._run_utmt           （ms 内裸名调用的路径——cmds 未迁期）
  - deterline.utmt._run_utmt（包内 utmt._run_utmt 模块属性调用的路径）

拆包期两种调用路径并存，任一路径都被同一 mock 拦截；若未来有人写成
from-import 绑定（导入时快照），两条路径同时失效 → golden 捕获为空 →
哨兵响亮失败。这正是该机制的设计目的。

步 10 完成后（ms 纯 shim、命令全在包内）可摘除 ms 侧挂点。
"""

import sys
import contextlib
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import modify_save as ms  # noqa: E402
from deterline import utmt  # noqa: E402


@contextlib.contextmanager
def dual_patch_utmt(**kwargs):
    """用法：with dual_patch_utmt(side_effect=fake_run) as m: ..."""
    m = mock.MagicMock(**kwargs)
    with mock.patch.object(ms, "_run_utmt", m), \
         mock.patch.object(utmt, "_run_utmt", m):
        yield m
