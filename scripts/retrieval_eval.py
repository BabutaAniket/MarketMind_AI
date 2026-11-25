"""Run the labeled Recall@5 comparison for the synthetic demo profile."""

from __future__ import annotations

import json

from marketmind.memory_store import write_json
from marketmind.retrieval_evaluation import run_retrieval_evaluation
from marketmind.settings import EVAL_DIR


def main() -> None:
    report = run_retrieval_evaluation()
    report_path = EVAL_DIR / "retrieval_report.json"
    write_json(report_path, report)
    print(
        json.dumps(
            {
                "queries": report["query_count"],
                "before_recall_at_5": report["before"]["recall"],
                "after_recall_at_5": report["after"]["recall"],
                "change": report["change"],
                "report": str(report_path),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
