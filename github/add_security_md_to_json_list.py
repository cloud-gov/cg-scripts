import os
import json
import logging
from datetime import datetime
import subprocess
import git  # Requires GitPython to be installed

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# Configuration
ORG_NAME = os.getenv("ORG_NAME", "cloud-gov")
REPOS_JSON_PATH = os.getenv("REPOS_JSON_PATH", "repos.json")
current_time = datetime.now().strftime("%Y%m%d%H%M%S")
BASE_PATH = os.path.expanduser(f"~/Downloads/repos_{current_time}")

SECURITY_MD_CONTENT = """
**Reporting Security Issues**

Please refrain from reporting security vulnerabilities through public GitHub issues.

Instead, kindly report them via the information provided in [cloud.gov's security.txt](https://cloud.gov/.well-known/security.txt).

When reporting, include the following details (as much as possible) to help us understand the nature and extent of the potential issue:

- Type of issue (e.g., buffer overflow, SQL injection, cross-site scripting, etc.)
- Full paths of related source file(s)
- Location of affected source code (tag/branch/commit or direct URL)
- Any special configuration required to reproduce the issue
- Step-by-step instructions to reproduce the issue
- Proof-of-concept or exploit code (if available)
- Impact of the issue, including potential exploitation by attackers

Providing this information will facilitate a quicker triage of your report.
"""


def run_command(cmd, cwd=None, ignore_error=False):
    """Run a command and return its output, handling errors."""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
            shell=False,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        logging.error(f"Command failed: {' '.join(cmd)}\nError: {e.stderr}")
        if not ignore_error:
            raise
        return None


def check_gh_auth():
    """Check if 'gh' CLI is authenticated."""
    if run_command(["gh", "auth", "status"], ignore_error=True):
        logging.info("GitHub CLI is authenticated.")
    else:
        logging.error("GitHub CLI is not authenticated. Please check the setup.")


def get_default_branch(repo_name):
    """Fetch the default branch for the repository using 'gh'."""
    try:
        branch = run_command(
            ["gh", "api", f"repos/{ORG_NAME}/{repo_name}", "--jq", ".default_branch"],
            ignore_error=False,
        )
        logging.info(f"Default branch for {repo_name} retrieved successfully: {branch}")
        return branch
    except Exception as e:
        logging.error(f"Failed to get default branch for {repo_name}: {e}")
        return None


def security_md_exists(repo_name):
    """Check if SECURITY.md exists in the repository's default branch."""
    try:
        result = run_command(
            ["gh", "api", f"repos/{ORG_NAME}/{repo_name}/contents/SECURITY.md"],
            ignore_error=True,
        )
        if result is None or "Not Found" in result:
            logging.info(f"SECURITY.md does not exist in {repo_name}.")
            return False
        logging.info(f"SECURITY.md already exists in {repo_name}.")
        return True
    except Exception as e:
        logging.error(
            f"Error occurred while checking SECURITY.md existence for {repo_name}: {e}"
        )
        return None


def clone_and_prepare_repo(repo_name):
    """Clone a repository and prepare it for adding SECURITY.md."""
    repo_path = os.path.join(BASE_PATH, repo_name)
    if not os.path.exists(repo_path):
        os.makedirs(repo_path, exist_ok=True)
    logging.info(f"Cloning {repo_name}...")
    try:
        git.Repo.clone_from(f"https://github.com/{ORG_NAME}/{repo_name}.git", repo_path)
        repo = git.Repo(repo_path)
        branch_name = (
            f"{repo_name}_add_security_md_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        )
        repo.git.checkout("-b", branch_name)
        logging.info(
            f"Repository {repo_name} cloned and new branch {branch_name} created."
        )
        return repo_path, branch_name
    except Exception as e:
        logging.error(f"Failed to clone and prepare {repo_name}: {e}")
        return None, None


def add_commit_push_security_md(repo_path, branch_name):
    """Add SECURITY.md, commit, and push it."""
    try:
        security_md_path = os.path.join(repo_path, "SECURITY.md")
        with open(security_md_path, "w") as file:
            file.write(SECURITY_MD_CONTENT)
        repo = git.Repo(repo_path)
        repo.index.add(["SECURITY.md"])
        repo.index.commit("Add SECURITY.md")
        origin = repo.remote(name="origin")
        origin.push(refspec=f"{branch_name}:{branch_name}")
        logging.info(
            f"SECURITY.md added, committed, and pushed to {branch_name} in {repo_path}."
        )
    except Exception as e:
        logging.error(
            f"Failed to add, commit, and push SECURITY.md for {repo_path}: {e}"
        )


def create_pull_request(repo_path, branch_name, default_branch):
    """Create a pull request for the branch and attempt to add reviewers."""
    original_dir = os.getcwd()  # Save the current directory
    try:
        os.chdir(repo_path)  # Change to the repo's directory
        pr_body = """## Changes proposed in this pull request:

- added Security.md

## Things to check

- Ensure everything looks correct

## Security considerations

Improves security by adding Security.md"""
        # Attempt to create the pull request and add the primary reviewer
        result = run_command(
            [
                "gh",
                "pr",
                "create",
                "--title",
                "Add SECURITY.md",
                "--body",
                pr_body,
                "--base",
                default_branch,
                "--head",
                f"{ORG_NAME}:{branch_name}",
                "--reviewer",
                "cloud-gov/platform-ops",
            ],  # Primary reviewer
            ignore_error=True,
        )

        # If the primary reviewer addition fails, try the secondary reviewer
        if "could not be requested" in result:
            logging.warning(
                f"Failed to add cloud-gov/platform-ops as a reviewer, trying cloud-gov-pages-operations."
            )
            result = run_command(
                [
                    "gh",
                    "pr",
                    "create",
                    "--title",
                    "Add SECURITY.md",
                    "--body",
                    pr_body,
                    "--base",
                    default_branch,
                    "--head",
                    f"{ORG_NAME}:{branch_name}",
                    "--reviewer",
                    "drewbo",
                ],  # Secondary reviewer
                ignore_error=True,
            )

        if "could not be requested" in result:
            logging.error(
                f"Failed to add drewbo as a reviewer as well."
            )
        else:
            logging.info(
                f"Pull request created for {branch_name}. Reviewer added successfully."
            )

    except Exception as e:
        logging.error(
            f"Failed to create pull request for the repository at {repo_path}: {e}"
        )
    finally:
        os.chdir(original_dir)  # Restore the original directory


def main():
    check_gh_auth()
    if not os.path.exists(BASE_PATH):
        os.makedirs(BASE_PATH)
    logging.info(f"Base directory set to: {BASE_PATH}")

    with open(REPOS_JSON_PATH, "r") as file:
        repos_data = json.load(file)

    for repo in repos_data:
        repo_name = repo["Repository"]
        logging.info(f"Processing {repo_name}...")
        try:
            if (
                repo.get("Forked From") == "Not a Fork"
                and repo.get("Has SECURITY.md") == "No"
            ):
                default_branch = get_default_branch(repo_name)
                if default_branch and not security_md_exists(repo_name):
                    repo_path, branch_name = clone_and_prepare_repo(repo_name)
                    if repo_path and branch_name:
                        add_commit_push_security_md(repo_path, branch_name)
                        create_pull_request(repo_path, branch_name, default_branch)
                else:
                    logging.info(
                        f"Skipping {repo_name} due to existing SECURITY.md or missing default branch."
                    )
            else:
                logging.info(
                    f"Skipping {repo_name} as it is either a fork or already has SECURITY.md."
                )
        except Exception as e:
            logging.error(f"An error occurred while processing {repo_name}: {e}")


if __name__ == "__main__":
    main()
