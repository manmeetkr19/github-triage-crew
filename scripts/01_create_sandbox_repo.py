"""
Phase 0: create the public sandbox repo the triage crew will operate on.

Uses the plain GitHub REST API (not the MCP server) because repo creation
is a one-time setup action, not something a triage agent should ever do.
Reads GITHUB_TOKEN from .env; never prints the token itself.
"""

import os
import sys

import requests
from dotenv import load_dotenv

load_dotenv()

REPO_NAME = "github-triage-crew-sandbox"
REPO_DESCRIPTION = "Sandbox repo for a multi-agent GitHub issue triage system (learning project)."


def main() -> None:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("GITHUB_TOKEN not set in .env", file=sys.stderr)
        raise SystemExit(1)

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    me = requests.get("https://api.github.com/user", headers=headers, timeout=15)
    me.raise_for_status()
    login = me.json()["login"]
    print(f"Authenticated as: {login}")

    resp = requests.post(
        "https://api.github.com/user/repos",
        headers=headers,
        json={
            "name": REPO_NAME,
            "description": REPO_DESCRIPTION,
            "private": False,
            "auto_init": True,
            "has_issues": True,
        },
        timeout=15,
    )

    if resp.status_code == 422 and "already exists" in resp.text:
        print(f"Repo already exists: https://github.com/{login}/{REPO_NAME}")
        print(f"\nSet in your .env: GITHUB_REPO={login}/{REPO_NAME}")
        return

    resp.raise_for_status()
    data = resp.json()
    print(f"Created: {data['html_url']}")
    print(f"\nSet in your .env: GITHUB_REPO={login}/{REPO_NAME}")


if __name__ == "__main__":
    main()
