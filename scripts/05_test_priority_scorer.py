"""Phase 2 checkpoint: manual message/send call to the running Priority Scorer agent."""

import asyncio

from _test_client_helper import send_and_log

if __name__ == "__main__":
    payload = {"owner": "manmeetkr19", "repo": "github-triage-crew-sandbox", "issue_number": 1}
    asyncio.run(send_and_log(8003, payload, "debug_response.txt"))
