#!/usr/bin/env python3
"""
Script to run tests for the project.
Equivalent to Run-Tests.ps1
"""

import argparse
import os
import subprocess
import sys
import tomllib
from pathlib import Path

# Repository root (parent directory of this script)
REPO_ROOT = Path(__file__).resolve().parent.parent


def get_package_name():
    """Auto-detect package name from pyproject.toml."""
    pyproject_path = REPO_ROOT / "pyproject.toml"
    if pyproject_path.exists():
        try:
            with open(pyproject_path, "rb") as f:
                data = tomllib.load(f)
            return data.get("project", {}).get("name", "")
        except Exception:
            pass
    # Fallback: use directory name
    return REPO_ROOT.name


def main():
    """Main function to run tests."""
    # Change to repository root directory
    os.chdir(REPO_ROOT)
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Run tests for this project.")
    parser.add_argument(
        "--coverage", action="store_true", help="Run with coverage report"
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Run with verbose output"
    )
    parser.add_argument(
        "--test-file", default="", help="Specific test file to run"
    )
    parser.add_argument(
        "--test-path", default="tests", help="Path to test directory"
    )
    parser.add_argument(
        "--args", default="", help="Additional pytest arguments"
    )
    parser.add_argument(
        "--retry", type=int, default=0, help="Retry failed tests N times"
    )
    parser.add_argument(
        "--retry-delay",
        type=int,
        default=1,
        help="Delay between retries (seconds)",
    )

    args = parser.parse_args()

    # Check if virtual environment is active
    if not (REPO_ROOT / ".venv").exists():
        print("No virtual environment found. Creating one...", file=sys.stderr)
        subprocess.run(["uv", "venv"], check=True)

        print("Installing dependencies...", file=sys.stderr)
        subprocess.run(["uv", "pip", "install", "-e", ".[dev]"], check=True)

    print("Running tests for this project...", file=sys.stderr)

    # Build the command
    command = ["uv", "run", "python", "-m", "pytest"]

    if args.verbose:
        command.append("-v")

    # Add retry for flaky tests if requested
    if args.retry > 0:
        command.extend(["--reruns", str(args.retry)])
        if args.retry_delay > 0:
            command.extend(["--reruns-delay", str(args.retry_delay)])

    if args.coverage:
        package_name = get_package_name()
        if package_name:
            command.extend([
                f"--cov={package_name}",
                "--cov-report=term"
            ])

    if args.test_file:
        command.append(args.test_file)
    else:
        command.append(args.test_path)

    if args.args:
        command.extend(args.args.split())

    # Display the command being run
    print(f"Executing: {' '.join(command)}", file=sys.stderr)

    # Run the command
    subprocess.run(command, check=True)


if __name__ == "__main__":
    main()
