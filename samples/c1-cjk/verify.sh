#!/bin/bash
# c1-cjk 样例·阶段 2/3：验收（本地沙箱级，只读）。
# 用法: verify.sh <运行目录>   ← prepare.sh 输出的目录
#
# 语义：
#   - 指纹链核对（run.json ↔ apply 回执 ↔ 副本现值）；
#   - O7 结构化差异（检出基线 vs 已应用副本，--detail 全文）；
#   - recovery-scan 收尾确认（findings 期望 0）；
#   - 打印实机窗口清单——**仅为材料**：实机验证属用户值守场次（证据分级
#     sandbox/实机 不得升格），本脚本不启动游戏、不做安装、不撤销。
set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/lib.sh"

[ $# -eq 1 ] || c1_die "用法: verify.sh <运行目录>"
RUN_DIR="$1"
[ -d "$RUN_DIR" ] || c1_die "运行目录不存在: $RUN_DIR"
[ -f "$RUN_DIR/run.json" ] || c1_die "缺 run.json（先跑 prepare.sh）: $RUN_DIR"

c1_preflight_core

UTC_START="$(c1_now)"
# patch_id/cjk 从 run.json 取（prepare 已参数化 --defn；cjk 缺省 true 兼容旧运行目录）。
RUN_DIR="$RUN_DIR" "$PY" -c 'import json,os,sys
try:
    d = json.load(open(os.environ["RUN_DIR"]+"/run.json", encoding="utf-8"))
except Exception:
    sys.exit(2)
sys.exit(0 if isinstance(d, dict) else 2)' \
  || c1_die "run.json 无法解析或顶层不是对象（旧/截断格式）"
PATCH="$(RUN_DIR="$RUN_DIR" "$PY" -c \
  'import json,os; print(json.load(open(os.environ["RUN_DIR"]+"/run.json", encoding="utf-8")).get("patch_id",""))')"
RUN_DIR="$RUN_DIR" "$PY" -c 'import json,os,re,sys
try:
    d = json.load(open(os.environ["RUN_DIR"]+"/run.json", encoding="utf-8"))
except Exception:
    sys.exit(1)
p = d.get("patch_id")
sys.exit(0 if isinstance(p, str) and re.fullmatch(r"[a-z0-9][a-z0-9_]{2,63}", p) else 1)' \
  || c1_die "run.json patch_id 不合引擎规则（正则 [a-z0-9][a-z0-9_]{2,63}，全串匹配）: $(printf '%q' "$PATCH")"
IS_CJK="$(RUN_DIR="$RUN_DIR" "$PY" -c \
  'import json,os; print("1" if json.load(open(os.environ["RUN_DIR"]+"/run.json", encoding="utf-8")).get("cjk", True) else "0")')"
RECEIPT="$RUN_DIR/.deterline/storyline/game.ios/$PATCH/receipt.json"
[ -f "$RECEIPT" ] || c1_die "apply 回执缺失: ${RECEIPT}（prepare 未成功？）"

# 指纹链：apply 回执 after_sha256 == 副本现值（sha256）；run.json 一致。
CURRENT_SHA="$(shasum -a 256 "$RUN_DIR/game.ios" | awk '{print $1}')"
PY="$PY" RUN_DIR="$RUN_DIR" CURRENT_SHA="$CURRENT_SHA" PATCH="$PATCH" \
"$PY" - <<'PYEOF'
import json, os, pathlib, sys
rd = pathlib.Path(os.environ["RUN_DIR"])
receipt = json.loads(
    (rd / ".deterline/storyline/game.ios" / os.environ["PATCH"] / "receipt.json")
    .read_text(encoding="utf-8"))
run = json.loads((rd / "run.json").read_text(encoding="utf-8"))
current = os.environ["CURRENT_SHA"]
ok = True


def _dict(x):
    return x if isinstance(x, dict) else {}


if not isinstance(run, dict):
    print("✗ run.json 顶层不是对象（旧/截断格式）"); sys.exit(1)
if not isinstance(receipt, dict):
    print("✗ apply 回执顶层不是对象（旧/截断格式）"); sys.exit(1)
if receipt.get("schema") != "deterline.storyline-apply/v1":
    print(f"✗ apply 回执 schema 异常: {receipt.get('schema')}"); ok = False
if receipt.get("after_sha256") != current:
    print(f"✗ 指纹链断裂: 回执 after={receipt.get('after_sha256')[:16]}… "
          f"≠ 副本现值 {current[:16]}…"); ok = False
staged = _dict(_dict(_dict(run.get("stages")).get("prepare"))
               .get("applied")).get("after_sha256")
if not staged:
    print("✗ run.json 缺 stages.prepare.applied.after_sha256（旧/截断格式）"); ok = False
elif staged != current:
    print(f"✗ run.json 与副本现值不一致: {staged[:16]}… vs {current[:16]}…"); ok = False
print("✓ 指纹链一致: run.json == apply 回执 == 副本现值" if ok else "", end="\n" if ok else "")
sys.exit(0 if ok else 1)
PYEOF

echo "== [V1] O7 结构化差异（检出基线 vs 已应用副本；--expected 声明闸门） =="
cp "$C1_SAMPLE_DIR/expected_scope.json" "$RUN_DIR/expected_scope.json"
RC=""
c1_run_cli --action diff-snapshots --file data_win \
  --key "$C1_REPO_ROOT/game.ios" --value "$RUN_DIR/game.ios" --detail \
  --expected "$RUN_DIR/expected_scope.json" \
  > "$RUN_DIR/verify_diff.txt" 2>&1 || RC=$?
# 闸门语义（当前工具链实测钉定）：
#   rc=1 且 成功标记在场 且 计入差异恰为 2 = 工具链自身不可豁免的
#   deterline_state 变量副作用（COUNT VARS + VARDETERLINE）——预期通过态；
#   rc=0 = 副本与基线零差异 → 材料未应用，fail；其余 → 现场保留待人工判读。
[ "$RC" = "1" ] || c1_die "diff-snapshots rc=${RC}（预期 1）——看 ${RUN_DIR}/verify_diff.txt"
grep -q -- "--- 资源级差异" "$RUN_DIR/verify_diff.txt" || c1_die \
  "diff 输出缺成功标记（可能工具错误）——看 verify_diff.txt"
SUMMARY="$(grep -o "共 [0-9]* 处差异" "$RUN_DIR/verify_diff.txt" | grep -o "[0-9]*" || true)"
[ -n "$SUMMARY" ] || c1_die "diff 输出缺「共 N 处差异」汇总行——看 verify_diff.txt"
[ "$SUMMARY" = "2" ] || c1_die \
  "计入差异 $SUMMARY 处（当前工具链预期恰 2：deterline_state 变量副作用）" \
  "——看 verify_diff.txt，若工具链闸门行为变化请更新本样例"
grep -q -- "COUNT VARS" "$RUN_DIR/verify_diff.txt" && \
  grep -q -- "VARDETERLINE" "$RUN_DIR/verify_diff.txt" || c1_die \
  "未见到 deterline_state 变量副作用行——计入差异构成与预期不符"
echo "  下列为 diff --detail 尾部：所列 STR/CODEF 行均为声明内命中（expected_scope 覆盖，不计入）"
echo "  工具总结「共 2 处差异」= 声明闸门后剩余，预期恰 2 = deterline_state 变量副作用（COUNT VARS + VARDETERLINE，已知形态）"
tail -n 6 "$RUN_DIR/verify_diff.txt"

echo "== [V2] recovery-scan 收尾确认 =="
c1_run_cli --action recovery-scan --dir "$RUN_DIR/game.ios" --json \
  > "$RUN_DIR/verify_recovery.json" 2> "$RUN_DIR/verify_recovery.err"
PY="$PY" RUN_DIR="$RUN_DIR" \
"$PY" - <<'PYEOF'
import json, os, pathlib
d = json.loads((pathlib.Path(os.environ["RUN_DIR"]) / "verify_recovery.json")
               .read_text(encoding="utf-8"))
n = len(d.get("findings", []))
if n:
    print(f"✗ findings: {n}（期望 0）——recovery-scan 报告未完结事务/孤儿文件")
    raise SystemExit(1)
print("  findings: 0 ✓")
PYEOF

UTC_END="$(c1_now)"
PY="$PY" RUN_DIR="$RUN_DIR" UTC_START="$UTC_START" UTC_END="$UTC_END" \
"$PY" - <<'PYEOF'
import json, os, pathlib
rd = pathlib.Path(os.environ["RUN_DIR"])
run = json.loads((rd / "run.json").read_text(encoding="utf-8"))
run["stages"]["verify"] = {
    "started_utc": os.environ["UTC_START"],
    "finished_utc": os.environ["UTC_END"], "rc": 0,
    "artifacts": ["expected_scope.json", "verify_diff.txt", "verify_recovery.json"]}
rd.joinpath("run.json").write_text(
    json.dumps(run, ensure_ascii=False, indent=2), encoding="utf-8")
PYEOF

if [ "$IS_CJK" = "1" ]; then
  RENDER_NOTE="首屏中文（typer=31 渲染）/ 选项行 / 是·否两支"
else
  RENDER_NOTE="首屏文本（typer=5 标准渲染，ASCII 腿）/ 选项行 / Yes·No 两支"
fi
cat <<EOF
== [V3] 本地沙箱级验收完成（实机级留用户窗口） ==
  实机窗口清单（仅用户值守时执行；口径 05 §5.2 / 15-SOP，逐格记录）:
    ① 真实安装前备份（03 §10 授权）→ 将运行目录副本安装到游戏数据位
    ② steam://run/391540 → room_ruins1 触发点（100,200 半径 60）观察:
       $RENDER_NOTE / once 自毁 / 重进 /
       存读档持久语义；holdSeconds ≥ 0.15
    ③ 恢复真实安装备份 + 哈希核对（fc049850856dea4ef1427bbf5653fc47）
  撤销（本地副本）: samples/c1-cjk/undo.sh "<运行目录>"
EOF
