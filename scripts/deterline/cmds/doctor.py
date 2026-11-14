"""doctor 聚合体检（O2 后收编，风险席路线图 B1 项：2026-11-11 落地）。

只读聚合：rooms.json 健康 / 存档文件可解析 / 游戏文件 md5 与基线比对 /
备份占盘盘点 / 沙箱残留提醒 / UTMT CLI 与 dotnet 可达 / CJK 字形表状态。
零 UTMT 子进程、零写盘（全部读取）——deep 验证（verify-code/smoke-test）
仍是独立命令，本命令只做"开机体检"。

退出码：全部 ✓ 0 / 任一 ✗ 1。
跨模块一律模块属性形式：paths./rooms_data./file0./inifile./utmt./errors.
"""

import configparser
import json
import shutil
import sys
from pathlib import Path

from .. import file0, paths, rooms_data, utmt

_ROOT = Path(__file__).resolve().parents[3]  # doctor: 仓库根（基线/字形表）


def cmd_doctor(save_dir: Path, dir_override: str | None = None,
               json_out: bool = False,
               save_dir_error: str | None = None) -> None:
    """聚合体检（全部只读）。--dir 走 find_save_dir 语义。

    --json（v2.5.5）：stdout 纯 JSON（schema deterline.doctor/v1，items 为
    逐项 {label, ok, detail}）；人读各行不再打印（stderr 保持静默）。
    退出码语义不变：任一 ✗ → 1。
    """
    fails = 0
    items: list[dict] = []

    def check(label: str, ok: bool, detail: str = "") -> None:
        nonlocal fails
        items.append({"label": label, "ok": ok, "detail": detail})
        if not ok:
            fails += 1  # 计数必须先于 json 分支（v2.5.5 自纠：曾只在人读分支计数）
        if json_out:
            return
        mark = "✓" if ok else "✗"
        print(f"  {mark} {label}" + (f" — {detail}" if detail else ""))

    if not json_out:
        print("--- doctor（只读体检） ---")

    # 0. 存档目录定位（None = 定位失败，由调用方打印 ✗；此处跳过存档项）
    check("存档目录定位", save_dir is not None,
          str(save_dir) if save_dir is not None else (save_dir_error or ""))

    # 1. rooms.json（路径复用 rooms_data 单点，不新增模块路径位点）
    rooms_json = rooms_data._rooms_json_path()  # noqa: 私有复用（同包）
    try:
        # 直接 json.load 判定（rooms_data._load_rooms 会把损坏吞成空表，
        # 复核 P2-1：损坏文件误报"✓ 0 条"）；解析成功后再经 _load_rooms 供后续
        raw = json.loads(rooms_json.read_text(encoding="utf-8")) if rooms_json.exists() else {}
        is_map = isinstance(raw, dict)  # B P2-4：非 dict 形态（如 list）不得 ✓
        n = len(raw) if is_map else 0
        if is_map and raw:
            detail = ""
        elif not raw:
            detail = "文件缺失或内容为空"
        else:
            detail = f"非映射形态（{type(raw).__name__}）——应为 id→中文名 dict"
        check(f"rooms.json 可解析（{n} 条）", is_map and bool(raw), detail)
        rooms_data._load_rooms()
    except Exception as e:  # noqa: BLE001 — 体检命令吞异常改为 ✗ 行
        check("rooms.json 可解析", False, str(e)[:80])

    # 2. 存档文件
    if save_dir is None:
        check("file0 可解析", False, "存档目录未定位")
        check("undertale.ini 可解析", False, "存档目录未定位")
    else:
        f0 = save_dir / "file0"
        ini = save_dir / "undertale.ini"
        try:
            name, nums = file0._parse_file0(f0)
            check(f"file0 可解析（玩家 {name}，{len(nums)} 变量）", True)
        except Exception as e:
            check("file0 可解析", False, str(e)[:80])
        # ⚠️ 只读解析：不走 inifile._read_ini——现行实现已零写盘（strict=False
        # 重读 + stderr 提示），但带 stderr 副作用且语义耦合；doctor 自持
        # configparser strict=False 读，零写盘零噪声（复核 P1-1 承诺不变；
        # B P3-8 注释订正——旧注释"会备份+改写 ini"与现行实现不符）
        try:
            cp = configparser.ConfigParser(strict=False)
            cp.read(str(ini), encoding="utf-8")
            dup = sum(len(cp.options(sec)) for sec in cp.sections())
            check(f"undertale.ini 可解析（{len(cp.sections())} 节 {dup} 键，strict=False 容忍重复键）", True)
        except Exception as e:
            check("undertale.ini 可解析", False, str(e)[:80])

    # 3. 游戏数据文件 + 基线比对（--dir 文件/含 game.ios 的目录双形态，
    #    与 md5/backup-index 同语义——v2.5.5 补齐 cli help 承诺）
    try:
        game_file = paths.resolve_game_data_file(dir_override)
    except FileNotFoundError as e:
        game_file = None
        check("游戏数据文件定位", False, str(e)[:80])
    if game_file is not None and not game_file.is_file():
        check("游戏数据文件定位", False, f"{game_file} 是目录不是文件（--dir 指向存档目录？）")
        game_file = None
    if game_file is not None:
        md5 = utmt._md5_file(game_file)
        baseline = _ROOT / "game.ios"
        if game_file.suffix == ".ios" and baseline.exists() and game_file.exists():
            same = md5 == utmt._md5_file(baseline)
            check(f"游戏文件与仓库基线比对", same,
                  f"{game_file.name} md5={md5[:12]}…" + ("" if same else "（≠基线——实验态属正常）"))
        else:
            check(f"游戏数据文件定位", True, f"{game_file}")

    # 4. 备份占盘（game 旁 + 存档目录）
    total = 0
    count = 0
    roots = [save_dir] if save_dir is not None else []
    if game_file is not None:
        roots.append(game_file.parent)
    for root in roots:
        for p in root.glob("*.bak*"):
            count += 1
            total += p.stat().st_size
    check(f"备份占盘盘点（{count} 个 .bak*，共 {total / 1e6:.0f} MB）", True,
          "≈250MB/个——长期不用可清" if count > 3 else "")

    # 5. 沙箱残留
    sandboxes = [p for root in roots for p in root.glob("*.sandbox")]
    if game_file is not None:
        workspaces = game_file.resolve().parent / ".deterline" / game_file.name
        sandboxes.extend(path for path in workspaces.glob(f"*/{game_file.name}") if path.is_file())
    check("实验工作区", True, f"{len(sandboxes)} 个副本" if sandboxes else "无")

    # 6. UTMT CLI + dotnet
    try:
        cli = utmt._find_utmt_cli()
        dotnet = shutil.which("dotnet")
        check("UTMT CLI 可达", bool(cli and Path(cli).exists() and dotnet),
              f"{cli}" + ("" if dotnet else "（dotnet 不在 PATH）"))
    except FileNotFoundError as e:
        check("UTMT CLI 可达", False, str(e)[:60])

    # 7. CJK 字形表
    glyphs = _ROOT / "build" / "font_cjk" / "glyphs.json"
    try:
        n = len(json.loads(glyphs.read_text(encoding="utf-8")))
        check(f"CJK 字形表（{n} 码点）", True,
              "full:false——二级字需 --full 重建（cjk-check 预检）")
    except FileNotFoundError:
        check("CJK 字形表", False, f"缺 {glyphs}——先跑 cjk-font")
    except Exception as e:  # noqa: BLE001 — 损坏 JSON 等也降级为 ✗ 行（复核 P2-2）
        check("CJK 字形表", False, str(e)[:80])

    if json_out:
        print(json.dumps({
            "schema": "deterline.doctor/v1",
            "save_dir": str(save_dir) if save_dir is not None else None,
            "items": items,
            "fails": fails,
        }, ensure_ascii=False, indent=2))
    else:
        print(f"--- 体检完成: {'全部通过 ✓' if fails == 0 else f'{fails} 项 ✗'} ---")
    if fails:
        sys.exit(1)
