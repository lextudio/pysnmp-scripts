#!/usr/bin/env python3
"""
Script to upgrade project dependencies via uv.
"""

import argparse
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description="Upgrade project dependencies.")
    parser.add_argument(
        "--package",
        metavar="PKG",
        help="Upgrade a single package instead of all dependencies",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be upgraded without writing the lockfile",
    )
    args = parser.parse_args()

    if args.package:
        cmd = ["uv", "lock", "--upgrade-package", args.package]
    else:
        cmd = ["uv", "lock", "--upgrade"]

    if args.dry_run:
        # uv lock has no --dry-run; show outdated packages instead
        print("Dry run: showing outdated packages (no lockfile changes)")
        result = subprocess.run(["uv", "pip", "list", "--outdated"], check=False)
        sys.exit(result.returncode)

    print(f"Executing: {' '.join(cmd)}")
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
