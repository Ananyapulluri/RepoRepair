import difflib
import json
import os
import time

import requests

from analysis import run_checks, error_key

MODELS = ["gemini-flash-latest", "gemini-3-flash-preview", "gemini-2.5-flash-lite"]
MAX_STEPS = 8

SYSTEM = """You are an autonomous debugging agent for a Python repository. Your job is to fix ONE reported error.
Reply with exactly one JSON object per turn and no other text. The allowed forms are:
{"action": "search_code", "query": "words or identifiers to look for"}
{"action": "read_file", "file": "relative/path.py", "start": 10, "end": 40}
{"action": "propose_fix", "cause": "root cause", "file": "relative/path.py", "original_code": "exact text copied from the file, appearing once", "fixed_code": "replacement text", "explanation": "one or two sentences"}
{"action": "give_up", "reason": "why no safe fix was found"}
Investigate with search_code and read_file before proposing a fix. Change only what is needed to fix this error. After a rejected fix, use the feedback to try a different approach."""


def ask_agent(history):
    last_problem = "no response"
    for model in MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        for attempt in range(3):
            try:
                resp = requests.post(
                    url,
                    params={"key": os.environ["GEMINI_API_KEY"]},
                    json={
                        "systemInstruction": {"parts": [{"text": SYSTEM}]},
                        "contents": history,
                        "generationConfig": {"responseMimeType": "application/json", "temperature": 0.2},
                    },
                    timeout=60,
                )
            except requests.exceptions.RequestException as exc:
                last_problem = f"{model}: connection problem ({exc})"
                time.sleep(5 * (attempt + 1))
                continue
            if resp.status_code in (429, 503):
                last_problem = f"{model}: {resp.status_code} busy"
                time.sleep(5 * (attempt + 1))
                continue
            if resp.status_code == 404:
                last_problem = f"{model}: not available for this key"
                break  # skip this model and try the next one
            resp.raise_for_status()
            text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
            return json.loads(text)
    raise RuntimeError(f"All models failed. Last problem: {last_problem}")


def safe_path(root, rel):
    base = os.path.realpath(root)
    path = os.path.realpath(os.path.join(root, rel))
    if not path.startswith(base + os.sep):
        raise ValueError("path is outside the repository")
    return path


def read_lines(root, rel, start=1, end=None):
    with open(safe_path(root, rel), encoding="utf-8", errors="ignore") as fh:
        lines = fh.read().splitlines()
    start = max(1, start)
    end = min(end or start + 59, start + 149, len(lines))
    return "\n".join(f"{i:>4}: {lines[i - 1]}" for i in range(start, end + 1))


def source_window(root, rel, line, radius=15):
    with open(safe_path(root, rel), encoding="utf-8", errors="ignore") as fh:
        lines = fh.read().splitlines()
    lo, hi = max(1, line - radius), min(len(lines), line + radius)
    window = "\n".join(f"{i:>4}: {lines[i - 1]}" for i in range(lo, hi + 1))
    return lo, hi, window


def apply_fix(root, rel, original, fixed):
    path = safe_path(root, rel)
    with open(path, encoding="utf-8") as fh:
        old = fh.read()
    count = old.count(original) if original else 0
    if count != 1:
        raise ValueError(f"original_code must appear exactly once; found {count} times")
    new = old.replace(original, fixed, 1)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(new)
    return path, old, new


def _failed(note, steps, context):
    return {"status": "failed", "attempts": len(steps), "cause": "", "explanation": note,
            "diff": "", "steps": steps, "context": context}


def repair_one(root, target, index, structure="", max_steps=MAX_STEPS):
    key = error_key(target)
    baseline = {error_key(e) for e in run_checks(root)}
    if key not in baseline:
        return {"status": "already_resolved", "attempts": 0, "cause": "", "explanation": "",
                "diff": "", "steps": [], "context": []}

    context, steps = {}, []
    lo, hi, window = source_window(root, target["file"], target["line"])
    history = [{"role": "user", "parts": [{"text": (
        f"ERROR\nfile: {target['file']}\nline: {target['line']}\nkind: {target['kind']}\n"
        f"message: {target['message']}\n\n"
        f"PROJECT STRUCTURE\n{structure[:4000]}\n\n"
        f"SOURCE AROUND THE ERROR (lines {lo}-{hi} of {target['file']})\n{window}\n\n"
        "Investigate, then propose a fix.")}]}]

    for step in range(1, max_steps + 1):
        try:
            act = ask_agent(history)
        except Exception as exc:
            return _failed(f"Model error: {exc}", steps, list(context.values()))
        if not isinstance(act, dict):
            act = {"action": None}
        history.append({"role": "model", "parts": [{"text": json.dumps(act)}]})

        action = act.get("action")
        detail = {k: v for k, v in act.items() if k not in ("original_code", "fixed_code")}
        steps.append({"action": action, "detail": json.dumps(detail, ensure_ascii=False)})

        if action == "search_code":
            hits = index.search(str(act.get("query", "")), k=4, prefer_file=target["file"])
            for h in hits:
                context[(h["file"], h["name"], h["start"])] = h
            result = "\n\n".join(
                f"### {h['file']} ({h['name']}, lines {h['start']}-{h['end']})\n{h['code']}"
                for h in hits) or "No matches."

        elif action == "read_file":
            try:
                result = read_lines(root, str(act.get("file", "")),
                                    int(act.get("start", 1)), int(act.get("end", 0)) or None)
            except Exception as exc:
                result = f"Error reading file: {exc}"

        elif action == "propose_fix":
            try:
                path, old, new = apply_fix(root, act["file"], act["original_code"], act["fixed_code"])
            except Exception as exc:
                result = f"Fix could not be applied: {exc}. Copy original_code exactly from the source."
            else:
                after = {error_key(e) for e in run_checks(root)}
                new_errors = after - baseline
                if key not in after and not new_errors:
                    diff = "".join(difflib.unified_diff(
                        old.splitlines(True), new.splitlines(True),
                        fromfile=act["file"], tofile=act["file"]))
                    return {"status": "validated", "attempts": step,
                            "cause": act.get("cause", ""), "explanation": act.get("explanation", ""),
                            "diff": diff, "steps": steps, "context": list(context.values())}
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write(old)
                if key in after:
                    problem = "the original error is still present"
                else:
                    problem = "it introduced new errors: " + "; ".join(sorted({m for _, m in new_errors}))
                result = f"Fix rejected and rolled back: {problem}. Try a different approach."

        elif action == "give_up":
            return _failed(str(act.get("reason", "Agent gave up.")), steps, list(context.values()))

        else:
            result = "Unknown action. Reply with one of the allowed JSON actions."

        history.append({"role": "user", "parts": [{"text": f"Result:\n{result}"}]})

    return _failed(f"No validated fix after {max_steps} steps.", steps, list(context.values()))