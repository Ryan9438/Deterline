"""任务状态机（16 号计划包 16）——声明层的纯模型模拟器。

对 v2 定义 ``states`` 块（合同见 storyline._validate_states）做确定性
模拟：有限输入序列 → 逐步记录（状态转换 / 诊断 / 实例层事件），同输入
恒同轨迹（可重放）。本模块只建模不触产物——产物侧守卫与旗标写入是
包 18 候选（默认不接线）。

三层持久语义（计划包 16/17：分清实例自毁、房间内状态、存档持久状态）：
- **实例层** alive：once=true 的 npc 触发后自毁；重进房间或读档后实例
  重建（重新可用）。对应产物 instance_destroy() 语义（npc.py 包 12）。
- **会话层** state：状态机当前态。换房/重进不丢；persistence=session 时
  读档即丢失（无投影 → 回 initial）。
- **旗标层** codes：persistence=flag 时状态以整数 code 投影到 flag_id
  （存档持久）。投影映射依据与往返核验在包 17（合成存档）。

触发分派（合同层已静态消歧）：匹配 (npc, answer) 且守卫满足（require ==
当前态，或无守卫）的 enter 至多一个 → 转换；无候选 = 原地不动 + 可解释
诊断（无声明 vs 守卫未满足分开说明）。
"""

__all__ = ["QuestMachine"]


def _pkg():
    """运行时取本包模块（跨模块引用一律运行时属性查找——包纪律，
    同 commands._pkg）。"""
    import sys as _sys
    return _sys.modules[__package__]


class QuestMachine:
    """从已载入的 v2 定义构造状态机并模拟轨迹。

    defn 须经过 storyline 载入（states 块已规范化：
    {"persistence", "initial", "map"}）。结构性错误在合同层已拒绝；
    本层仅拒绝「无 states 块」与「触发引用未声明 npc / 选择 npc 缺
    answer / 纯对话 npc 带 answer」这类调用侧形态错误（fail-closed）。
    """

    def __init__(self, defn: dict):
        st = defn.get("states")
        if not st or "map" not in st:
            raise _pkg().StorylineError(
                "QuestMachine 需要声明 states 块的 v2 定义"
                "（load_definition 载入；无状态机场景不需要模拟）")
        self.persistence: str = st["persistence"]
        self.initial: str = st["initial"]
        self.states: dict[str, dict] = st["map"]
        self.npc_kind: dict[str, str] = {
            nid: ("choice" if "\\C" in spec["prompt"] else "talk")
            for nid, spec in (defn.get("npcs") or {}).items()}
        self.npc_once: dict[str, bool] = {
            nid: bool(spec.get("once", True))
            for nid, spec in (defn.get("npcs") or {}).items()}
        self.codes: dict[str, int] = {
            sid: s["code"] for sid, s in self.states.items() if "code" in s}
        self.by_code: dict[int, str] = {c: s for s, c in self.codes.items()}
        self.trace: list[dict] = []
        self.state: str = self.initial
        self.alive: dict[str, bool] = {nid: True for nid in self.npc_kind}
        self.last_save_code: int | None = None

    # ---- 输入字母表（有限）------------------------------------

    def trigger(self, npc: str, answer: str | None = None) -> dict:
        """触发 npc（进入范围并交互）。选择 npc 必须给 answer∈{yes,no}。"""
        if npc not in self.npc_kind:
            raise _pkg().StorylineError(
                f"trigger 引用未声明 npc '{npc}'（已有: {sorted(self.npc_kind)}）")
        if self.npc_kind[npc] == "choice":
            if answer not in ("yes", "no"):
                raise _pkg().StorylineError(
                    f"npc '{npc}' 为选择 npc——trigger 必须给 answer='yes'|'no'")
        elif answer is not None:
            raise _pkg().StorylineError(
                f"npc '{npc}' 为纯对话 npc——trigger 不带 answer")
        rec: dict = {"event": "trigger", "npc": npc, "answer": answer,
                     "from": self.state}
        if not self.alive.get(npc, True):
            rec["to"] = self.state
            rec["diagnostic"] = (f"npc '{npc}' 实例已自毁（once=true）——"
                                 "重进房间后重新可用")
        else:
            matches = [sid for sid, s in self.states.items()
                       if s.get("enter", {}).get("npc") == npc
                       and s.get("enter", {}).get("answer") == answer
                       and (s.get("require") is None
                            or s.get("require") == self.state)]
            # 合同层静态消歧（同触发键全守卫互异）保证至多一个候选
            if matches:
                self.state = matches[0]
            else:
                declared = [sid for sid, s in self.states.items()
                            if s.get("enter", {}).get("npc") == npc
                            and s.get("enter", {}).get("answer") == answer]
                if not declared:
                    rec["diagnostic"] = (
                        f"触发 (npc={npc}, answer={answer}) 无任何状态声明 "
                        "enter——无转换")
                else:
                    guards = {sid: self.states[sid].get("require")
                              for sid in declared}
                    rec["diagnostic"] = (
                        f"当前态 '{self.state}' 不满足守卫 {guards}——"
                        f"npc '{npc}' 触发不改变状态")
            rec["to"] = self.state
            if self._npc_once(npc):
                self.alive[npc] = False
                rec["note"] = "实例自毁（once=true）——本房间进入内不再触发"
        return self._append(rec)

    def reenter(self, room: str | None = None) -> dict:
        """重进房间：实例层重建（自毁 npc 重新可用），会话层状态保持。"""
        rearmed = sorted(n for n, a in self.alive.items() if not a)
        self.alive = {n: True for n in self.alive}
        rec: dict = {"event": "reenter", "room": room,
                     "from": self.state, "to": self.state}
        if rearmed:
            rec["note"] = f"实例层重建——重新可用: {rearmed}"
        else:
            rec["note"] = "实例层重建（无待重臂的自毁实例）"
        return self._append(rec)

    def save(self) -> dict:
        """存档：flag 持久化时状态投影为旗标值；session 态无投影。"""
        rec: dict = {"event": "save", "from": self.state, "to": self.state}
        if self.persistence == "flag":
            code = self.codes[self.state]
            self.last_save_code = code
            rec["projected_code"] = code
        else:
            rec["projected_code"] = None
            rec["diagnostic"] = (
                f"persistence=session：状态 '{self.state}' 无存档投影"
                "（读档后将丢失——产物接线为包 18 候选）")
        return self._append(rec)

    def load(self, code: int | None = None) -> dict:
        """读档：flag 持久化按旗标值回读状态；session 态随读档丢失。

        旗标值无对应状态（占用漂移/外部写入）时 fail-safe 回 initial
        并给出诊断；无任何可用投影码属于调用侧轨迹不完整，拒绝。
        """
        rec: dict = {"event": "load", "from": self.state}
        if code is None:
            code = self.last_save_code
        if self.persistence == "flag" and code is None:
            raise _pkg().StorylineError(
                "load 需要投影码：先 save 或显式传 code"
                "（读档轨迹必须有存档来源）")
        if self.persistence == "flag":
            dest = self.by_code.get(code)
            if dest is None:
                self.state = self.initial
                rec["diagnostic"] = (
                    f"旗标值 {code} 无对应状态（占用漂移或外部写入）——"
                    f"fail-safe 回 initial '{self.initial}'")
            else:
                self.state = dest
        else:
            self.state = self.initial
            rec["diagnostic"] = (
                "persistence=session：会话态随读档丢失——回 initial "
                f"'{self.initial}'")
        self.alive = {n: True for n in self.alive}
        rec["to"] = self.state
        rec["restored_code"] = code
        return self._append(rec)

    # ---- 内部 --------------------------------------------------

    def _npc_once(self, npc: str) -> bool:
        return bool(self.npc_once.get(npc, True))

    def _append(self, rec: dict) -> dict:
        rec["step"] = len(self.trace) + 1
        self.trace.append(rec)
        return rec

    def render_trace(self) -> str:
        """可读轨迹（四条标准轨迹的可重放呈现；诊断行带 ⚠ 标记）。"""
        lines = []
        for rec in self.trace:
            ev = rec["event"]
            head = f"#{rec['step']:02d} {ev}"
            if ev == "trigger":
                head += f" npc={rec['npc']}"
                if rec.get("answer"):
                    head += f" answer={rec['answer']}"
            elif ev == "reenter" and rec.get("room"):
                head += f" room={rec['room']}"
            line = f"{head}: {rec['from']} → {rec['to']}"
            if rec.get("note"):
                line += f" ［{rec['note']}］"
            if rec.get("diagnostic"):
                line += f" ⚠ {rec['diagnostic']}"
            lines.append(line)
        return "\n".join(lines)
