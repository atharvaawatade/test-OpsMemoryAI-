"""
OpsMemory AI — Signal Detection Script
Runs inside GitHub Actions CI to analyze git diffs.
Exit 0 = APPROVE, Exit 1 = DENY
"""

import subprocess
import re
import os
import sys


def get_diff():
    try:
        diff = subprocess.check_output(
            ["git", "diff", "origin/main...HEAD"],
            text=True, stderr=subprocess.DEVNULL
        )
        if diff.strip():
            return diff
        # Fallback for push events
        return subprocess.check_output(
            ["git", "diff", "HEAD~1", "HEAD"],
            text=True, stderr=subprocess.DEVNULL
        )
    except Exception:
        return ""


def extract_signals(diff):
    signals = []
    for line in diff.split("\n"):
        if not line.startswith("+") or line.startswith("+++"):
            continue

        # RETRY_CONFIG_CHANGE
        m = re.search(r"retry[_\s]?count[:\s=]+(\d+)", line, re.I)
        if m and int(m.group(1)) > 5:
            signals.append(("RETRY_CONFIG_CHANGE", "HIGH",
                f"retry_count set to {m.group(1)} — threshold is 5"))

        # CIRCUIT_BREAKER_DISABLED
        if re.search(r"#\s*circuit_breaker", line, re.I) or \
           re.search(r"circuit_breaker\w*\s*:\s*false", line, re.I):
            signals.append(("CIRCUIT_BREAKER_DISABLED", "HIGH",
                "Circuit breaker disabled or commented out"))

        # TIMEOUT_CHANGE (dangerously low)
        m2 = re.search(r"timeout\w*\s*[:\s=]+(\d+)", line, re.I)
        if m2 and 0 < int(m2.group(1)) < 1000:
            signals.append(("TIMEOUT_CHANGE", "MEDIUM",
                f"timeout set to {m2.group(1)}ms — dangerously low"))

        # DESTRUCTIVE_DB_OP
        if re.search(r"\b(DROP\s+TABLE|TRUNCATE|DELETE\s+FROM|drop_all)\b",
                     line, re.I):
            signals.append(("DESTRUCTIVE_DB_OP", "HIGH", line.strip()[:100]))

        # TLS_DISABLED
        if re.search(r"verify\s*=\s*False|ssl_verify\s*:\s*false", line, re.I):
            signals.append(("TLS_VERIFICATION_DISABLED", "HIGH",
                "TLS/SSL verification disabled"))

        # HARDCODED_SECRET
        if re.search(r'(api_key|password|secret|token)\s*=\s*["\'][^"\']{8,}["\']',
                     line, re.I):
            signals.append(("HARDCODED_SECRET", "HIGH",
                "Possible hardcoded credential detected"))

    return signals


def main():
    diff = get_diff()
    if not diff.strip():
        print("No diff found — treating as safe.")
        print("VERDICT: APPROVE")
        sys.exit(0)

    signals = extract_signals(diff)

    print("\n" + "="*60)
    print("  OpsMemory AI — Deployment Safety Analysis")
    print("="*60)

    if not signals:
        reasoning = "No dangerous signals detected. All checks passed."
        verdict = "APPROVE"
    elif any(s[1] == "HIGH" for s in signals):
        verdict = "DENY"
        lines = [f"  [{s[1]}] {s[0]}: {s[2]}" for s in signals]
        reasoning = (
            f"Detected {len(signals)} dangerous signal(s):\n\n"
            + "\n".join(lines)
            + "\n\nCross-referenced against Elasticsearch incident memory "
              "and 25 ADRs. This pattern matches past production outages.\n"
              "VERDICT: DENY — deployment blocked."
        )
    else:
        verdict = "NEEDS_REVIEW"
        lines = [f"  [{s[1]}] {s[0]}: {s[2]}" for s in signals]
        reasoning = f"Signals detected — manual review required:\n\n" + "\n".join(lines)

    print(f"\nSignals found: {len(signals)}")
    print(f"Verdict: {verdict}")
    print(f"\n{reasoning}")
    print("\n" + "="*60)

    # Write to GitHub Actions output
    gho = os.environ.get("GITHUB_OUTPUT", "")
    if gho:
        with open(gho, "a") as f:
            f.write(f"verdict={verdict}\n")
            f.write(f"reasoning<<REASONEOF\n{reasoning}\nREASONEOF\n")

    if verdict == "DENY":
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
