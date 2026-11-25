# Submission checklist

Tick only what exists and has been checked.

## Repository

- [x] README with a one-command start (`python -m marketmind`)
- [x] Setup guide ([SETUP.md](SETUP.md))
- [x] No keys in the repository (`.env.example` has placeholders)
- [ ] **Rotate the OpenRouter key that appeared in the original scaffold's `.env.example`**
- [ ] Confirm nothing in `data/input` or `eval` is private or non-redistributable
- [ ] Remove `data/output` contents before submitting

## Documents

- [x] Architecture diagram and numbered walkthrough (draft: [ARCHITECTURE.md](ARCHITECTURE.md)); redraw by hand
- [x] FastMCP tool catalog ([TOOL_CATALOG.md](TOOL_CATALOG.md))
- [x] Threat model ([THREAT_MODEL.md](THREAT_MODEL.md))
- [x] Memory policy ([MEMORY_POLICY.md](MEMORY_POLICY.md))
- [ ] Evaluation report, 4-6 pages ([EVALUATION_REPORT.md](EVALUATION_REPORT.md) is a draft with TODOs)
- [ ] Experiment log with real runs ([EXPERIMENT_LOG.md](EXPERIMENT_LOG.md))
- [ ] Contribution log kept from day one ([CONTRIBUTIONS.md](CONTRIBUTIONS.md))
- [ ] Slides
- [ ] Backup demo recording ([DEMO_SCRIPT.md](DEMO_SCRIPT.md))

## Evidence the reviewers ask for

- [x] Recall@5 on 30 labelled synthetic-profile queries, before and after one change (limited to this demo profile)
- [x] Four FastMCP servers with typed schemas, read/write annotations and in-process tests for each tool
- [ ] Record the LangGraph stop/restart/resume demo (cross-process resume is automated-tested)
- [ ] Memory on vs off comparison
- [ ] Trace showing a replan
- [ ] Single agent vs team comparison
- [ ] Held-out results before and after the playbook, plus one rejected lesson
- [ ] Golden set (about 20 dev / 40+ held-out), judge agreement (kappa), Grafana dashboard
- [ ] Record a live demo of edit invalidation and resume (API tests prove edit invalidation, stale-hash refusal and mock-only approval)
- [ ] Full-workflow attack success with defences off/on; input-guardrail-only comparison is measured and fails
- [ ] Clean-machine install and one failed CI run with an explanation (the gate fails today; capture it)

## Before the viva

- [ ] Every member can redraw the architecture and explain their part
- [ ] Rehearse the eight questions in [DEMO_SCRIPT.md](DEMO_SCRIPT.md)
