#!/bin/bash
# c1-cjk 样例·阶段 1/3：准备（构建 + 应用到独立副本）。
# 用法: prepare.sh [--out DIR] [--defn FILE]
#   --out 缺省 = ${DL_C1_RUNS:-${TMPDIR:-/tmp}/dl_c1_runs}/<UTC 时间戳>
#   --defn 缺省 = 本样例 defn_cjk.yaml；可指向任意 storyline/v1 定义
#     （如 defn_ascii.yaml——cjk:false 腿，免字体与 Pillow/numpy 闸门）
#
# 语义（14 手册 §1 拆解）：
#   - 每次运行创建**全新独立目录**（已存在即拒——无固定路径复用）；
#   - 基线副本 → 只读计划 → 工作区构建 → 应用预览 → **显式 --no-steam-sync
#     整包应用**；全程零真实数据写入（副本在运行目录内，回执/工作区同目录）；
#   - 应用完成后**就地停住**：构建产物长期保留在运行目录，等待操作者显式
#     验收（verify.sh）与显式撤销（undo.sh）——本脚本绝不自动撤销；
#   - 构建指纹与交接信息落 run.json（机器可读）+ 各阶段 --json 产物。
set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/lib.sh"

OUT=""
DEFN_SRC=""
while [ $# -gt 0 ]; do
  case "$1" in
    --out) OUT="$2"; shift 2 ;;
    --defn) DEFN_SRC="$2"; shift 2 ;;
    *) c1_die "未知参数: $1（用法: prepare.sh [--out DIR] [--defn FILE]）" ;;
  esac
done

c1_preflight_core
# 定义选择先于资产闸门：cjk:false 腿不需要字体/Pillow/numpy（14 手册 §1
# 正例矩阵的资产缺席形态——ASCII 是最小依赖面）。
: "${DEFN_SRC:=$C1_SAMPLE_DIR/defn_cjk.yaml}"
[ -f "$DEFN_SRC" ] || c1_die "定义文件不存在: $DEFN_SRC"
DEFN_SRC="$(cd "$(dirname "$DEFN_SRC")" && pwd)/$(basename "$DEFN_SRC")"
DEFN_BASE="$(basename "$DEFN_SRC")"
# 包 04：定义闸门与引擎同源——_read_definition 单一来源（重复键/未知字段/
# 类型/patch_id 正则全部引擎裁决、带行号），样例不再 sed/grep 文本截取。
# 闸门输出 JSON {"patch_id","cjk"}；失败时引擎错误原样过 stderr 并退出。
GATE_JSON="$("$PY" "$C1_SAMPLE_DIR/defn_gate.py" "$DEFN_SRC")"
PATCH_ID="$(printf '%s' "$GATE_JSON" | "$PY" -c 'import json,sys; print(json.load(sys.stdin)["patch_id"])')"
CJK_FLAG="$(printf '%s' "$GATE_JSON" | "$PY" -c 'import json,sys; print("1" if json.load(sys.stdin)["cjk"] else "0")')"
echo "[c1-cjk] 定义: $DEFN_BASE (patch_id=$PATCH_ID, cjk=$CJK_FLAG → 引擎同源闸门)"
if [ "$CJK_FLAG" = "1" ]; then
  echo "[c1-cjk] cjk=true → 字体资产闸门"
  c1_ensure_cjk_assets
else
  echo "[c1-cjk] cjk=false → 免字体/Pillow/numpy"
fi
c1_check_baseline

UTC_START="$(c1_now)"
if [ -z "$OUT" ]; then
  RUNS_ROOT="${DL_C1_RUNS:-${TMPDIR:-/tmp}/dl_c1_runs}"
  OUT="$RUNS_ROOT/$(date -u +"%Y%m%dT%H%M%SZ")"
fi
[ -e "$OUT" ] && c1_die "运行目录已存在（每次运行必须全新目录）: $OUT"
mkdir -p "$OUT"

# 失败留痕：半成品目录带 FAILED 标记，交接时可见（不静默）。
# EXIT trap 覆盖 set -e 中止与 c1_die 的显式 exit 1（旧 ERR trap 漏掉后者）。
# 注意先捕 rc 再做命令替换——$(c1_now) 会重置 $?。
RUN_DIR="$OUT"
trap 'rc=$?; if [ "$rc" -ne 0 ]; then echo "prepare 于 $(c1_now) 失败（rc=${rc}）——现场保留于 ${RUN_DIR}" > "$RUN_DIR/FAILED"; fi' EXIT

cp "$DEFN_SRC" "$RUN_DIR/$DEFN_BASE"
cp "$C1_REPO_ROOT/game.ios" "$RUN_DIR/game.ios"
COPIED_MD5="$(md5 -q "$RUN_DIR/game.ios")"
[ "$COPIED_MD5" = "$C1_BASELINE_MD5" ] || c1_die "副本指纹不符: $COPIED_MD5"
BASELINE_SHA="$(shasum -a 256 "$RUN_DIR/game.ios" | awk '{print $1}')"

echo "== [P1] 基线副本: $RUN_DIR/game.ios (md5 $COPIED_MD5) =="
c1_run_cli --action storyline-plan --file data_win \
  --value "$RUN_DIR/$DEFN_BASE" --dir "$RUN_DIR/game.ios" --json \
  > "$RUN_DIR/plan.json" 2> "$RUN_DIR/plan.err"
echo "  plan rc=0 → plan.json（期望资源/结构集）"

echo "== [P2] storyline-build（工作区 c1_cjk；cjk → 字体栈注入） =="
c1_run_cli --action storyline-build --value "$RUN_DIR/$DEFN_BASE" \
  --workspace c1_cjk --dir "$RUN_DIR/game.ios" --json \
  > "$RUN_DIR/build.out.json" 2> "$RUN_DIR/build.err"
echo "  build rc=0 → build.out.json（构建回执：产物 sha256/声明差异）"

echo "== [P3] storyline-apply 预览 =="
c1_run_cli --action storyline-apply --value "$RUN_DIR/$DEFN_BASE" \
  --workspace c1_cjk --dir "$RUN_DIR/game.ios" --json \
  > "$RUN_DIR/apply_preview.json" 2> "$RUN_DIR/apply.err"
echo "  预览 rc=0 → apply_preview.json"

echo "== [P4] storyline-apply --commit（显式 --no-steam-sync：副本零 Steam 波及） =="
c1_run_cli --action storyline-apply --value "$RUN_DIR/$DEFN_BASE" \
  --workspace c1_cjk --dir "$RUN_DIR/game.ios" --commit --no-steam-sync --json \
  > "$RUN_DIR/apply_commit.json" 2> "$RUN_DIR/apply_commit.err"

AFTER_MD5="$(md5 -q "$RUN_DIR/game.ios")"
AFTER_SHA="$(shasum -a 256 "$RUN_DIR/game.ios" | awk '{print $1}')"
UTC_END="$(c1_now)"

# run.json：构建指纹 + 交接信息（机器可读；值含路径空格由 python 转义）。
PY="$PY" RUN_DIR="$RUN_DIR" UTC_START="$UTC_START" UTC_END="$UTC_END" \
BASELINE_SHA="$BASELINE_SHA" AFTER_MD5="$AFTER_MD5" AFTER_SHA="$AFTER_SHA" \
C1_DOTNET="${C1_DOTNET:-}" UTMT_CLI="$UTMT_CLI" PY_VER="$PY_VER" \
DEFN_BASE="$DEFN_BASE" PATCH_ID="$PATCH_ID" CJK_FLAG="$CJK_FLAG" \
"$PY" - <<'PYEOF'
import json, os, pathlib
rd = pathlib.Path(os.environ["RUN_DIR"])

def load(path):
    # 上游（cmd_cjk_font / sandbox-restore）会向 stdout 混入进度行，
    # --json 产物非纯 JSON——从首个 '{' 起解析（进度行不含 '{'，防御不裁上游）
    text = (rd / path).read_text(encoding="utf-8")
    idx = text.find("{")
    if idx < 0:
        raise ValueError(f"{path} 中找不到 JSON 对象")
    return json.loads(text[idx:])

def sha(path, key):
    return load(path)[key]
defn_sha = sha("build.out.json", "defn_sha256")
product_sha = sha("build.out.json", "product_sha256")
before_sha = sha("apply_commit.json", "baseline_sha256")
after_receipt_sha = sha("apply_commit.json", "after_sha256")
manifest = {
    "sample": "c1-cjk",
    "patch_id": os.environ["PATCH_ID"],
    "cjk": os.environ["CJK_FLAG"] == "1",
    "status": "prepared",
    "created_utc": os.environ["UTC_START"],
    "prepare_finished_utc": os.environ["UTC_END"],
    "python": f"{os.environ['PY']} ({os.environ['PY_VER']})",
    "dotnet": os.environ["C1_DOTNET"],
    "utmt_cli": os.environ["UTMT_CLI"],
    "baseline": {"md5": "fc049850856dea4ef1427bbf5653fc47",
                 "sha256": os.environ["BASELINE_SHA"]},
    "defn": {"file": os.environ["DEFN_BASE"], "sha256": defn_sha},
    "stages": {"prepare": {
        "started_utc": os.environ["UTC_START"],
        "finished_utc": os.environ["UTC_END"],
        "rc": 0,
        "artifacts": ["plan.json", "build.out.json", "apply_preview.json",
                      "apply_commit.json"],
        "workspace": "c1_cjk",
        "product_sha256": product_sha,
        "applied": {"before_sha256": before_sha,
                    "after_sha256": after_receipt_sha,
                    "after_md5": os.environ["AFTER_MD5"]},
        "apply_receipt": ".deterline/storyline/game.ios/"
                         + os.environ["PATCH_ID"] + "/receipt.json",
    }},
}
(rd / "run.json").write_text(
    json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
PYEOF

cat <<EOF
== [P5] 准备完成——材料就位，等待显式验收/撤销 ==
  运行目录: $RUN_DIR
  状态: 已应用（副本内 patched；apply 回执含 before/after 指纹）
  下一步（时点由操作者决定）:
    · 本地验收:  samples/c1-cjk/verify.sh "$RUN_DIR"
    · 显式撤销:  samples/c1-cjk/undo.sh  "$RUN_DIR"
    · 实机窗口（仅用户值守）: 见 README「实机窗口」节
EOF
