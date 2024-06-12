import os
import sys
import requests
import zipfile
import io
import argparse
import logging
from typing import List

# Setting up basic configuration for logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def get_excluded_files() -> List[str]:
    """
    Returns a list of filenames to be excluded from processing.
    These are typically non-code files that do not contain useful information
    for analysis or model training.
    """
    return ["README.md", "README", "LICENSE", "LICENSE.txt"]


def is_excluded_file(file_path: str, excluded_files: List[str]) -> bool:
    """
    Determines whether a file should be excluded based on its filename ending.
    Args:
        file_path: The path of the file within the repository.
        excluded_files: A list of filename endings to exclude.
    Returns:
        True if the file is to be excluded, False otherwise.
    """
    return any(file_path.endswith(ex_file) for ex_file in excluded_files)


def has_sufficient_content(file_content: str, min_line_count: int = 10) -> bool:
    """
    Checks if the file content has at least a minimum number of non-empty lines.
    Args:
        file_content: The content of the file as a string.
        min_line_count: The minimum number of non-empty lines required for the file to be included.
    Returns:
        True if the content meets the minimum line count, False otherwise.
    """
    lines = [line for line in file_content.split("\n") if line.strip()]
    return len(lines) >= min_line_count


def download_and_process_files(
    repo_url: str, output_file: str, branch_or_tag: str = "master"
):
    """
    Downloads and processes files from a GitHub repository archive.
    Args:
        repo_url: The URL of the GitHub repository.
        output_file: The path to the output text file where combined contents will be stored.
        branch_or_tag: The branch or tag to download from the repository.
    """
    excluded_files = get_excluded_files()
    download_url = f"{repo_url}/archive/refs/heads/{branch_or_tag}.zip"

    try:
        response = requests.get(download_url)
        response.raise_for_status()  # Raises HTTPError for bad requests (4XX or 5XX)

        with zipfile.ZipFile(io.BytesIO(response.content)) as zip_file:
            with open(output_file, "w", encoding="utf-8") as outfile:
                for file_path in zip_file.namelist():
                    if file_path.endswith("/") or is_excluded_file(
                        file_path, excluded_files
                    ):
                        continue
                    with zip_file.open(file_path) as file:
                        file_content = file.read().decode("utf-8")
                        if has_sufficient_content(file_content):
                            outfile.write(f"# File: {file_path}\n{file_content}\n\n")

        logging.info(f"Combined source code saved to {output_file}")
    except requests.exceptions.HTTPError as e:
        logging.error(f"HTTP Error occurred: {e}")
    except requests.exceptions.RequestException as e:
        logging.error(f"Error downloading the file: {e}")
    except zipfile.BadZipFile:
        logging.error(
            "Error processing zip file: The downloaded file was not a valid zip file."
        )
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Download and process files from a GitHub repository."
    )
    parser.add_argument("repo_url", type=str, help="The URL of the GitHub repository")
    parser.add_argument(
        "--branch_or_tag",
        type=str,
        help="The branch or tag of the repository to download",
        default="master",
    )
    args = parser.parse_args()

    output_file = f"{args.repo_url.split('/')[-1]}_combined.txt"
    download_and_process_files(args.repo_url, output_file, args.branch_or_tag)
