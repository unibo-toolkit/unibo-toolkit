#!/usr/bin/env python3
"""Version management and changelog generation for unibo-toolkit."""

import argparse
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import List, Tuple


def run_git_command(cmd: List[str]) -> str:
    """Run git command and return output."""
    result = subprocess.run(
        ["git"] + cmd,
        capture_output=True,
        text=True,
        check=True
    )
    return result.stdout.strip()


def get_current_version() -> str:
    """Read current version from pyproject.toml."""
    pyproject_path = Path("pyproject.toml")
    content = pyproject_path.read_text()

    match = re.search(r'version\s*=\s*"([^"]+)"', content)
    if not match:
        raise ValueError("Version not found in pyproject.toml")

    return match.group(1)


def parse_version(version: str) -> Tuple[int, int, int]:
    """Parse semver version string."""
    base_version = version.split("-")[0]

    if ".dev" in base_version:
        base_version = base_version.split(".dev")[0]

    parts = base_version.split(".")

    if len(parts) != 3:
        raise ValueError(f"Invalid version format: {version}")

    return int(parts[0]), int(parts[1]), int(parts[2])


def bump_version(version: str, bump_type: str) -> str:
    """Bump version based on type."""
    major, minor, patch = parse_version(version)

    if bump_type == "major":
        return f"{major + 1}.0.0"
    elif bump_type == "minor":
        return f"{major}.{minor + 1}.0"
    elif bump_type == "patch":
        return f"{major}.{minor}.{patch + 1}"
    elif bump_type == "none":
        return f"{major}.{minor}.{patch}"
    else:
        raise ValueError(f"Unknown bump type: {bump_type}")


def detect_bump_type() -> str:
    """Detect version bump type from latest commit message."""
    try:
        commit_msg = run_git_command(["log", "-1", "--pretty=%B"])
    except subprocess.CalledProcessError:
        return "none"

    # Check for version tags in commit message
    if "#major" in commit_msg.lower():
        return "major"
    elif "#minor" in commit_msg.lower():
        return "minor"
    elif "#patch" in commit_msg.lower():
        return "patch"
    else:
        return "none"


def get_commits_since_tag(tag: str = None) -> List[str]:
    """Get commit messages since last tag."""
    try:
        if tag:
            commits = run_git_command(["log", f"{tag}..HEAD", "--pretty=%s"])
        else:
            # Try to get last tag
            try:
                last_tag = run_git_command(["describe", "--tags", "--abbrev=0"])
                commits = run_git_command(["log", f"{last_tag}..HEAD", "--pretty=%s"])
            except subprocess.CalledProcessError:
                # No tags exist yet
                commits = run_git_command(["log", "--pretty=%s"])
    except subprocess.CalledProcessError:
        return []

    return [c for c in commits.split("\n") if c.strip()]


def generate_changelog(commits: List[str]) -> str:
    """Generate changelog from commits."""
    features = []
    fixes = []

    for commit in commits:
        # Parse conventional commit format
        if commit.startswith("feat:") or commit.startswith("feat("):
            features.append(commit)
        elif commit.startswith("fix:") or commit.startswith("fix("):
            fixes.append(commit)

    changelog_parts = []

    if features:
        changelog_parts.append("### Features\n")
        for feat in features:
            # Remove "feat:" or "feat(scope):" prefix
            msg = re.sub(r"^feat(\([^)]+\))?:\s*", "", feat)
            # Remove version tags
            msg = re.sub(r"\s*#(major|minor|patch|none)\s*", "", msg, flags=re.IGNORECASE)
            changelog_parts.append(f"- {msg}")
        changelog_parts.append("")

    if fixes:
        changelog_parts.append("### Bug Fixes\n")
        for fix in fixes:
            msg = re.sub(r"^fix(\([^)]+\))?:\s*", "", fix)
            msg = re.sub(r"\s*#(major|minor|patch|none)\s*", "", msg, flags=re.IGNORECASE)
            changelog_parts.append(f"- {msg}")
        changelog_parts.append("")

    if not changelog_parts:
        return "No significant changes."

    return "\n".join(changelog_parts).strip()


def update_pyproject_version(new_version: str):
    """Update version in pyproject.toml."""
    pyproject_path = Path("pyproject.toml")
    content = pyproject_path.read_text()

    # Replace version
    new_content = re.sub(
        r'version\s*=\s*"[^"]+"',
        f'version = "{new_version}"',
        content
    )

    pyproject_path.write_text(new_content)
    print(f"✓ Updated pyproject.toml to version {new_version}")


def update_init_version(new_version: str):
    """Update version in __init__.py."""
    init_path = Path("src/unibo_toolkit/__init__.py")
    content = init_path.read_text()

    # Check if __version__ exists
    if "__version__" in content:
        # Update existing
        new_content = re.sub(
            r'__version__\s*=\s*"[^"]+"',
            f'__version__ = "{new_version}"',
            content
        )
    else:
        # Add after module docstring or at beginning
        lines = content.split("\n")
        insert_index = 0

        # Find end of module docstring
        in_docstring = False
        for i, line in enumerate(lines):
            if '"""' in line or "'''" in line:
                if in_docstring:
                    insert_index = i + 1
                    break
                else:
                    in_docstring = True

        lines.insert(insert_index, f'__version__ = "{new_version}"')
        new_content = "\n".join(lines)

    init_path.write_text(new_content)
    print(f"✓ Updated __init__.py to version {new_version}")


def create_dev_version(base_version: str) -> str:
    """Create dev version with timestamp."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"{base_version}.dev{timestamp}"


def main():
    parser = argparse.ArgumentParser(description="Manage package version and changelog")
    parser.add_argument(
        "--mode",
        choices=["release", "dev", "manual"],
        required=True,
        help="Version mode: release (prod), dev (test), or manual"
    )
    parser.add_argument(
        "--bump",
        choices=["major", "minor", "patch", "none"],
        help="Version bump type (auto-detected if not specified)"
    )
    parser.add_argument(
        "--version",
        help="Manual version override"
    )
    parser.add_argument(
        "--changelog-only",
        action="store_true",
        help="Only generate and print changelog"
    )

    args = parser.parse_args()

    # Get current version
    current_version = get_current_version()
    print(f"Current version: {current_version}")

    # Generate changelog
    commits = get_commits_since_tag()
    changelog = generate_changelog(commits)

    if args.changelog_only:
        print("\n=== CHANGELOG ===")
        print(changelog)
        return

    # Determine new version
    if args.version:
        # Manual version override
        new_version = args.version
        print(f"Using manual version: {new_version}")
    else:
        # Detect bump type
        bump_type = args.bump or detect_bump_type()
        print(f"Detected bump type: {bump_type}")

        # Bump version
        new_base_version = bump_version(current_version, bump_type)

        if args.mode == "dev":
            new_version = create_dev_version(new_base_version)
        else:
            new_version = new_base_version

    print(f"New version: {new_version}")

    update_pyproject_version(new_version)
    update_init_version(new_version)

    changelog_escaped = changelog.replace("\\", "\\\\").replace("'", "'\\''").replace("\n", "\\n")

    with open("/tmp/version_outputs.txt", "w") as f:
        f.write(f"VERSION={new_version}\n")
        f.write(f"CHANGELOG=$'{changelog_escaped}'\n")

    print("\n=== CHANGELOG ===")
    print(changelog)


if __name__ == "__main__":
    main()
