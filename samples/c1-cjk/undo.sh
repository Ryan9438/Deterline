#!/bin/bash
# c1-cjk 样例·阶段 3/3：撤销（显式）。
# 用法: undo.sh <运行目录>   ← prepare.sh 输出的目录
#
# 语义：
#   - 撤销**只在本脚本显式运行时发生**（prepare/verify 绝不代做——14 手册
#     §1：显式指定应用与撤销的时点）；
#   - 恢复运行目录副本到基线（game.ios.bak → game.ios），md5 对账
#     fc049850856dea4ef1427bbf5653fc47，recovery-scan 收尾；
#   - 结果写回 run.json（stages.undo），回执留档。
set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/lib.sh"

[ $# -eq 1 ] || c1_die "用法: undo.sh <运行目录>"
RUN_DIR="$1"
[ -d "$RUN_DIR" ] || c1_die "运行目录不存在: $RUN_DIR"
[ -f "$RUN_DIR/run.json" ] || c1_die "缺 run.json（先跑 prepare.sh）: $RUN_DIR"

c1_preflight_core

UTC_START="$(c1_now)"
BAK="$RUN_DIR/game.ios.bak"
[ -f "$BAK" ] || c1_die "备份缺失: ${BAK}（无可用撤销点——检查 prepare 是否真的应用过）"
BAK_MD5="$(md5 -q "$BAK")"
[ "$BAK_MD5" = "$C1_BASELINE_MD5" ] || c1_die \
  "备份指纹异常: $BAK md5=$BAK_MD5 期望=${C1_BASELINE_MD5}（撤销点不可信，拒绝执行）"

echo "== [U1] undo（副本内 .bak → game.ios） =="
c1_run_cli --action undo --file data_win --value data_win --dir "$RUN_DIR/game.ios"

AFTER_MD5="$(md5 -q "$RUN_DIR/game.ios")"
AFTER_SHA="$(shasum -a 256 "$RUN_DIR/game.ios" | awk '{print $1}')"
MATCHES="false"
[ "$AFTER_MD5" = "$C1_BASELINE_MD5" ] && MATCHES="true"
[ "$MATCHES" = "true" ] || c1_die \
  "撤销后指纹不符: $AFTER_MD5 ≠ 基线 ${C1_BASELINE_MD5}——现场保留待人工核查"

echo "== [U2] recovery-scan 收尾确认 =="
c1_run_cli --action recovery-scan --dir "$RUN_DIR/game.ios" --json \
  > "$RUN_DIR/undo_recovery.json" 2> "$RUN_DIR/undo_recovery.err"
PY="$PY" RUN_DIR="$RUN_DIR" \
"$PY" - <<'PYEOF'
import json, os, pathlib
d = json.loads((pathlib.Path(os.environ["RUN_DIR"]) / "undo_recovery.json")
               .read_text(encoding="utf-8"))
n = len(d.get("findings", []))
print(f"  findings: {n}" + ("（期望 0）" if n else " ✓"))
PYEOF

UTC_END="$(c1_now)"
PY="$PY" RUN_DIR="$RUN_DIR" UTC_START="$UTC_START" UTC_END="$UTC_END" \
AFTER_SHA="$AFTER_SHA" MATCHES="$MATCHES" \
"$PY" - <<'PYEOF'
import json, os, pathlib
rd = pathlib.Path(os.environ["RUN_DIR"])
run = json.loads((rd / "run.json").read_text(encoding="utf-8"))
run["status"] = "undone"
run["stages"]["undo"] = {
    "started_utc": os.environ["UTC_START"],
    "finished_utc": os.environ["UTC_END"], "rc": 0,
    "sha256_after": os.environ["AFTER_SHA"],
    "matches_baseline": os.environ["MATCHES"] == "true",
    "artifacts": ["undo_recovery.json"]}
rd.joinpath("run.json").write_text(
    json.dumps(run, ensure_ascii=False, indent=2), encoding="utf-8")
PYEOF

echo "== [U3] 撤销完成: 副本已回基线（md5 对账通过）——运行目录保留作证据 =="
