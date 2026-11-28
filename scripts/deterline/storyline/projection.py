"""存档投影（16 号计划包 17）——v2 状态机到 file0 的映射与占用守卫。

映射依据（反编译取证，本基线 fc049850，证据 /tmp/dl16w1/dump17/，实录存档）：
- ``gml_Script_scr_saveprocess``：file0 写出序 = 名字行 + lv(0)..kills(10)
  + item/phone 交替 16 项(11-26) + weapon(27) + armor(28) +
  **flag[0..511]（位 29-540）** + plot(541) + menuchoice[0..2]（542-544）+
  currentsong(545) + currentroom(546) + time(547)——数值共 548 个。
- ``gml_Script_scr_load`` 对称读回；读后强制清零 flag[94] / flag[360..364]
  （读档覆盖行为——旗标载体避开）。
- **flag[512..999] 不入存档**（save 循环上界 i<512）——运行时旗标；
  ``29+flag_id`` 对 flag≥512 会越位踩 plot/menuchoice/currentroom 等槽，
  投影层硬拒绝（写前拒绝，不伪造字段）。
- 持久区 [500,511] 全部 12 槽被游戏代码静态引用（占用普查：全部 6272 个
  代码条目反编译后字面量扫描 ``global.flag[N]``；计算索引访问不可静态
  归因——登记限制）。menuchoice[0..2]（542-544）同样被占用（SCR_GAMESTART
  清零 + obj_overworldcontroller_Draw_0 每帧读取 + torieltrigger4 写
  menuchoice[2]）——本基线无净空持久旗标槽，存档持久任务状态无安全载体；
  包 18 接线以运行时旗标（513-999 无静态引用）为 session 级载体。
"""

from pathlib import Path

from .. import errors, file0


def _pkg():
    """运行时取本包模块（跨模块引用一律运行时属性查找——包纪律，同 commands）。"""
    import sys as _sys
    return _sys.modules[__package__]

FLAG_SAVE_BASE = 29            # scr_saveprocess：flag[0] 位于 file0 第 29 位
PERSISTED_FLAG_MAX = 511       # save 循环上界 i<512——512+ 运行时旗标不入存档
FILE0_NUMBER_COUNT = 548       # 数值行总数（0..547；名字行不计入）

# 持久区 [500,511] 逐槽占用（反编译字面量扫描，脚本族名精简；512 为运行时
# 占用——SCR_GAMESTART 清零 + 结局/credits 脚本引用）
PERSISTED_ZONE_OCCUPANCY: dict[int, list[str]] = {
    500: ["scr_battlegroup", "obj_asrielb", "obj_heartdefeated"],
    501: ["SCR_TEXT", "scr_battlegroup", "obj_asrielfinal",
          "obj_asrielpanels", "obj_asbulletparent"],
    502: ["obj_asriel_body", "obj_roundedge", "obj_heartdefeated"],
    503: ["scr_itemuseb"],
    504: ["obj_asrielb"],
    505: ["SCR_TEXT", "obj_ripoff_undyne", "obj_asrielfinal"],
    506: ["SCR_TEXT", "obj_ripoff_alphys", "obj_asrielfinal"],
    507: ["SCR_TEXT", "obj_ripoff_papyrus", "obj_asrielfinal"],
    508: ["SCR_TEXT", "obj_ripoff_toriel", "obj_asrielfinal"],
    509: ["scr_binfowrite", "obj_lastbeam", "obj_friendc"],
    510: ["obj_friendc", "obj_asriel_overworldanim"],
    511: ["obj_torinteractable7"],
    512: ["SCR_GAMESTART(清零)", "obj_outsideworld", "obj_the_end_really",
          "obj_creditsloader"],
}


def flag_slot(flag_id: int) -> int:
    """运行时旗标号 → file0 槽位（29+flag）。仅持久区 [500,511] 合法：
    512+ 不入存档且映射越位（踩 plot/menuchoice/currentroom），写前拒绝。"""
    if not isinstance(flag_id, int) or isinstance(flag_id, bool):
        raise errors.ValidationError(f"flag_id 必须是整数（收到 {flag_id!r}）")
    if not (500 <= flag_id <= PERSISTED_FLAG_MAX):
        raise errors.ValidationError(
            f"flag_id={flag_id} 不可投影——scr_saveprocess 只持久化 "
            f"flag[0..{PERSISTED_FLAG_MAX}]（{FLAG_SAVE_BASE}+flag 位映射仅对 "
            f"500-{PERSISTED_FLAG_MAX} 成立）；512+ 为运行时旗标不入存档，"
            "且 29+flag 位映射会越位踩 plot/menuchoice/currentroom（包 17）")
    return FLAG_SAVE_BASE + flag_id


def check_flag_occupancy(flag_id: int) -> list[str]:
    """占用诊断（普查口径：反编译字面量扫描；非投影闸门——投影层用
    flag_slot 范围守卫）。返回引用脚本族清单；空 = 无静态引用。"""
    return list(PERSISTED_ZONE_OCCUPANCY.get(flag_id, []))


def project_state(defn: dict, state_id: str) -> dict[int, int]:
    """状态 → 存档投影（{"flag_id": code}）。仅 persistence=flag 的 v2
    定义有投影；session 机器无存档投影（显式拒绝，不静默空投影）。"""
    st = defn.get("states") or {}
    if st.get("persistence") != "flag":
        raise _pkg().StorylineError(
            f"状态 '{state_id}' 无存档投影——persistence=session 的机器"
            "不写入存档（会话态，包 16 三层语义）")
    spec = st["map"].get(state_id)
    if spec is None:
        raise _pkg().StorylineError(
            f"状态 '{state_id}' 未在 states 块声明（已有: {sorted(st['map'])}）")
    if "code" not in spec:
        raise _pkg().StorylineError(f"状态 '{state_id}' 未声明 code（投影必需）")
    return {defn["flag_id"]: spec["code"]}


def read_state(defn: dict, flag_value: int) -> str | None:
    """旗标值 → 状态 id（回读）。未知值返回 None（fail-safe 判定由调用方
    定——模型层 QuestMachine.load 回 initial + 诊断）。"""
    codes = {s["code"]: sid for sid, s in (defn.get("states") or {})
             .get("map", {}).items() if "code" in s}
    return codes.get(flag_value)


def read_flag(save_dir: Path, flag_id: int) -> int:
    """读合成存档中 flag_id 的当前值（槽位越界 = 存档不完整，拒绝）。"""
    slot = flag_slot(flag_id)
    name, nums = file0._parse_file0(Path(save_dir) / "file0")
    if slot >= len(nums):
        raise errors.ValidationError(
            f"file0 长度 {len(nums)} 不含槽位 {slot}（flag {flag_id}）——"
            "存档不完整，拒绝（不补零伪造字段）")
    return nums[slot]


def apply_flag_writes(save_dir: Path, writes: dict[int, int]) -> dict:
    """把 {"flag_id": code} 投影写入合成存档 file0（槽位级差异回执）。

    fail-closed：非持久区旗标拒绝；槽位超出存档长度拒绝（不补零）；
    值须为 0-999 整数（旗标值域）。返回 {"flag_id": (before, after)}。
    """
    path = Path(save_dir) / "file0"
    name, nums = file0._parse_file0(path)
    result: dict[int, tuple[int, int]] = {}
    for flag_id, value in sorted(writes.items()):
        slot = flag_slot(flag_id)
        if not isinstance(value, int) or isinstance(value, bool) \
                or not (0 <= value <= 999):
            raise errors.ValidationError(
                f"flag {flag_id} 投影值 {value!r} 越界——须为 0-999 整数"
                "（旗标值域合同）")
        if slot >= len(nums):
            raise errors.ValidationError(
                f"file0 长度 {len(nums)} 不含槽位 {slot}（flag {flag_id}）——"
                "存档不完整，拒绝（不补零伪造字段）")
        result[flag_id] = (nums[slot], value)
        nums[slot] = value
    file0._write_file0(path, name, nums)
    return result
