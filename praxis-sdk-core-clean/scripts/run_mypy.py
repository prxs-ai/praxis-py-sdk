#!/usr/bin/env python3
"""Script to run MyPy on each package separately to avoid module name conflicts."""

import subprocess
import sys
from pathlib import Path


def run_mypy_for_package(package_path: Path) -> bool:
    """Run MyPy for a single package."""
    try:
        result = subprocess.run(
            [
                "poetry",
                "run",
                "mypy",
                str(package_path),
                "--ignore-missing-imports",
                "--no-strict-optional",
                "--allow-untyped-defs",
                "--allow-incomplete-defs",
                "--exclude",
                "tests/",
            ],
            capture_output=True,
            text=True,
            cwd=Path.cwd(),
            check=False,
        )

        if result.returncode != 0:
            print(f"MyPy failed for {package_path.name}:")
            print(result.stdout)
            print(result.stderr)
            return False
        print(f"✅ MyPy passed for {package_path.name}")
        return True
    except Exception as e:
        print(f"Error running MyPy for {package_path.name}: {e}")
        return False


def main():
    """Run MyPy for all packages."""
    packages_dir = Path("packages")

    if not packages_dir.exists():
        print("packages directory not found")
        sys.exit(1)

    all_passed = True

    # Get all package directories that have src/ subdirectory
    for package_dir in packages_dir.iterdir():
        if package_dir.is_dir() and (package_dir / "src").exists():
            src_path = package_dir / "src"
            if not run_mypy_for_package(src_path):
                all_passed = False

    if not all_passed:
        print("\n❌ MyPy failed for some packages")
        sys.exit(1)
    else:
        print("\n✅ MyPy passed for all packages")


if __name__ == "__main__":
    main()
