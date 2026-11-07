
int bad = 0;
int fixedCnt = 0;
for (int i = 0; i < Data.Variables.Count; i++)
{
    var v = Data.Variables[i];
    string vname = v.Name?.Content ?? "";
    if (vname.Length == 0) continue;
    bool corrupt = v.NameStringID <= 0 && v.Occurrences > 0;
    if (v.NameStringID > 0)
    {
        // Sanity: NSID must point back to the same name in the STRG table.
        var pointed = (v.NameStringID < Data.Strings.Count) ? (Data.Strings[v.NameStringID]?.Content ?? "") : "";
        if (pointed != vname) corrupt = true;
    }
    if (corrupt)
    {
        int correct = Data.Strings.IndexOf(v.Name);
        bad++;
        if (false)
        {
            v.NameStringID = correct;
            fixedCnt++;
        }
        ScriptMessage("BAD_NSID: name='" + vname + "' nsid=" + v.NameStringID + " occ=" + v.Occurrences + " correct=" + correct + " fixed=" + (false));
    }
}
ScriptMessage("VERIFY_NSID:bad=" + bad + " fixed=" + fixedCnt);
