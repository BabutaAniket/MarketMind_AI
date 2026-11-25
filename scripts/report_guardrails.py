"""Run guardrail-only off/on evaluation and save the complete measured report."""

from __future__ import annotations

import json

from marketmind.evaluation import run_evaluation
from marketmind.memory_store import write_json
from marketmind.settings import EVAL_DIR


def main() -> None:
    report = run_evaluation()
    path = EVAL_DIR / "guardrail_report.json"
    write_json(path, report)
    print(
        json.dumps(
            {
                "scope": report["scope"],
                "defences_off_attack_success": report["defences_off"]["red_team"]["attack_success_rate"],
                "defences_on_attack_success": report["defences_on"]["red_team"]["attack_success_rate"],
                "defences_on_false_block_rate": report["defences_on"]["clean_requests"]["false_block_rate"],
                "passed": report["passed"],
                "report": str(path),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
