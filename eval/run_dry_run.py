"""
Dry-run evaluation: calls the three specialists (already-running servers)
for every issue in ground_truth.json, but skips the Coordinator's final
GitHub write - this is prediction-only, for measuring accuracy.
"""

import asyncio
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from coordinator.coordinator import SPECIALIST_URLS, _call_specialist  # noqa: E402
from eval.metrics import compute_metrics  # noqa: E402

load_dotenv()

GROUND_TRUTH_PATH = Path(__file__).parent / "ground_truth.json"


async def predict(owner: str, repo: str, issue_number: int) -> dict:
    payload = {"owner": owner, "repo": repo, "issue_number": issue_number}
    duplicate, label, priority = await asyncio.gather(
        _call_specialist("duplicate", SPECIALIST_URLS["duplicate"], payload),
        _call_specialist("label", SPECIALIST_URLS["label"], payload),
        _call_specialist("priority", SPECIALIST_URLS["priority"], payload),
    )
    return {"duplicate": duplicate, "label": label, "priority": priority}


async def main() -> None:
    owner, repo = os.environ["GITHUB_REPO"].split("/")
    ground_truth = json.loads(GROUND_TRUTH_PATH.read_text(encoding="utf-8"))

    predictions: dict[int, dict] = {}
    for entry in ground_truth:
        issue_number = entry["issue_number"]
        predictions[issue_number] = await predict(owner, repo, issue_number)
        print(f"predicted issue #{issue_number}")

    metrics = compute_metrics(predictions, ground_truth)
    report = {"metrics": metrics, "predictions": predictions}
    (Path(__file__).parent / "dry_run_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
