#!/usr/bin/env python3
"""
Script to publish Python packages for pysnmp.
Equivalent to Publish-Packages.ps1
"""

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

try:
    import tomllib  # type: ignore
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore

REPO_ROOT = Path(__file__).resolve().parent.parent
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"
TAG_PREFIX = "v"


class PublishError(Exception):
    pass


def run_command(cmd, check=True, capture_output=True, text=True):
    return subprocess.run(
        cmd,
        check=check,
        capture_output=capture_output,
        text=text,
    ).stdout.strip()


def read_publish_config(path: Path):
    if not path.is_file():
        raise PublishError(f"Unable to read repository configuration from {path}.")

    config = tomllib.loads(path.read_text(encoding="utf-8"))
    publish = config.get("tool", {}).get("publish")
    if not isinstance(publish, dict):
        raise PublishError("Missing [tool.publish] section in pyproject.toml.")

    remote = publish.get("remote")
    if not remote:
        raise PublishError("Missing required [tool.publish].remote in pyproject.toml.")
    return str(remote)


def normalize_version(version: str) -> str:
    version = version.strip()
    if version.startswith(TAG_PREFIX):
        version = version[len(TAG_PREFIX) :]
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise PublishError(
            f"Invalid release version: {version}. Expected format: 7.1.28"
        )
    return version


def local_tag_exists(tag: str) -> bool:
    try:
        run_command(["git", "rev-parse", "--verify", tag])
        return True
    except subprocess.CalledProcessError:
        return False


def remote_tag_exists(remote: str, tag: str) -> bool:
    try:
        output = run_command(
            ["git", "ls-remote", "--tags", remote, f"refs/tags/{tag}"]
        )
        return bool(output)
    except subprocess.CalledProcessError:
        return False


def read_pypirc_credentials(path: Path):
    if not path.is_file():
        raise PublishError(f"Error: ~/.pypirc file not found at '{path}'.")

    content = path.read_text(encoding="utf-8")
    if "[pypi]" not in content:
        raise PublishError(f"Error: ~/.pypirc does not contain a [pypi] section.")

    username_match = re.search(r"(?m)^\s*username\s*=\s*(.+)$", content)
    password_match = re.search(r"(?m)^\s*password\s*=\s*(.+)$", content)

    username = username_match.group(1).strip() if username_match else None
    password = password_match.group(1).strip() if password_match else None
    if not username or not password:
        raise PublishError(
            f"Error: Could not find username and/or password under the [pypi] section in '{path}'."
        )
    return username, password


def get_dist_version(dist_dir: Path) -> str:
    if not dist_dir.is_dir():
        raise PublishError(f"Dist directory '{dist_dir}' does not exist.")

    versions = set()
    for file in dist_dir.iterdir():
        if not file.is_file():
            continue
        match = re.match(r"^pysnmp-(\d+\.\d+\.\d+)(?:[-_].*)?\.(?:whl|tar\.gz)$", file.name)
        if match:
            versions.add(match.group(1))

    if not versions:
        raise PublishError(
            f"No built pysnmp artifacts found in '{dist_dir}'. "
            "Build the package first so the release version can be inferred."
        )

    if len(versions) == 1:
        return versions.pop()

    def version_key(value: str):
        return tuple(int(part) for part in value.split("."))

    sorted_versions = sorted(versions, key=version_key)
    highest = sorted_versions[-1]
    print(
        f"Multiple built versions found in '{dist_dir}': {', '.join(sorted_versions)}. "
        f"Using the highest version {highest}."
    )
    return highest


def main():
    parser = argparse.ArgumentParser(
        description="Publish Python packages for pysnmp."
    )
    parser.add_argument(
        "--version",
        help="Optional explicit release version to publish, e.g. 7.1.28. If omitted, version is inferred from dist/.",
    )
    parser.add_argument(
        "--what-if",
        "--dry-run",
        action="store_true",
        dest="what_if",
        help="Validate configuration and tag state without actually publishing.",
    )
    args = parser.parse_args()

    os.chdir(REPO_ROOT)
    remote = read_publish_config(PYPROJECT_PATH)

    if args.version:
        release_version = normalize_version(args.version)
    else:
        release_version = get_dist_version(REPO_ROOT / "dist")

    tag = f"{TAG_PREFIX}{release_version}"

    if not local_tag_exists(tag):
        raise PublishError(f"Local git tag '{tag}' does not exist.")

    if not remote_tag_exists(remote, tag):
        raise PublishError(
            f"Remote tag '{tag}' was not found on remote '{remote}'. "
            f"Push the tag with 'git push {remote} refs/tags/{tag}' before publishing."
        )

    pypirc_path = Path.home() / ".pypirc"
    pypi_username, pypi_password = read_pypirc_credentials(pypirc_path)

    if args.what_if:
        print("What-if mode enabled. Publish checks passed, but no package will be published.")
        print(f"Remote: {remote}")
        print(f"Tag: {tag}")
        print(f"Credentials found: username={pypi_username}")
        print("Would execute: uv publish --username <username> --password <password>")
        return

    print(f"Publishing to remote '{remote}' using tag '{tag}'.")
    print(f"Credentials found. Username: {pypi_username}")

    subprocess.run(
        ["uv", "publish", "--username", pypi_username, "--password", pypi_password],
        check=True,
    )


if __name__ == "__main__":
    try:
        main()
    except PublishError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    except subprocess.CalledProcessError as exc:
        print(f"Command failed: {exc}", file=sys.stderr)
        sys.exit(1)
