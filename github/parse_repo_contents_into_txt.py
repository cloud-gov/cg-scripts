import os
import sys
import requests
import zipfile
import io
import ast
import argparse
import logging
from typing import List, Dict

# Configure logging
logging.basicConfig(level=logging.INFO)


def get_language_config() -> Dict[str, Dict]:
    """
    Returns a dictionary of language configurations including file extensions,
    excluded directories, files, and indicators for test files.
    """
    return {
        "python": {
            "extensions": [".py", ".pyw"],
            "excluded_dirs": [
                "docs",
                "examples",
                "tests",
                "test",
                "scripts",
                "utils",
                "benchmarks",
                "__pycache__",
            ],
            "excluded_files": [
                "hubconf.py",
                "setup.py",
                ".github",
                ".gitignore",
                "LICENSE",
                "README",
                "stale.py",
                "gen-card-",
                "write_model_card",
            ],
            "test_indicators": [
                "import unittest",
                "import pytest",
                "from unittest",
                "from pytest",
            ],
        },
        "go": {
            "extensions": [".go"],
            "excluded_dirs": [
                "docs",
                "examples",
                "tests",
                "test",
                "scripts",
                "utils",
                "benchmarks",
                "vendor",
            ],
            "excluded_files": [
                "go.mod",
                "go.sum",
                "Makefile",
                ".github",
                ".gitignore",
                "LICENSE",
                "README",
            ],
            "test_indicators": ["import testing", "func Test"],
        },
        "terraform": {
            "extensions": [".tf", ".tfvars", ".hcl"],
            "excluded_dirs": ["examples", "tests", "docs"],
            "excluded_files": [".gitignore", "LICENSE", "README.md"],
            "test_indicators": [],
        },
        "docker": {
            "extensions": ["Dockerfile", ".dockerignore"],
            "excluded_dirs": [],
            "excluded_files": [".gitignore", "LICENSE", "README.md"],
            "test_indicators": [],
        },
        "bosh": {
            "extensions": [".yml"],
            "excluded_dirs": ["docs", "examples", "tests", "test"],
            "excluded_files": ["LICENSE", "README.md"],
            "test_indicators": [],
        },
        "cloudfoundry": {
            "extensions": [".yml"],
            "excluded_dirs": ["docs", "examples", "tests", "test"],
            "excluded_files": ["LICENSE", "README.md"],
            "test_indicators": [],
        },
    }


def is_file_type(file_path: str, extensions: List[str]) -> bool:
    """Check if the file is of a type specified by extensions."""
    return any(file_path.endswith(ext) or file_path == ext for ext in extensions)


def is_excluded_file(
    file_path: str, excluded_dirs: List[str], excluded_files: List[str]
) -> bool:
    """Check if the file should be excluded based on directories or file names."""
    if any(
        file_path.startswith(f"{ex_dir}/") or f"/{ex_dir}/" in file_path
        for ex_dir in excluded_dirs
    ):
        return True
    return file_path.split("/")[-1] in excluded_files


def has_test_indicators(content: str, indicators: List[str]) -> bool:
    """Check if file content contains test indicators specific to a language."""
    return any(indicator in content for indicator in indicators)


def has_sufficient_content(file_content: str, min_line_count: int = 10) -> bool:
    """Check if the file content has a sufficient number of substantive lines."""
    lines = [
        line
        for line in file_content.split("\n")
        if line.strip() and not line.strip().startswith(("#", "//"))
    ]
    return len(lines) >= min_line_count


def remove_comments_and_docstrings(source: str) -> str:
    """Remove comments and docstrings from Python source code."""
    try:
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(
                node, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)
            ) and ast.get_docstring(node):
                node.body = node.body[1:]  # Remove docstring
            elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Str):
                node.value.s = ""  # Remove comments
        return ast.unparse(tree)
    except SyntaxError as e:
        logging.error(f"Error parsing Python source: {e}")
        return source  # Return original source if it cannot be parsed


def is_likely_useful_file(file_path: str, language: str) -> bool:
    """
    Determines if the file is likely to be useful by checking against configured exclusions.
    """
    config = get_language_config()[language]
    return not is_excluded_file(
        file_path, config["excluded_dirs"], config["excluded_files"]
    )


def download_and_process_files(
    repo_url: str,
    output_file: str,
    language: str,
    keep_comments: bool,
    branch_or_tag: str = "master",
):
    """Download and process files from a GitHub repository based on language settings."""
    try:
        config = get_language_config()[language]
        download_url = f"{repo_url}/archive/refs/heads/{branch_or_tag}.zip"
        response = requests.get(download_url)

        if response.status_code == 200:
            zip_file = zipfile.ZipFile(io.BytesIO(response.content))
            with open(output_file, "w", encoding="utf-8") as outfile:
                for file_path in zip_file.namelist():
                    if (
                        file_path.endswith("/")
                        or not is_file_type(file_path, config["extensions"])
                        or not is_likely_useful_file(file_path, language)
                    ):
                        continue
                    file_content = zip_file.read(file_path).decode("utf-8")

                    if has_test_indicators(
                        file_content, config["test_indicators"]
                    ) or not has_sufficient_content(file_content):
                        continue
                    if language == "python" and not keep_comments:
                        file_content = remove_comments_and_docstrings(file_content)

                    comment_tag = "//" if language == "go" else "#"
                    outfile.write(
                        f"{comment_tag} File: {file_path}\n{file_content}\n\n"
                    )
            logging.info(
                f"Combined {language.capitalize()} source code saved to {output_file}"
            )
        else:
            logging.error(
                f"Failed to download the repository. Status code: {response.status_code}"
            )
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Download and process files from a GitHub repository."
    )
    parser.add_argument("repo_url", type=str, help="The URL of the GitHub repository")
    parser.add_argument(
        "--lang",
        type=str,
        choices=get_language_config().keys(),
        default="python",
        help="The programming language of the repository",
    )
    parser.add_argument(
        "--keep-comments",
        action="store_true",
        help="Keep comments and docstrings in the source code (only applicable for Python)",
    )
    parser.add_argument(
        "--branch_or_tag",
        type=str,
        help="The branch or tag of the repository to download",
        default="master",
    )
    args = parser.parse_args()

    output_file = f"{args.repo_url.split('/')[-1]}_{args.lang}.txt"
    download_and_process_files(
        args.repo_url, output_file, args.lang, args.keep_comments, args.branch_or_tag
    )
