#!/bin/bash
# c1-cjk 样例共享库：环境 preflight + 路径/解释器解析。
# 三阶段脚本（prepare/verify/undo）皆 source 本文件。
# 设计约束见 samples/c1-cjk/README.md（14 手册 §1：准备/验收/撤销拆解）。

# 本样例钉死的基线指纹（rc6 检出的 game.ios；与 HANDOFF/ROUND_PROMPT 同源）。
C1_BASELINE_MD5="fc049850856dea4ef1427bbf5653fc47"
C1_FONT_REL="assets/fonts/vendor/fusion-pixel-12px/fusion-pixel-12px-monospaced-zh_hans.ttf"
C1_FONT_MD5="0349f9f173558216daa5a9579537da8a"

c1_die() { echo "✗ [c1-cjk] $*" >&2; exit 1; }
c1_now() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }

# 解析样例目录与检出根（脚本自身位置 = <root>/samples/c1-cjk/）。
c1_resolve_repo() {
  C1_SAMPLE_DIR="$(cd "$(dirname "${BASH_SOURCE[1]}")" && pwd)"
  C1_REPO_ROOT="$(cd "$C1_SAMPLE_DIR/../.." && pwd)"
  [ -f "$C1_REPO_ROOT/run.py" ] || c1_die "检出根解析失败（无 run.py）: $C1_REPO_ROOT"
  [ -f "$C1_REPO_ROOT/game.ios" ] || c1_die "基线缺失: $C1_REPO_ROOT/game.ios"
}

# 解释器选择：DL_PYTHON 显式指定 > 逐候选探测；须 ≥3.10
#（deterline 包含 `X | None` 模块级注解，3.9 在导入期即 TypeError——
# 本机 python3=3.9.6 的实际卡点，见 README「已知卡点」）。
c1_pick_python() {
  local cands=() c v ok
  if [ -n "${DL_PYTHON:-}" ]; then
    cands=("$DL_PYTHON")
  else
    cands=(python3.14 python3.13 python3.12 python3.11 python3)
  fi
  PY=""
  for c in "${cands[@]}"; do
    command -v "$c" >/dev/null 2>&1 || continue
    if "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)' 2>/dev/null; then
      PY="$c"
      PY_VER="$("$c" -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
      return
    fi
  done
  c1_die "未找到 Python ≥3.10（候选: ${cands[*]}）。可用 DL_PYTHON=/path/to/python 指定。"
}

# UTMT CLI 解析：UTMT_CLI 显式指定 > 常见候选路径。data_win 全链路依赖。
c1_pick_utmt_cli() {
  if [ -n "${UTMT_CLI:-}" ] && [ -f "$UTMT_CLI" ]; then export UTMT_CLI; return; fi
  local home_candidates=(
    "$HOME/UndertaleModTool/UndertaleModCli/bin/Release/net10.0/UndertaleModCli.dll"
    "$HOME/UndertaleModTool/UndertaleModCli/bin/Release/net9.0/UndertaleModCli.dll"
    "$HOME/UndertaleModTool/UndertaleModCli/bin/Release/net8.0/UndertaleModCli.dll"
  )
  local c
  for c in "${home_candidates[@]}"; do
    if [ -f "$c" ]; then UTMT_CLI="$c"; export UTMT_CLI; return; fi
  done
  c1_die "未找到 UndertaleModCli.dll。设置 UTMT_CLI=/path/to/UndertaleModCli.dll" \
         "（下载/编译: https://github.com/UnderminersTeam/UndertaleModTool）"
}

# dotnet 解析：LaunchAgent 最小 PATH（~/.local/bin:/usr/bin:/bin:…）不含
# Homebrew——本机卡点。缺 dotnet 时补 /opt/homebrew/bin 再试，命中则留痕。
c1_ensure_dotnet() {
  if command -v dotnet >/dev/null 2>&1; then C1_DOTNET="$(command -v dotnet)"; return; fi
  if [ -x /opt/homebrew/bin/dotnet ]; then
    export PATH="/opt/homebrew/bin:$PATH"
    C1_DOTNET="/opt/homebrew/bin/dotnet"
    C1_DOTNET_PATCHED=1
    return
  fi
  c1_die "未找到 dotnet（.NET runtime，UTMT CLI 依赖）。安装: brew install dotnet"
}

# CJK 构建依赖（storyline cjk:true 的字体管线）：Pillow + numpy + vendor 字体。
# 字体按 .gitignore 口径不入库——干净检出自备（来源与 md5 见 README）。
c1_ensure_cjk_assets() {
  if ! "$PY" -c "import PIL" >/dev/null 2>&1; then
    c1_die "当前解释器缺 Pillow（CJK 字形页生成依赖，requirements.txt）。" \
      "修法: $PY -m venv <dir> && <dir>/bin/pip install pillow numpy" \
      "然后 DL_PYTHON=<dir>/bin/python 重跑。"
  fi
  # numpy 闸门（R31 P2 清偿）：font_emb20_compose 的图集合成依赖 numpy，
  # run1 实跑证明缺它在完整 pass1 之后才炸 ModuleNotFoundError——预检必须提前拦。
  if ! "$PY" -c "import numpy" >/dev/null 2>&1; then
    c1_die "当前解释器缺 numpy（emb20 图集合成依赖，requirements.txt 已登记）。" \
      "修法: $PY -m venv <dir> && <dir>/bin/pip install pillow numpy" \
      "然后 DL_PYTHON=<dir>/bin/python 重跑。"
  fi
  local font="$C1_REPO_ROOT/$C1_FONT_REL"
  [ -f "$font" ] || c1_die "OFL 字体源缺失: $font" \
    "（vendor 字体不入库；获取与校验口径见 README「前置条件」）"
  local got; got="$(md5 -q "$font")"
  [ "$got" = "$C1_FONT_MD5" ] || c1_die "字体指纹不符: $font 得 $got 期望 $C1_FONT_MD5"
}

# 基线守门：样例一切操作只对运行目录副本，源 game.ios 必须是已知干净基线。
c1_check_baseline() {
  local got; got="$(md5 -q "$C1_REPO_ROOT/game.ios")"
  [ "$got" = "$C1_BASELINE_MD5" ] || c1_die \
    "检出基线漂移: $C1_REPO_ROOT/game.ios md5=$got 期望=$C1_BASELINE_MD5" \
    "（样例定义钉在 rc6 基线；先恢复检出再跑）"
}

# 全量 preflight（三脚本共用序言；verify/undo 不需要 CJK 资产）。
c1_preflight_core() {
  c1_resolve_repo
  c1_pick_python
  c1_ensure_dotnet
  c1_pick_utmt_cli
  c1_check_baseline
  echo "[c1-cjk] python=$PY ($PY_VER) dotnet=$C1_DOTNET"
  echo "[c1-cjk] UTMT_CLI=$UTMT_CLI"
}

# 统一的 CLI 调用形态：解释器 + run.py，全部显式 --dir（零隐式定位）。
c1_run_cli() { "$PY" "$C1_REPO_ROOT/run.py" "$@"; }
