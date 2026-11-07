
// Verify / fix room instance IDs across all rooms (experiment 19)
ulong maxUsed = 0;
var used = new System.Collections.Generic.HashSet<uint>();
foreach (var room in Data.Rooms)
{
    foreach (var g in room.GameObjects)
    {
        if (g.InstanceID != 0)
        {
            used.Add(g.InstanceID);
            if (g.InstanceID > maxUsed) maxUsed = g.InstanceID;
        }
    }
}
uint nextId = (uint)(System.Math.Max((long)Data.GeneralInfo.LastObj, (long)maxUsed) + 1);

int badZero = 0, badDup = 0, badNull = 0, badNonexist = 0, fixedCnt = 0;
var local = new System.Collections.Generic.HashSet<uint>();
foreach (var room in Data.Rooms)
{
    local.Clear();
    string roomName = room.Name?.Content ?? "(unnamed)";
    foreach (var g in room.GameObjects)
    {
        string objName = g.ObjectDefinition?.Name?.Content ?? "(null)";
        bool idZero = (g.InstanceID == 0);
        bool idDup = (!idZero && !local.Add(g.InstanceID));
        bool nullObj = (g.ObjectDefinition == null);
        bool nonexist = g.Nonexistent;
        if (idZero) badZero++;
        if (idDup) badDup++;
        if (nullObj) badNull++;
        if (nonexist) badNonexist++;
        if (idZero || idDup || nullObj || nonexist)
        {
            ScriptMessage("BAD_INSTANCE: room='" + roomName + "' obj=" + objName + " id=" + g.InstanceID + " x=" + g.X + " y=" + g.Y + " zero=" + idZero + " dup=" + idDup + " null=" + nullObj + " nonexist=" + nonexist);
        }
        if (false && (idZero || idDup))
        {
            g.InstanceID = nextId;
            nextId++;
            fixedCnt++;
        }
    }
}
if (false)
{
    Data.GeneralInfo.LastObj = nextId - 1;
}
int bad = badZero + badDup + badNull + badNonexist;
ScriptMessage("VERIFY_INSTANCES:bad=" + bad + " zero=" + badZero + " dup=" + badDup + " null=" + badNull + " nonexist=" + badNonexist + " fixed=" + fixedCnt);
