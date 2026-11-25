# Memory and feedback policy

MarketMind keeps only human-reviewed feedback that can improve later drafts. This is an application memory layer. It is not model training.

## What is saved, and when

| Record | Saved when | File |
|---|---|---|
| Company knowledge (profile and source text) | The user clicks save | `data/output/knowledge_base.json` |
| Latest campaign plan | A plan is created | `data/output/campaign_plan.json` |
| Feedback record: original request, corrected meaning, decision, lesson, draft, source references, timestamp | The reviewer approves or rejects | `data/output/feedback_records.jsonl` |
| Approved lesson | The reviewer **approves** | `data/output/approved_lessons.jsonl` |
| Approval actions and their status | An action is prepared or decided | `data/output/actions.json` |
| Leads | An approved `write_lead` action executes | `data/output/leads.jsonl` |

## What guides future prompts

Only records with `human_approved: true`, and at most the latest five. Lessons shape style, safety and wording. They are never treated as facts: product facts must come from the saved knowledge and the retrieved passages.

Not used: rejected drafts, unreviewed model output, unconfirmed claims, keys or passwords. Rejected feedback stays in the audit file only.

## Who can read it

Anyone with access to the machine and the `data/output` folder. The app has no user accounts yet, so run it locally. Do not store real personal data until access control exists.

## Correction and deletion

- **Correct a lesson**: save a new approved lesson; to remove the old one, delete its line.
- **Delete a lesson**: remove its line from `approved_lessons.jsonl`. It stops influencing prompts at the next generation. Keep the audit line in `feedback_records.jsonl` only if the project policy requires an audit trail.
- **Delete a lead or action**: edit `leads.jsonl` or `actions.json`.
- **Delete everything**: clear the contents of `data/output`.

## Evaluation rule

Freeze the approved lesson set before the held-out run. Do not add lessons from held-out cases until the evaluation is finished.

## Short-term context

Each request is stateless: the plan is built from the saved knowledge and retrieved passages, so there is no conversation history to trim yet. A trimming or summarising step is needed if chat is added.

## Human control

No feedback record publishes content, sends a message, changes a CRM or performs an external action.
