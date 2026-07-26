"""
Phase 3 checkpoint: run the full pipeline (fan-out to all 3 specialists,
reconcile, apply labels + post a comment) against a real sandbox issue.
Requires all three agent servers (ports 8001-8003) already running.
"""

import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from coordinator.coordinator import triage_issue  # noqa: E402

if __name__ == "__main__":
    result = asyncio.run(triage_issue("manmeetkr19", "github-triage-crew-sandbox", 3))
    with open("debug_response.txt", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print("done, see debug_response.txt")
