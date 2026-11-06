# API Contract Breaking-Change Detection — micro1 Eval Hackathon

Original hackathon problem statement kept at the bottom for reference.

## What this eval tests

Frontier models are routinely asked to review API changes for backward
compatibility, yet they quietly fail on classification edges that real
integration teams argue about weekly. This eval measures whether a model can
correctly label changes between two versions of a REST API contract as
**breaking** or **non-breaking** for existing JSON API clients.

## Who it's for

- API/platform teams deciding whether a release can ship without a new major version
- Teams evaluating LLMs for changelog triage and compatibility review
- Anyone assessing whether frontier models have real backend-engineering judgment

## Why it matters

A false "non-breaking" label ships a change that breaks production clients; a
false "breaking" label blocks a safe release. Both are costly, and the correct
answer is defensible: two API design experts agree on every task in this set.

## What it shows about model limitations

The eval isolates compatibility reasoning from code generation: no coding is
required, only precise contract reasoning. It distinguishes mechanical rules
(removed field = breaking) from judgment calls (new enum value with unknown
values tolerated = non-breaking under the stated contract).

## Structure

- `eval/tasks/` — 6 tasks as JSON. Each contains: instructions, the change(s)
  to review, old and new API specs, ground truth, and the expert rationale.
  Regenerate with `python eval/tasks/make_tasks.py`.
- `eval/runner.py` — runs a model via OpenRouter, saves raw replies to
  `eval/results/raw/<model>/task_NN.json` (parsed answer + raw text).
- `eval/grader.py` — deterministic exact-match grading per change label.
  Wrong, missing, or unparseable labels all count as incorrect.
- `eval/results/` — raw outputs and score CSVs.

## Decision rules used for ground truth

1. Removing or narrowing anything a client can read → breaking.
2. Adding response fields → non-breaking (clients tolerate unknown fields, per the stated contract).
3. Adding requirements to inputs (required params/fields) → breaking.
4. Renames → breaking (old name stops working).
5. Semantic changes without a contract-visible signal are judged per the
   stated client model: unknown enum values are treated as data, not errors.
   Each task's rationale is embedded in the task JSON.

## How to run (reproducibility)

Requirements: Python 3.10+, an OpenRouter API key (free tier works), no other
dependencies (stdlib only).

```bash
# 1. Run the eval against a model (~2 min, cost < $0.05 per model at 6 tasks)
export OPENROUTER_API_KEY=sk-or-...   # keep out of git
python eval/runner.py --model anthropic/claude-sonnet-4.5

# 2. Grade
python eval/grader.py --model anthropic/claude-sonnet-4.5
# -> prints accuracy + per-task scores, writes eval/results/scores_<model>.csv
```

Expected results with the current task set (verified with a dry-run grader):
a perfect model scores 100%; a model that misses the removed-field case
(task_01) scores 83%. Approximate runtime: under 2 minutes for 6 tasks.

## Scope and honesty notes

- 6 tasks — small, per the hackathon's quality-over-quantity guidance; the
  authoring pipeline (`make_tasks.py`) makes it trivial to extend toward 10.
- One task (task_06) is a judgment call that depends on the stated client
  model; its rule is explicit in both the prompt and the task JSON so grading
  is not ambiguous.
- Models are run at temperature 0; raw replies are preserved for audit.

---

## Original problem statement (reference)

Find what AI can't do yet!

AI models can look impressive in seconds. The real test is where they quietly break: tasks that need real expertise, edge cases, judgment, and work that has to be right, not just convincing. Evals are how we measure that, and great evals are still rare.

The micro1 Eval Hackathon is a free, global, online competition for experts who can spot those gaps. Your challenge: discover something today's frontier AI models still can't do in a field you know well, and turn it into a rigorous, reproducible eval.

Evaluation criteria:

1. Where does AI fall short in your field? A real limitation that matters in practice.
2. Would two experts agree on the right answer? Clear tasks with a defensible correct result.
3. Does your grader judge it reliably? No false passes and no false fails.
4. Can someone else reproduce your results? From a clean environment, using your README.