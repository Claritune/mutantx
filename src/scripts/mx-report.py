#!/usr/bin/env python3
"""MutantX deterministic report generator.

Reads .mutants/manifest.json, calculates the mutation score, and generates
a report with summary statistics, survived mutant details, and killed mutant
table. Zero AI tokens.

For AI-powered analysis of survived mutants ("why this matters", "suggested
test"), run /mx-report in Claude Code after this script.

Usage:
    python mx-report.py [--mutants-dir .mutants]
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def git_short_hash() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=10,
        )
        return result.stdout.strip() if result.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


def project_name() -> str:
    return Path.cwd().name


def read_patch(mutants_dir: Path, patch_file: str) -> str:
    path = mutants_dir / patch_file
    if path.exists():
        return path.read_text()
    return "(patch file not found)"


# Every status that counts as the tests catching the mutant.
KILLED_STATUSES = ("killed", "killed-crash", "killed-build", "timeout")


def score_interpretation(score: float) -> str:
    if score > 0.8:
        return "Strong test suite — tests catch most injected bugs."
    elif score >= 0.6:
        return "Moderate — there are meaningful gaps in test coverage."
    else:
        return "Weak — many realistic bugs would go undetected."


def generate_report(manifest: dict, mutants_dir: Path) -> str:
    mutants = manifest.get("mutants", [])

    killed = [m for m in mutants if m["status"] == "killed"]
    crashed = [m for m in mutants if m["status"] == "killed-crash"]
    build_failed = [m for m in mutants if m["status"] == "killed-build"]
    survived = [m for m in mutants if m["status"] == "survived"]
    timeout = [m for m in mutants if m["status"] == "timeout"]
    skipped = [m for m in mutants if m["status"] == "skipped"]
    all_killed = [m for m in mutants if m["status"] in KILLED_STATUSES]
    total = len(mutants)

    testable = len(all_killed) + len(survived)
    score = len(all_killed) / testable if testable > 0 else 0.0

    killed_pct = f"{len(killed)/total*100:.0f}" if total else "0"
    survived_pct = f"{len(survived)/total*100:.0f}" if total else "0"

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    commit = git_short_hash()

    lines = []
    lines.append("# MutantX — Mutation Testing Report")
    lines.append("")
    lines.append(f"**Project:** {project_name()}")
    lines.append(f"**Date:** {now}")
    lines.append(f"**Commit:** {commit}")
    lines.append("")

    # Summary table
    lines.append("## Summary")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| Total mutants | {total} |")
    lines.append(f"| Killed | {len(killed)} ({killed_pct}%) |")
    lines.append(f"| Killed by crash | {len(crashed)} |")
    lines.append(f"| Killed by build failure | {len(build_failed)} |")
    lines.append(f"| Timeout | {len(timeout)} |")
    lines.append(f"| Survived | {len(survived)} ({survived_pct}%) |")
    lines.append(f"| Skipped | {len(skipped)} |")
    lines.append(f"| **Mutation Score** | **{score:.0%}** |")
    lines.append("")

    # Score interpretation
    lines.append("## Score Interpretation")
    lines.append("")
    lines.append(f"**{score:.0%}** — {score_interpretation(score)}")
    lines.append("")
    lines.append("- **> 80%**: Strong test suite — tests catch most injected bugs.")
    lines.append("- **60–80%**: Moderate — there are meaningful gaps in test coverage.")
    lines.append("- **< 60%**: Weak — many realistic bugs would go undetected.")
    lines.append("")

    # Survived mutants
    if survived:
        lines.append("## Survived Mutants ⚠️")
        lines.append("")
        lines.append("These mutants were NOT caught by your tests. Each one represents a potential gap in your test coverage.")
        lines.append("")

        for m in survived:
            mid = m["id"]
            cat = m.get("category", "unknown").replace("_", " ").title()
            f = m.get("file", "unknown")
            line = m.get("line", "?")
            desc = m.get("description", "")
            patch = read_patch(mutants_dir, m.get("patch_file", ""))

            lines.append(f"### Mutant {mid} — {cat} in `{f}`")
            lines.append("")
            lines.append(f"**Line {line}:** {desc}")
            lines.append("")
            lines.append("```diff")
            lines.append(patch.rstrip())
            lines.append("```")
            lines.append("")
            # Placeholder for AI analysis
            lines.append("<!-- AI analysis: run /mx-report in Claude Code for 'why this matters' and 'suggested test' -->")
            lines.append("")

    # Crashes are kills, but they hide which other tests would have failed and
    # often point at an unsafe test helper rather than a good assertion.
    if crashed:
        lines.append("## Crashed Mutants")
        lines.append("")
        lines.append(
            "These mutants made the test process crash. They count as killed, but the "
            "crash stopped the run early, so other failing tests went unobserved, and "
            "a crash from undefined behaviour may not reproduce on another platform. "
            "Check the tests for unsafe helpers, such as indexing an empty container "
            "after a non-fatal assertion."
        )
        lines.append("")
        for m in crashed:
            lines.append(f"### Mutant {m['id']} — `{m.get('file', 'unknown')}`:{m.get('line', '?')}")
            lines.append("")
            lines.append(m.get("description", ""))
            lines.append("")
            lines.append("```text")
            lines.append(m.get("test_output", "").rstrip())
            lines.append("```")
            lines.append("")

    # Killed mutants table
    if all_killed:
        lines.append("## Killed Mutants ✓")
        lines.append("")
        lines.append("| ID | File | Line | Category | Description |")
        lines.append("|----|------|------|----------|-------------|")
        notes = {
            "killed-crash": " (crash)",
            "killed-build": " (build failed)",
            "timeout": " (timeout)",
        }
        for m in all_killed:
            mid = m["id"]
            f = m.get("file", "")
            line = m.get("line", "")
            cat = m.get("category", "").replace("_", " ")
            desc = m.get("description", "")
            status_note = notes.get(m["status"], "")
            lines.append(f"| {mid} | {f} | {line} | {cat}{status_note} | {desc} |")
        lines.append("")

    # Skipped mutants
    if skipped:
        lines.append("## Skipped Mutants")
        lines.append("")
        lines.append("| ID | File | Reason |")
        lines.append("|----|------|--------|")
        for m in skipped:
            mid = m["id"]
            f = m.get("file", "")
            reason = m.get("test_output", "unknown")
            lines.append(f"| {mid} | {f} | {reason} |")
        lines.append("")

    return "\n".join(lines)


def update_manifest_summary(manifest: dict) -> dict:
    mutants = manifest.get("mutants", [])

    def count(status: str) -> int:
        return sum(1 for m in mutants if m["status"] == status)

    killed = count("killed")
    crashed = count("killed-crash")
    build_failed = count("killed-build")
    survived = count("survived")
    timeout_count = count("timeout")
    skipped = count("skipped")
    total = len(mutants)
    all_killed = killed + crashed + build_failed + timeout_count
    testable = all_killed + survived
    score = all_killed / testable if testable > 0 else 0.0

    manifest["summary"] = {
        "total": total,
        "killed": killed,
        "killed_crash": crashed,
        "killed_build": build_failed,
        "survived": survived,
        "timeout": timeout_count,
        "skipped": skipped,
        "score": round(score, 4),
        "tested_at": datetime.now(timezone.utc).isoformat(),
    }
    return manifest


def main():
    parser = argparse.ArgumentParser(description="MutantX deterministic report generator")
    parser.add_argument(
        "--mutants-dir",
        type=Path,
        default=Path(".mutants"),
        help="Path to the mutants directory (default: .mutants)",
    )
    args = parser.parse_args()

    manifest_path = args.mutants_dir / "manifest.json"
    if not manifest_path.exists():
        print(f"ERROR: {manifest_path} not found. Run /mx-generate first.", file=sys.stderr)
        sys.exit(1)

    with open(manifest_path) as f:
        manifest = json.load(f)

    mutants = manifest.get("mutants", [])
    pending = [m for m in mutants if m.get("status") == "pending"]
    if pending:
        print(f"WARNING: {len(pending)} mutants still pending. Run mx-test.py first.", file=sys.stderr)
        print("Generating report with available results anyway.", file=sys.stderr)

    # Generate report
    report = generate_report(manifest, args.mutants_dir)
    report_path = args.mutants_dir / "report.md"
    report_path.write_text(report)
    print(f"Report written to {report_path}")

    # Update manifest summary
    manifest = update_manifest_summary(manifest)
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    # Print summary to stdout
    summary = manifest["summary"]
    all_killed = (
        summary["killed"] + summary["killed_crash"]
        + summary["killed_build"] + summary["timeout"]
    )
    testable = all_killed + summary["survived"]
    score_val = summary["score"]

    print(f"\nMutation Testing Complete!")
    print(f"  Score: {score_val:.0%} ({all_killed} killed / {testable} testable)")
    if summary["killed_crash"]:
        print(f"  Crashed: {summary['killed_crash']} mutants — see the Crashed Mutants section")
    if summary["killed_build"]:
        print(f"  Build failed: {summary['killed_build']} mutants — the generator should avoid these")
    if summary["survived"] > 0:
        print(f"  Survived: {summary['survived']} mutants — see {report_path} for details")
    else:
        print(f"  All testable mutants were killed!")


if __name__ == "__main__":
    main()
