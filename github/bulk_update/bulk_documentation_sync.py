#!/usr/bin/env python3
"""
bulk_documentation_sync.py — v1.1 (2025-05-23)

Description:
    bulk_documentation_sync.py is a command-line tool that automates the
    synchronization of key documentation files across all repositories in a
    GitHub organization. Specifically, it handles:

      • CONTRIBUTING.md
      • LICENSE.md
      • SECURITY.md

    The script will:
      1. Authenticate via GITHUB_TOKEN or the GitHub CLI.
      2. Download canonical versions of the above files from a single source.
      3. Enumerate every non-archived, non-fork, non-template, non-private repo.
      4. Compare SHA-256 checksums of existing files against the canonical ones.
      5. In “audit” mode, list which repos/files require updates without making
         any changes.
      6. In normal mode:
         a. Skip any repo that already has an open “Update docs:” PR.
         b. Create a new branch named
            `<branch-prefix><timestamp>-CONTRIBUTING_LICENSE_SECURITY`
         c. Commit all out-of-date or missing files in one atomic GraphQL mutation.
         d. Open a PR with a title and body listing exactly which files changed.
      7. Emit structured JSON logs for every major event (page fetch, branch
         creation, PR creation, errors), and append one record per repo to a
         daily audit file (`audit_update_docs_YYYYMMDD.jsonl`) so each repo is
         only processed once per day.

Usage:
    python bulk_documentation_sync.py --org <ORG> [options]

Required:
    --org <ORG>             GitHub organization login (e.g. cloud-gov)

Options:
    --canonical-url <URL>   Raw URL to CONTRIBUTING.md. LICENSE.md and
                            SECURITY.md are derived from the same directory.
                            (default:
                            https://raw.githubusercontent.com/cloud-gov/.github/main/CONTRIBUTING.md)
    --limit <N>             Max repositories to process. 0 means unlimited.
                            (default: 0)
    --branch-prefix <PFX>   Prefix for created branches.
                            (default: sync-docs-)
    --audit                 Audit mode: list needed updates without making changes.
    --help                  Show this help message and exit.

Examples:
    # Dry-run audit for entire org (no changes)
    python bulk_documentation_sync.py --org cloud-gov --audit

    # Synchronize all repos, creating PRs for any out-of-date docs
    python bulk_documentation_sync.py --org cloud-gov

    # Test on first 10 repos only
    python bulk_documentation_sync.py --org cloud-gov --limit 10

    # Use alternate canonical files location
    python bulk_documentation_sync.py \
      --org cloud-gov \
      --canonical-url https://raw.githubusercontent.com/my-org/my-repo/main/docs/CONTRIBUTING.md
"""

import os
import sys
import argparse
import base64
import hashlib
import json
import logging
import tempfile
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

# ───────────────────── Configuration ───────────────────── #
GITHUB_API = "https://api.github.com/graphql"
DOC_FILES = ["CONTRIBUTING.md", "LICENSE.md", "SECURITY.md"]
PR_TITLE_PREFIX = "Update docs: "

# Authentication via GITHUB_TOKEN or fallback to GH CLI
raw_token = os.getenv("GITHUB_TOKEN")
if raw_token:
    TOKEN = raw_token.strip()
else:
    try:
        TOKEN = subprocess.run(
            ["gh", "auth", "token"], text=True, capture_output=True, check=True
        ).stdout.strip()
    except Exception:
        print(
            "Error: Could not obtain GitHub token. Please set GITHUB_TOKEN or run `gh auth login`.",
            file=sys.stderr,
        )
        sys.exit(1)

HEADERS = {"Authorization": f"Bearer {TOKEN}"}

# Timestamps
RUN_TS = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
RUN_DATE = datetime.now(timezone.utc).strftime("%Y%m%d")
AUDIT_FILE = Path(f"audit_update_docs_{RUN_DATE}.jsonl")

# Defaults
DEFAULT_CANONICAL_URL = (
    "https://raw.githubusercontent.com/cloud-gov/.github/main/CONTRIBUTING.md"
)
DEFAULT_BRANCH_PREFIX = "sync-docs-"
DEFAULT_LIMIT = 0  # 0 = unlimited

# ──────────────────── Structured Logging ─────────────────── #
logger = logging.getLogger("bulk_sync")
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter(fmt="%(message)s"))
logger.setLevel(logging.INFO)
logger.addHandler(handler)


def log_json(event: Dict[str, Any]) -> None:
    """Emit a structured JSON log event."""
    logger.info(json.dumps(event, default=str))


# ───────────────────────── Helpers ───────────────────────── #
def run_graphql(query: str, variables: Dict[str, Any]) -> Dict[str, Any]:
    resp = requests.post(
        GITHUB_API, json={"query": query, "variables": variables}, headers=HEADERS
    )
    if resp.status_code != 200:
        raise RuntimeError(f"GraphQL HTTP {resp.status_code}: {resp.text}")
    data = resp.json()
    if errors := data.get("errors"):
        raise RuntimeError(f"GraphQL errors: {errors}")
    return data["data"]  # type: ignore


def audit_load() -> set:
    seen = set()
    if AUDIT_FILE.exists():
        for line in AUDIT_FILE.read_text().splitlines():
            try:
                rec = json.loads(line)
                seen.add(rec.get("repo"))
            except json.JSONDecodeError:
                continue
    return seen


def audit_write(record: Dict[str, Any]) -> None:
    with AUDIT_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, default=str) + "\n")


# ──────────────────── Canonical Fetch ──────────────────── #
def fetch_canonicals(base_url: str) -> Dict[str, Tuple[Path, str]]:
    base_dir = base_url.rsplit("/", 1)[0]
    result: Dict[str, Tuple[Path, str]] = {}
    for fname in DOC_FILES:
        url = f"{base_dir}/{fname}"
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        tmp = Path(tempfile.gettempdir()) / f"{fname}_{RUN_TS}"
        tmp.write_bytes(resp.content)
        sha = hashlib.sha256(resp.content).hexdigest()
        result[fname] = (tmp, sha)
        log_json({"event": "canonical_fetched", "file": fname, "sha": sha})
    return result


# ──────────────────── Repository Listing ──────────────────── #
def list_repos(org: str, limit: int) -> List[Dict[str, Any]]:
    """
    Fetch non-archived, non-fork, non-template, non-private repos.
    Uses cursor pagination with orderBy NAME ASC. If limit>0, stops after that many.
    """
    repos: List[Dict[str, Any]] = []
    cursor: Optional[str] = None
    remaining = limit
    unlimited = limit == 0
    per_page = 100

    query = """
query($org:String!, $first:Int!, $after:String) {
  organization(login:$org) {
    repositories(
      first:$first, after:$after,
      orderBy:{field:NAME, direction:ASC}
    ) {
      pageInfo { hasNextPage endCursor }
      nodes {
        id nameWithOwner isArchived isFork isTemplate isPrivate
        defaultBranchRef { name target { oid } }
      }
    }
  }
}
"""
    total_fetched = 0
    while True:
        take = per_page if unlimited else min(per_page, remaining)
        vars = {"org": org, "first": take, "after": cursor}
        data = run_graphql(query, vars)
        block = data["organization"]["repositories"]
        has_next = block["pageInfo"]["hasNextPage"]
        log_json(
            {
                "event": "page_fetched",
                "endCursor": block["pageInfo"]["endCursor"],
                "hasNextPage": has_next,
                "nodes_returned": len(block["nodes"]),
            }
        )
        for node in block["nodes"]:
            if any(
                node.get(flag)
                for flag in ("isArchived", "isFork", "isTemplate", "isPrivate")
            ):
                continue
            if not node.get("defaultBranchRef"):
                continue
            repos.append(node)
            total_fetched += 1
            if not unlimited:
                remaining -= 1
                if remaining <= 0:
                    log_json(
                        {
                            "event": "list_repos_complete",
                            "repos_returned": total_fetched,
                            "limit": limit,
                        }
                    )
                    return repos
        if not has_next:
            break
        cursor = block["pageInfo"]["endCursor"]

    log_json(
        {
            "event": "list_repos_complete",
            "repos_returned": total_fetched,
            "limit": limit,
        }
    )
    return repos


# ───────────────────────── File Checks ───────────────────────── #
def get_blob_sha(owner: str, name: str, branch: str, fname: str) -> Optional[str]:
    blob_q = """
query($owner:String!, $name:String!, $expr:String!) {
  repository(owner:$owner, name:$name) {
    object(expression:$expr) { ... on Blob { text } }
  }
}
"""
    expr = f"{branch}:{fname}"
    try:
        data = run_graphql(blob_q, {"owner": owner, "name": name, "expr": expr})
        text = data["repository"]["object"]["text"]
        return hashlib.sha256(text.encode()).hexdigest()
    except Exception:
        return None


def get_existing_pr(owner: str, name: str) -> Optional[str]:
    pr_q = """
query($owner:String!, $name:String!) {
  repository(owner:$owner, name:$name) {
    pullRequests(states:OPEN, first:10) {
      nodes { title url }
    }
  }
}
"""
    data = run_graphql(pr_q, {"owner": owner, "name": name})
    for pr in data["repository"]["pullRequests"]["nodes"]:
        if pr["title"].startswith(PR_TITLE_PREFIX):
            return pr["url"]
    return None


# ───────────────────────── Git Operations ───────────────────────── #
def create_ref(repo_id: str, branch: str, base_oid: str) -> None:
    m = """
mutation($i:CreateRefInput!) {
  createRef(input:$i) { ref { name } }
}
"""
    inp = {"repositoryId": repo_id, "name": f"refs/heads/{branch}", "oid": base_oid}
    run_graphql(m, {"i": inp})


def commit_on_branch(
    owner: str, name: str, branch: str, files: List[Path], base_oid: str
) -> str:
    additions = []
    for f in files:
        content = base64.b64encode(f.read_bytes()).decode()
        additions.append({"path": f.name, "contents": content})
    m = """
mutation($i:CreateCommitOnBranchInput!) {
  createCommitOnBranch(input:$i) { commit { oid } }
}
"""
    inp = {
        "branch": {"repositoryNameWithOwner": f"{owner}/{name}", "branchName": branch},
        "message": {"headline": "Sync documentation files"},
        "expectedHeadOid": base_oid,
        "fileChanges": {"additions": additions},
    }
    data = run_graphql(m, {"i": inp})
    return data["createCommitOnBranch"]["commit"]["oid"]


def create_pull_request(repo_id: str, branch: str, base: str, files: List[str]) -> str:
    title = PR_TITLE_PREFIX + ", ".join(files)
    body = (
        "This PR synchronizes the following documentation files:\n\n"
        + "\n".join(f"- `{f}`" for f in files)
        + "\n\n*Automated by bulk_documentation_sync.py*"
    )
    m = """
mutation($i:CreatePullRequestInput!) {
  createPullRequest(input:$i) { pullRequest { url } }
}
"""
    inp = {
        "repositoryId": repo_id,
        "headRefName": branch,
        "baseRefName": base,
        "title": title,
        "body": body,
    }
    data = run_graphql(m, {"i": inp})
    return data["createPullRequest"]["pullRequest"]["url"]


# ───────────────────────── Worker ───────────────────────── #
def process_repo(
    node: Dict[str, Any],
    canonicals: Dict[str, Tuple[Path, str]],
    branch_prefix: str,
    audit_mode: bool,
) -> None:
    full = node["nameWithOwner"]
    owner, name = full.split("/")
    repo_id = node["id"]
    ref = node["defaultBranchRef"]
    base = ref["name"]
    oid = ref["target"]["oid"]
    branch = f"{branch_prefix}{RUN_TS}-" + "_".join(f[:-3] for f in DOC_FILES)
    rec: Dict[str, Any] = {"repo": full, "branch": branch}

    try:
        to_update: List[Path] = []
        missing: List[str] = []
        for fname in DOC_FILES:
            existing_sha = get_blob_sha(owner, name, base, fname)
            _, canon_sha = canonicals[fname]
            if existing_sha != canon_sha:
                to_update.append(canonicals[fname][0])
                missing.append(fname)

        if not to_update:
            rec["status"] = "up-to-date"
            log_json(rec)
        else:
            rec["files_needed"] = missing
            if audit_mode:
                rec["status"] = "will_update"
                log_json(rec)
            else:
                if get_existing_pr(owner, name):
                    rec["status"] = "pr_exists"
                    log_json(rec)
                else:
                    create_ref(repo_id, branch, oid)
                    new_oid = commit_on_branch(owner, name, branch, to_update, oid)
                    pr_url = create_pull_request(repo_id, branch, base, missing)
                    rec.update(
                        {
                            "status": "pr_created",
                            "commit": new_oid,
                            "pr": pr_url,
                            "files_changed": missing,
                        }
                    )
                    log_json(rec)
    except Exception as e:
        rec.update({"status": "error", "error": str(e)})
        log_json(rec)
    finally:
        rec["timestamp"] = datetime.now(timezone.utc).isoformat()
        audit_write(rec)


# ────────────────────────── Main ───────────────────────── #
def main() -> None:
    seen = audit_load()

    parser = argparse.ArgumentParser(
        description="Bulk-sync CONTRIBUTING.md, LICENSE.md, SECURITY.md"
    )
    parser.add_argument("--org", required=True, help="GitHub organization login")
    parser.add_argument(
        "--canonical-url",
        default=DEFAULT_CANONICAL_URL,
        help="Raw URL to canonical CONTRIBUTING.md; LICENSE/SECURITY derived",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        help="Max repos to process (0=unlimited)",
    )
    parser.add_argument(
        "--branch-prefix",
        default=DEFAULT_BRANCH_PREFIX,
        help="Prefix for created branches",
    )
    parser.add_argument(
        "--audit",
        action="store_true",
        help="Audit mode: list needed updates without making changes",
    )
    args = parser.parse_args()

    canonicals = fetch_canonicals(args.canonical_url)
    log_json({"event": "canonicals_ready", "files": list(canonicals.keys())})

    repos = list_repos(args.org, args.limit)
    to_process = [r for r in repos if r["nameWithOwner"] not in seen]
    log_json(
        {
            "event": "start_processing",
            "count": len(to_process),
            "audit_mode": args.audit,
        }
    )

    for node in to_process:
        process_repo(node, canonicals, args.branch_prefix, args.audit)


if __name__ == "__main__":
    main()
