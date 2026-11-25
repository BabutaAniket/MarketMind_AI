"""CI gate: run the guardrail evaluation and fail below the configured threshold."""

from __future__ import annotations

import json
import sys

from marketmind.evaluation import run_evaluation


def main() -> int:
    report = run_evaluation()
    print(
        json.dumps(
            {k: report[k] for k in ("red_team_block_rate", "golden_allowed_rate", "minimum_pass_rate", "passed")}
        )
    )
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
