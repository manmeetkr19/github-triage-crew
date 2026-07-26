"""Phase 2 checkpoint: manual message/send call to the running Labeler agent."""

import asyncio

from _test_client_helper import send_and_log

if __name__ == "__main__":
    payload = {"owner": "manmeetkr19", "repo": "github-triage-crew-sandbox", "issue_number": 3}
    asyncio.run(send_and_log(8002, payload, "debug_response.txt"))
