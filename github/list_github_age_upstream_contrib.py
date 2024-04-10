import requests
import json
import os
import csv
from datetime import datetime

# Access the GITHUB_AUTH_TOKEN from environment variables
GITHUB_TOKEN = os.environ.get("GITHUB_AUTH_TOKEN")
if not GITHUB_TOKEN:
    raise ValueError("GITHUB_AUTH_TOKEN environment variable is not set.")
else:
    print("GitHub authentication token found.")

# Your GitHub org name
ORG_NAME = "cloud-gov"
print(f"Organization set to {ORG_NAME}.")


def run_query(query, max_retries=5):
    """Execute the GraphQL query with error handling for rate limits and network issues."""
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"}
    for attempt in range(max_retries):
        response = requests.post(
            "https://api.github.com/graphql", json={"query": query}, headers=headers
        )
        if response.status_code == 200:
            return response.json()
        elif attempt < max_retries - 1:
            print(f"Attempt {attempt + 1} failed, retrying...")
            continue
        else:
            raise Exception(
                f"Query failed after {max_retries} retries with status code {response.status_code}. {response.text}"
            )


def fetch_repositories():
    """Fetch all repositories including checks for README.md, SECURITY.md, and LICENSE.md with pagination."""
    all_edges = []
    end_cursor = None
    has_next_page = True

    while has_next_page:
        after_cursor = f', after: "{end_cursor}"' if end_cursor else ""
        query = f"""
        {{
          organization(login: "{ORG_NAME}") {{
            repositories(first: 10, isArchived: false{after_cursor}) {{
              pageInfo {{
                endCursor
                hasNextPage
              }}
              edges {{
                node {{
                  name
                  url
                  updatedAt
                  isFork
                  parent {{
                    nameWithOwner
                    updatedAt
                  }}
                  readme: object(expression: "HEAD:README.md") {{
                    ... on Blob {{
                      byteSize
                    }}
                  }}
                  security: object(expression: "HEAD:SECURITY.md") {{
                    ... on Blob {{
                      byteSize
                    }}
                  }}
                  license: object(expression: "HEAD:LICENSE.md") {{
                    ... on Blob {{
                      byteSize
                    }}
                  }}
                  defaultBranchRef {{
                    target {{
                      ... on Commit {{
                        history(first: 100) {{
                          edges {{
                            node {{
                              author {{
                                user {{
                                  login
                                }}
                              }}
                            }}
                          }}
                        }}
                      }}
                    }}
                  }}
                }}
              }}
            }}
          }}
        }}
        """
        page_result = run_query(query)
        edges = page_result["data"]["organization"]["repositories"]["edges"]
        all_edges.extend(edges)

        page_info = page_result["data"]["organization"]["repositories"]["pageInfo"]
        has_next_page = page_info["hasNextPage"]
        end_cursor = page_info["endCursor"]

    return all_edges


def main():
    edges = fetch_repositories()
    data_for_json = []
    for edge in edges:
        repo = edge["node"]
        repo_url = repo["url"]
        has_readme = "Yes" if repo.get("readme") else "No"
        has_security = "Yes" if repo.get("security") else "No"
        has_license = "Yes" if repo.get("license") else "No"

        # Skip repositories that have SECURITY.md
        if has_security == "Yes":
            continue

        contributors_set = set()
        if (
            repo.get("defaultBranchRef")
            and repo["defaultBranchRef"].get("target")
            and repo["defaultBranchRef"]["target"].get("history")
        ):
            contributors_set = {
                edge["node"]["author"]["user"]["login"]
                for edge in repo["defaultBranchRef"]["target"]["history"]["edges"]
                if edge["node"]["author"]["user"]
            }

        forked_info = repo.get("parent")
        forked_from = forked_info["nameWithOwner"] if forked_info else "Not a Fork"
        parent_updated_at = forked_info["updatedAt"] if forked_info else "N/A"

        repo_data = {
            "Repository": repo["name"],
            "URL": repo_url,
            "Last Updated": repo["updatedAt"],
            "Forked From": forked_from,
            "Parent Last Updated": parent_updated_at,
            "Has README.md": has_readme,
            "Has SECURITY.md": has_security,
            "Has LICENSE.md": has_license,
            "Contributors": ", ".join(list(contributors_set)),
        }
        data_for_json.append(repo_data)

    base_filename = os.path.basename(__file__).replace(".py", "")
    current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    json_filename = f"{base_filename}_{current_time}.json"
    csv_filename = f"{base_filename}_{current_time}.csv"

    with open(json_filename, "w") as f_json:
        json.dump(data_for_json, f_json, indent=2)
    print(f"Data successfully written to {json_filename}")

    with open(csv_filename, "w", newline="", encoding="utf-8") as f_csv:
        csv_columns = data_for_json[0].keys()
        writer = csv.DictWriter(f_csv, fieldnames=csv_columns)
        writer.writeheader()
        for data in data_for_json:
            writer.writerow(data)
    print(f"Data successfully written to {csv_filename}")


if __name__ == "__main__":
    main()
