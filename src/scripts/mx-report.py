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
    survived = [m for m in mutants if m["status"] == "survived"]
    timeout = [m for m in mutants if m["status"] == "timeout"]
    skipped = [m for m in mutants if m["status"] == "skipped"]
    total = len(mutants)

    testable = len(killed) + len(survived) + len(timeout)
    score = (len(killed) + len(timeout)) / testable if testable > 0 else 0.0

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
    lines.append(f"| Survived | {len(survived)} ({survived_pct}%) |")
    lines.append(f"| Timeout | {len(timeout)} |")
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

    # Killed mutants table
    if killed or timeout:
        lines.append("## Killed Mutants ✓")
        lines.append("")
        lines.append("| ID | File | Line | Category | Description |")
        lines.append("|----|------|------|----------|-------------|")
        for m in killed + timeout:
            mid = m["id"]
            f = m.get("file", "")
            line = m.get("line", "")
            cat = m.get("category", "").replace("_", " ")
            desc = m.get("description", "")
            status_note = " (timeout)" if m["status"] == "timeout" else ""
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

    killed = sum(1 for m in mutants if m["status"] == "killed")
    survived = sum(1 for m in mutants if m["status"] == "survived")
    timeout_count = sum(1 for m in mutants if m["status"] == "timeout")
    skipped = sum(1 for m in mutants if m["status"] == "skipped")
    total = len(mutants)
    testable = killed + survived + timeout_count
    score = (killed + timeout_count) / testable if testable > 0 else 0.0

    manifest["summary"] = {
        "total": total,
        "killed": killed,
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
    testable = summary["killed"] + summary["survived"] + summary["timeout"]
    score_val = summary["score"]

    print(f"\nMutation Testing Complete!")
    print(f"  Score: {score_val:.0%} ({summary['killed'] + summary['timeout']} killed / {testable} testable)")
    if summary["survived"] > 0:
        print(f"  Survived: {summary['survived']} mutants — see {report_path} for details")
    else:
        print(f"  All testable mutants were killed!")


if __name__ == "__main__":
    main()
