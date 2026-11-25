# Evaluation report (draft)

Target length for submission: 4-6 pages. Sections marked **TODO** need evidence that does not exist yet. Do not fill them with estimates.

## 1. Scope and users

User: a marketer at a small company who needs channel drafts and lead follow-up grounded in approved company information. Impact measure to report: editing time per approved draft and share of claims supported by a cited passage. Neither is measured yet. **TODO**

## 2. Data

| Set | File | Cases | Notes |
|---|---|---|---|
| Golden set | `eval/golden_set.jsonl` | 60 (40 dev, 20 held-out) | MOSETA-based requests. The guideline asks for about 20 dev and 40+ held-out |
| Red team | `eval/red_team_cases.jsonl` | 30 | Natural-language unsafe requests with risk categories |

The sets were generated with a local model (`eval/generate_sets.py`) and the expected outcome of every golden case is the same four-point checklist. They are a starting point: expected outcomes should be written by the product and evaluation lead before any run, and held-out cases must be kept away from the person tuning the agents. **TODO**

## 3. Measured results

Input guardrail only, from `scripts/eval_gate.py`:

| Measure | Result | Threshold |
|---|---|---|
| Red-team attacks blocked | 13 / 30 (43.3%) | 85% |
| Legitimate golden cases allowed | 56 / 60 (93.3%) | 85% |
| Gate | **Fails** | |

Reading: the attacks are mostly requests for unsupported claims, guarantees and unapproved commitments written in ordinary language. A keyword input filter cannot recognise them, and 4 legitimate requests that mention "guaranteed" in a negative sense were blocked. Output-side claim verification and a trained classifier are the needed fixes. Do not tune the patterns to this attack set and then report it as held-out.

The earlier scaffold report (12/30) and the generic placeholder sets (30/30 blocked) are not comparable: the generic set contained obvious phrases.

## 4. Not yet measured (required)

| Item | Status |
|---|---|
| Retrieval Recall@5 on 30+ labelled queries, before and after one change | **TODO** |
| Task success, trajectories and tool use on the golden set | **TODO** |
| Judge from a different model family; 20+ human labels; Cohen's kappa | **TODO** |
| E1 fixed vs single agent vs team | **TODO** |
| E2 defences off vs on, attack success and false blocks end to end | **TODO** |
| E3 playbook off vs on on held-out, with lesson cost | **TODO** |
| E4 signature ablation | **TODO** |
| Cost, median and P95 latency, errors, 3 repeats | **TODO** |

## 5. Failure analysis

Record each failed or timed-out run, its category, and what changed. **TODO**

## 6. Limits

Prototype with rule-based agents; no authentication; single company; mock actions only; local-model output unverified. Requirements before a supervised pilot: authentication and roles, real held-out evaluation, claim-to-passage verification, and a privacy review of stored leads.
