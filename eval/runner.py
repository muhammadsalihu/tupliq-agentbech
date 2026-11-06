"""Run the eval against a model via OpenRouter.

Usage:
  python runner.py --model anthropic/claude-sonnet-4.5 [--tasks-dir tasks] [--out results/raw]

Requires OPENROUTER_API_KEY in the environment. Never hardcode keys.
"""
import argparse
import json
import os
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
API_URL = "https://openrouter.ai/api/v1/chat/completions"


def build_prompt(task):
    return (
        task["instructions"]
        + "\n\nChanges to review:\n"
        + "\n".join(f"- {c['id']}: {c['description']}" for c in task["changes"])
        + "\n\nOLD SPEC:\n"
        + json.dumps(task["old_spec"], indent=2)
        + "\n\nNEW SPEC:\n"
        + json.dumps(task["new_spec"], indent=2)
    )


def call_model(model, prompt, api_key, retries=3):
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
    }).encode()
    req = urllib.request.Request(
        API_URL, data=body,
        headers={"Authorization": f"Bearer {api_key}",
                 "Content-Type": "application/json"})
    last_err = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read())
            return data["choices"][0]["message"]["content"]
        except Exception as e:  # noqa: BLE001 - log and retry
            last_err = e
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"model call failed after {retries} attempts: {last_err}")


def parse_answer(text):
    """Extract the JSON object from a model reply, tolerating code fences."""
    t = text.strip()
    if t.startswith("```"):
        t = t.strip("`")
        if t.startswith("json"):
            t = t[4:]
    start, end = t.find("{"), t.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("no JSON object in reply")
    return json.loads(t[start:end + 1])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--tasks-dir", default=os.path.join(HERE, "tasks"))
    ap.add_argument("--out", default=os.path.join(HERE, "results", "raw"))
    args = ap.parse_args()

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        sys.exit("Set OPENROUTER_API_KEY in the environment (never commit it).")

    tasks = sorted(
        json.load(open(os.path.join(args.tasks_dir, f)))
        for f in os.listdir(args.tasks_dir) if f.endswith(".json")
    )
    outdir = os.path.join(args.out, args.model.replace("/", "__"))
    os.makedirs(outdir, exist_ok=True)

    for task in tasks:
        outpath = os.path.join(outdir, f"{task['id']}.json")
        if os.path.exists(outpath):
            print(f"skip {task['id']} (already run)")
            continue
        reply = call_model(args.model, build_prompt(task), api_key)
        record = {"task_id": task["id"], "model": args.model,
                  "raw_reply": reply, "timestamp": time.time()}
        try:
            record["answer"] = parse_answer(reply)
        except Exception as e:  # noqa: BLE001
            record["answer"] = None
            record["parse_error"] = str(e)
        with open(outpath, "w", encoding="utf-8") as f:
            json.dump(record, f, indent=2)
        print(f"done {task['id']} -> {outpath}")


if __name__ == "__main__":
    main()
