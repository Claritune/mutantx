#!/usr/bin/env python3
"""MutantX manual mutation capture.

Captures uncommitted file changes as mutation patches. Edit a file to
introduce the bug you want to test, then run this script to register
it as a mutant.

Workflow:
    1. Edit a source file (don't commit)
    2. python mx-capture.py
    3. The change is saved as a patch, added to the manifest, and reverted

Usage:
    python mx-capture.py [--mutants-dir .mutants] [--description "..."] [--keep]
"""

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def run_cmd(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=30, **kwargs)


def get_changed_files() -> list[str]:
    """Get list of files with uncommitted changes (tracked files only)."""
    result = run_cmd(["git", "diff", "--name-only"])
    if result.returncode != 0:
        print(f"ERROR: git diff failed: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    return [f for f in result.stdout.strip().splitlines() if f]


def get_diff_for_file(filepath: str) -> str:
    """Get unified diff for a single file."""
    result = run_cmd(["git", "diff", filepath])
    if result.returncode != 0:
        print(f"ERROR: git diff failed for {filepath}: {result.stderr}", file=sys.stderr)
        return ""
    return result.stdout


def find_changed_line(diff: str) -> int:
    """Extract the first changed line number from a unified diff."""
    for line in diff.splitlines():
        if line.startswith("@@"):
            # Parse @@ -old,count +new,count @@
            try:
                plus_part = line.split("+")[1].split("@@")[0].strip()
                line_num = int(plus_part.split(",")[0])
                return line_num
            except (IndexError, ValueError):
                pass
    return 0


def next_mutant_id(mutants: list[dict]) -> str:
    """Find the next available mutant ID."""
    existing = set()
    for m in mutants:
        try:
            existing.add(int(m.get("id", "0")))
        except ValueError:
            pass
    next_num = max(existing, default=0) + 1
    return f"{next_num:03d}"


def load_or_create_manifest(mutants_dir: Path) -> dict:
    manifest_path = mutants_dir / "manifest.json"
    if manifest_path.exists():
        with open(manifest_path) as f:
            return json.load(f)
    return {
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "config": {},
        "file_hashes": {},
        "mutants": [],
        "summary": None,
    }


def save_manifest(manifest: dict, mutants_dir: Path):
    manifest_path = mutants_dir / "manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)


def revert_file(filepath: str) -> bool:
    result = run_cmd(["git", "checkout", "--", filepath])
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(description="MutantX manual mutation capture")
    parser.add_argument(
        "--mutants-dir", type=Path, default=Path(".mutants"),
        help="Path to the mutants directory (default: .mutants)",
    )
    parser.add_argument(
        "--description", "-d", type=str, default=None,
        help="Description of the mutation (prompted interactively if omitted)",
    )
    parser.add_argument(
        "--keep", action="store_true",
        help="Don't revert the file change after capturing",
    )
    args = parser.parse_args()

    # Find uncommitted changes
    changed_files = get_changed_files()
    if not changed_files:
        print("No uncommitted changes found. Edit a file first, then run this script.")
        sys.exit(0)

    print(f"Found changes in {len(changed_files)} file(s):")
    for f in changed_files:
        print(f"  {f}")
    print()

    # Set up directories
    patches_dir = args.mutants_dir / "patches"
    patches_dir.mkdir(parents=True, exist_ok=True)

    manifest = load_or_create_manifest(args.mutants_dir)
    mutants = manifest.get("mutants", [])
    captured = 0

    for filepath in changed_files:
        diff = get_diff_for_file(filepath)
        if not diff:
            print(f"  Skipping {filepath}: no diff content")
            continue

        mutant_id = next_mutant_id(mutants)
        patch_file = f"patches/{mutant_id}.patch"
        patch_path = args.mutants_dir / patch_file
        line = find_changed_line(diff)

        # Get description
        if args.description and len(changed_files) == 1:
            description = args.description
        else:
            print(f"\nMutation in {filepath} (line {line}):")
            # Show a compact diff preview
            diff_lines = diff.splitlines()
            preview = [l for l in diff_lines if l.startswith(("+", "-")) and not l.startswith(("+++", "---"))]
            for l in preview[:10]:
                print(f"    {l}")
            if len(preview) > 10:
                print(f"    ... ({len(preview) - 10} more lines)")
            description = input("  Description (or Enter to skip): ").strip()
            if not description:
                description = f"Manual mutation in {filepath}"

        # Save patch
        patch_path.write_text(diff)

        # Verify patch applies after revert
        # (we need the original file to test against)
        original_hash = None
        if not args.keep:
            # Get hash of original (pre-change) file
            result = run_cmd(["git", "show", f"HEAD:{filepath}"])
            if result.returncode == 0:
                original_hash = hashlib.sha256(result.stdout.encode()).hexdigest()

            revert_file(filepath)

            # Verify the patch applies cleanly
            check = run_cmd(["git", "apply", "--check", str(patch_path)])
            if check.returncode != 0:
                print(f"  WARNING: Captured patch doesn't apply cleanly after revert", file=sys.stderr)
        else:
            # File is still modified, hash the original via git
            result = run_cmd(["git", "show", f"HEAD:{filepath}"])
            if result.returncode == 0:
                original_hash = hashlib.sha256(result.stdout.encode()).hexdigest()

        # Update file_hashes with the original file hash
        if original_hash:
            manifest.setdefault("file_hashes", {})[filepath] = original_hash

        # Add mutant to manifest
        mutant_entry = {
            "id": mutant_id,
            "file": filepath,
            "line": line,
            "category": "manual",
            "description": description,
            "patch_file": patch_file,
            "status": "pending",
        }
        mutants.append(mutant_entry)
        captured += 1

        print(f"  Captured mutant {mutant_id}: {description}")

    manifest["mutants"] = mutants
    save_manifest(manifest, args.mutants_dir)

    print(f"\n{captured} mutation(s) captured.")
    if not args.keep:
        print("File(s) reverted to original state.")
    else:
        print("File(s) left modified (--keep). Revert before testing.")
    print(f"Run mx-test.py to test, or /mutate for the full workflow.")


if __name__ == "__main__":
    main()
