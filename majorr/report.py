from datetime import datetime


def to_markdown(report):
    out = ["# Fault Localization and Self-Validated Repair Report",
           f"Repository: {report['repo']}",
           f"Generated: {datetime.now():%Y-%m-%d %H:%M}",
           f"Files analyzed: {report['files_analyzed']}  |  Code chunks indexed: {report['chunks_indexed']}",
           "", "## Errors detected"]
    if not report["errors_found"]:
        out.append("No errors detected.")
    for e in report["errors_found"]:
        out.append(f"- `{e['file']}` line {e['line']} [{e['kind']}]: {e['message']}")

    for i, r in enumerate(report["repairs"], 1):
        t = r["target"]
        out += ["", f"## Repair {i}: {t['file']} line {t['line']}",
                f"Status: **{r['status']}** after {r['attempts']} step(s)"]
        if r.get("cause"):
            out += ["", f"**Cause:** {r['cause']}"]
        if r.get("explanation"):
            out += ["", r["explanation"]]
        if r.get("diff"):
            out += ["", "**Corrected code (diff)**", "```diff", r["diff"], "```"]
        if r.get("steps"):
            out += ["", "**Agent steps**"] + [f"- {s['action']}: {s['detail']}" for s in r["steps"]]
        if r.get("context"):
            out += ["", "**Retrieved code context**"]
            for h in r["context"]:
                out += [f"- `{h['file']}` ({h['name']}, lines {h['start']}-{h['end']}, score {h['score']})",
                        "```python", h["code"], "```"]

    out += ["", f"## Errors remaining after repair: {len(report['remaining_errors'])}"]
    for e in report["remaining_errors"]:
        out.append(f"- `{e['file']}` line {e['line']}: {e['message']}")
    return "\n".join(out) + "\n"