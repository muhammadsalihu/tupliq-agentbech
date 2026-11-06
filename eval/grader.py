"""Grade raw model outputs against ground truth.

Usage:
  python grader.py --model anthropic/claude-sonnet-4.5 [--raw results/raw] [--tasks-dir tasks]

Writes results/scores_<model>.csv and prints a summary.
Grading is deterministic: exact match of each change label (breaking /
non-breaking). A task fails if any label is wrong, missing, or unparseable.
"""
import argparse
import csv
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))


def grade(rawdir, tasks_dir):
    tasks = {}
    for f in os.listdir(tasks_dir):
        if f.endswith(".json"):
            t = json.load(open(os.path.join(tasks_dir, f), encoding="utf-8"))
            tasks[t["id"]] = t
    rows = []
    for f in sorted(os.listdir(rawdir)):
        if not f.endswith(".json"):
            continue
        rec = json.load(open(os.path.join(rawdir, f), encoding="utf-8"))
        task = tasks[rec["task_id"]]
        gt = task["ground_truth"]
        answer = rec.get("answer")
        correct = 0
        total = len(gt)
        for cid, expected in gt.items():
            got = (answer or {}).get(cid)
            ok = (got == expected)
            correct += ok
            rows.append({"task_id": task["id"], "change_id": cid,
                         "expected": expected, "got": got,
                         "correct": ok, "task_title": task["title"]})
        rows.append({"task_id": task["id"], "change_id": "_TASK_SCORE_",
                     "expected": f"{correct}/{total}", "got": "", "correct": "",
                     "task_title": task["title"]})
    return rows


def summarize(rows):
    label_rows = [r for r in rows if r["change_id"] != "_TASK_SCORE_"]
    acc = sum(r["correct"] for r in label_rows) / len(label_rows)
    tasks_done = len({r["task_id"] for r in rows})
    return acc, tasks_done


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--raw", default=os.path.join(HERE, "results", "raw"))
    ap.add_argument("--tasks-dir", default=os.path.join(HERE, "tasks"))
    args = ap.parse_args()
    model_dir = args.model.replace("/", "__")
    rawdir = os.path.join(args.raw, model_dir)
    if not os.path.isdir(rawdir):
        raise SystemExit(f"no raw results for {args.model} in {rawdir}")

    rows = grade(rawdir, args.tasks_dir)
    outcsv = os.path.join(HERE, "results", f"scores_{model_dir}.csv")
    os.makedirs(os.path.dirname(outcsv), exist_ok=True)
    with open(outcsv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    acc, n = summarize(rows)
    print(f"{args.model}: accuracy {acc:.0%} over {len(rows) - n} labels, "
          f"{n} tasks graded")
    print("per-task:")
    for r in rows:
        if r["change_id"] == "_TASK_SCORE_":
            print(f"  {r['task_id']} ({r['task_title']}): {r['expected']}")
    print("scores written to", outcsv)


if __name__ == "__main__":
    main()
