"""
This Python script automates the process of aggregating and deduplicating .gitignore file entries from all repositories 
of a specific organization on GitHub. It is designed to help developers and organizations understand the common 
patterns and files that are being ignored across their projects. The script operates by:

1. Authenticating with the GitHub API using a Personal Access Token (PAT) stored in an environment variable.
2. Fetching all repositories from the specified organization.
3. For each repository, retrieving the .gitignore file's content if it exists.
4. Decoding the content of .gitignore files from base64 encoding and parsing it into individual entries.
5. Aggregating all entries across repositories and removing duplicates to create a consolidated list.
6. Writing the deduplicated list of .gitignore entries into a CSV file named 'gitignore_entries.csv'.

Prerequisites:
- Ensure the 'requests' and 'tqdm' libraries are installed in your environment (pip install requests tqdm).
- A GitHub Personal Access Token (PAT) must be available as an environment variable named 'GITHUB_AUTH_TOKEN'.
- The target organization name must be set in the 'ORG_NAME' variable.

Features:
- Rate limiting checks to ensure the script does not exceed the GitHub API's request limitations.
- Progress feedback through a visual progress bar provided by 'tqdm'.
- Error handling for API request failures and missing environment variables.

Output:
- The script generates a file named 'gitignore_entries.csv', containing a sorted, deduplicated list of .gitignore entries.
"""

# Ensure you have installed:
# pip install requests tqdm

import requests
import csv
import time
import os
import base64
from tqdm import tqdm  # Import tqdm for progress bar functionality

# Access the GITHUB_AUTH_TOKEN from environment variables
PAT = os.environ.get("GITHUB_AUTH_TOKEN")
if not PAT:
    raise ValueError("GITHUB_AUTH_TOKEN environment variable is not set.")

ORG_NAME = "cloud-gov"

# Base URL for GitHub API
BASE_URL = "https://api.github.com"


def check_rate_limit(response):
    """Check the current rate limit and wait if necessary."""
    if "X-RateLimit-Remaining" in response.headers:
        remaining = int(response.headers["X-RateLimit-Remaining"])
        if remaining < 10:  # Ensure some requests remain; adjust as needed
            reset_time = int(response.headers["X-RateLimit-Reset"])
            sleep_time = max(reset_time - time.time(), 0) + 10  # Adding a buffer
            print(f"Approaching rate limit. Sleeping for {sleep_time} seconds.")
            time.sleep(sleep_time)


def get_repos(org_name):
    """Fetch all repositories for a specified organization."""
    repos = []
    url = f"{BASE_URL}/orgs/{org_name}/repos"
    headers = {"Authorization": f"token {PAT}"}
    while url:
        response = requests.get(url, headers=headers)
        check_rate_limit(response)  # Check rate limit before proceeding
        if response.status_code == 200:
            repos.extend(response.json())
            url = response.links.get("next", {}).get("url", None)
        else:
            print(f"Failed to fetch repositories: {response.status_code}")
            break
    return repos


def get_gitignore_contents(repo_full_name):
    """Fetch the contents of the .gitignore file of a repository, if it exists."""
    url = f"{BASE_URL}/repos/{repo_full_name}/contents/.gitignore"
    headers = {"Authorization": f"token {PAT}"}
    response = requests.get(url, headers=headers)
    check_rate_limit(response)  # Check rate limit before proceeding
    if response.status_code == 200:
        content = response.json()
        return content["content"]
    return ""


def parse_gitignore_content(content):
    """Decode the content of the .gitignore file and return a list of its entries."""
    if content:
        decoded_content = base64.b64decode(content).decode("utf-8")
        return decoded_content.splitlines()
    return []


def main():
    deduplicated_list = set()
    repos = get_repos(ORG_NAME)
    print(f"Processing .gitignore files from {len(repos)} repositories...")
    for repo in tqdm(repos, desc="Repositories Processed"):
        gitignore_content = get_gitignore_contents(repo["full_name"])
        entries = parse_gitignore_content(gitignore_content)
        deduplicated_list.update(entries)

    # Write the deduplicated list to a CSV file
    with open("gitignore_entries.csv", "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["Entry"])
        for entry in sorted(deduplicated_list):
            writer.writerow([entry])


if __name__ == "__main__":
    main()
