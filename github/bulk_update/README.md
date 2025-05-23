# bulk_documentation_sync.py

**Version:** v1 (2025-05-23)  
**License:** MIT  
**Maintainer:** Cloud.gov Office of Cybersecurity

---

## Overview

`bulk_documentation_sync.py` is a command-line tool that automates the process of synchronizing three key documentation files across all repositories in a GitHub organization:

- **CONTRIBUTING.md**
- **LICENSE.md**
- **SECURITY.md**

It uses GitHub’s GraphQL API to:

1. **Fetch** the canonical versions of those files (from a single “source” repository).
2. **Enumerate** every non-archived, non-fork, non-template, non-private repository.
3. **Compare** the checksum of each file on each repo’s default branch against the canonicals.
4. **Create** a new branch (named with a timestamp and file list) when any file is missing or out of date.
5. **Commit** all changed files in one atomic GraphQL mutation.
6. **Open** a pull request with a clear title and body listing exactly which files were synchronized.
7. **Log** every step as structured JSON to stdout and to a daily audit file, preventing duplicate PRs.

An **audit mode** (`--audit`) will perform steps 1–3 and then simply list which repositories and files **would** be updated, without making any changes.

---

## Features

- **Unlimited pagination**: reliably processes more than 100 repositories by using cursor-based GraphQL pagination ordered by repository name.
- **Selective filtering**: skips archived, forked, template, and private repositories automatically.
- **Audit log**: appends one JSON record per repository to `audit_update_docs_YYYYMMDD.jsonl`, ensuring each repo is only processed once per day.
- **Audit mode**: with `--audit`, outputs “will_update” status and file list without creating branches or PRs.
- **Existing-PR detection**: skips any repository that already has an open PR whose title begins with “Update docs:” (normal mode only).
- **Structured logging**: emits JSON events (`canonical_fetched`, `page_fetched`, `start_processing`, etc.) to stdout for easy ingestion into centralized logging systems.
- **Dynamic branch names & PRs**: branch names include the timestamp and file identifiers; PR titles and bodies list exactly which files were changed.
- **GH CLI integration**: uses `gh auth token` for authentication if `GITHUB_TOKEN` is not set.

---

## Prerequisites

1. **Python 3.8+**
2. **`requests`** library
   ```bash
   pip install requests
   ```

````

3. **GitHub CLI (`gh`)** (for authentication fallback)

   ```bash
   gh auth login
   ```
4. **Network access** to `api.github.com`

---

## Installation

1. **Clone this repository** (or copy `bulk_documentation_sync.py` to your scripts folder).
2. Ensure it’s executable:

   ```bash
   chmod +x bulk_documentation_sync.py
   ```
3. (Optional) Place it on your PATH or symlink it to `/usr/local/bin`.

---

## Usage

```bash
./bulk_documentation_sync.py --org <ORG> [options]
```

### Required

* `--org <ORG>`
  Your GitHub organization login (e.g. `cloud-gov`).

### Optional

* `--canonical-url <URL>`
  Raw URL to the canonical `CONTRIBUTING.md`.
  **Default:**
  `https://raw.githubusercontent.com/cloud-gov/.github/main/CONTRIBUTING.md`
  The tool will automatically derive `LICENSE.md` and `SECURITY.md` from the same directory.

* `--limit <N>`
  Maximum number of repositories to process.
  **Default:** `0` → unlimited.

* `--branch-prefix <PREFIX>`
  Prefix for the branch name created on each repo.
  **Default:** `sync-docs-`

* `--audit`
  **Audit mode**: report which repos/files need updating without making changes.

---

## Examples

1. **Dry-run audit** for the entire organization:

   ```bash
   ./bulk_documentation_sync.py --org cloud-gov --audit
   ```

2. **Sync all repos**, creating PRs for any out-of-date or missing docs:

   ```bash
   ./bulk_documentation_sync.py --org cloud-gov
   ```

3. **Sync only the first 10 repos** (for testing):

   ```bash
   ./bulk_documentation_sync.py --org cloud-gov --limit 10
   ```

4. **Use a custom source directory** for canonicals:

   ```bash
   ./bulk_documentation_sync.py \
     --org cloud-gov \
     --canonical-url https://raw.githubusercontent.com/my-org/my-repo/main/docs/CONTRIBUTING.md
   ```

---

## How It Works

1. **Authentication**

   * If `GITHUB_TOKEN` is set in the environment, it’s used directly.
   * Otherwise, the script runs `gh auth token` and uses the returned token.

2. **Fetch Canonicals**

   * Downloads `CONTRIBUTING.md`, `LICENSE.md`, and `SECURITY.md` from the directory of the provided `--canonical-url`.
   * Saves them to a temp folder and computes their SHA-256 checksums.

3. **List Repositories**

   * Executes a GraphQL query against `organization(login:$org).repositories`, ordered by name ascending.
   * Paginates with `first: N, after: $cursor`, where `N` is either 100 or the remaining count.
   * Filters out any repo that is archived, a fork, a template, or private, or that lacks a default branch.

4. **Audit Determination**

   * Loads (or creates) `audit_update_docs_<YYYYMMDD>.jsonl`.
   * Skips any repo already seen in today’s audit file.

5. **Per-Repo Processing**

   * For each candidate repo:

     * **Compute** the existing SHA of each doc file via GraphQL blob queries.
     * **Compare** to the canonical SHA.
     * If **all match**, logs `{"repo": "...", "status":"up-to-date"}` and moves on.
     * Otherwise, in **audit mode** logs `{"repo":"...","status":"will_update","files_needed":[…]}`.
     * In **normal mode**:

       1. Checks for any open PR titled `Update docs: …`. If found, logs `{"status":"pr_exists"}`.
       2. Creates a new branch `PREFIX<timestamp>-CONTRIBUTING_LICENSE_SECURITY`.
       3. Commits all changed files in a single GraphQL `createCommitOnBranch` mutation.
       4. Opens a PR via `createPullRequest`, with a title listing the filenames.
       5. Logs `{"status":"pr_created","pr":"<url>","commit":"<oid>","files_changed":[…]}`.

6. **Logging & Auditing**

   * Every step emits a JSON event to stdout (`log_json`), suitable for piping to `jq` or ingesting into ELK/Prometheus.
   * Every per-repo outcome is appended to today’s audit file for idempotency.

---

## Audit File Format

* **Location:** same directory as the script, named
  `audit_update_docs_<YYYYMMDD>.jsonl`

* **Content:** one JSON object per line, for example:

  ```jsonl
  {"repo":"cloud-gov/example-repo","branch":"sync-docs-20250523120000-CONTRIBUTING_LICENSE","status":"pr_created","pr":"https://github.com/cloud-gov/example-repo/pull/123","commit":"abc123…","files_changed":["CONTRIBUTING.md","LICENSE.md"],"timestamp":"2025-05-23T12:00:05.123456+00:00"}
  ```

---

## Troubleshooting

* **Only 100 repos fetched?**
  Ensure you’re running without `--limit` or with `--limit 0`. Check the `page_fetched` logs to verify pagination.

* **Authentication errors**

  * Set `GITHUB_TOKEN` to a valid Personal Access Token with `repo` scope.
  * Or run `gh auth login` before invoking the script.

* **GraphQL rate limits**
  Monitor the `X-RateLimit-Remaining` header via GitHub’s API or wrap calls in backoff logic if needed.

* **Script crashes on Python errors**

  * Verify dependencies:

    ```bash
    pip install requests
    ```
  * Run `python3 --version` to confirm you’re using Python 3.8+.

---

## Contributing & Feedback

Feel free to open issues or pull requests on this script’s repository. For major changes, please follow the same contribution workflow:

1. Fork the repo.
2. Create a feature branch.
3. Run existing tests (if any) and verify linting.
4. Submit a pull request for review.

---

*Automated by bulk\_documentation\_sync.py — keeping your organization’s docs in perfect sync!*
````
