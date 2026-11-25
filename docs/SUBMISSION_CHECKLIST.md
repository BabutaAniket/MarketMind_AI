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
- [x] Threat model ([THREAT_MODEL.md](THREAT_MODEL.md))
- [x] Memory policy ([MEMORY_POLICY.md](MEMORY_POLICY.md))
- [ ] Evaluation report, 4-6 pages ([EVALUATION_REPORT.md](EVALUATION_REPORT.md) is a draft with TODOs)
- [ ] Experiment log with real runs ([EXPERIMENT_LOG.md](EXPERIMENT_LOG.md))
- [ ] Contribution log kept from day one ([CONTRIBUTIONS.md](CONTRIBUTIONS.md))
- [ ] Slides
- [ ] Backup demo recording ([DEMO_SCRIPT.md](DEMO_SCRIPT.md))

## Evidence the reviewers ask for

- [ ] Recall@5 on 30+ labelled queries, before and after one change
- [ ] Tool list with schemas and one test per tool (FastMCP)
- [ ] Graph diagram and live stop-and-resume (LangGraph)
- [ ] Memory on vs off comparison
- [ ] Trace showing a replan
- [ ] Single agent vs team comparison
- [ ] Held-out results before and after the playbook, plus one rejected lesson
- [ ] Golden set (about 20 dev / 40+ held-out), judge agreement (kappa), Grafana dashboard
- [x] Live demonstration of an edit invalidating an earlier approval (web app, Approvals tab)
- [ ] Attack success with defences off and on, and the false-block rate
- [ ] Clean-machine install and one failed CI run with an explanation (the gate fails today; capture it)

## Before the viva

- [ ] Every member can redraw the architecture and explain their part
- [ ] Rehearse the eight questions in [DEMO_SCRIPT.md](DEMO_SCRIPT.md)
