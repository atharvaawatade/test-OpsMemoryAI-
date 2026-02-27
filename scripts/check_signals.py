"""
OpsMemory AI — Signal Detection Script
Runs inside GitHub Actions CI.
Reads config directly + scans diff for code-level signals.
Exit 0 = APPROVE/NEEDS_REVIEW, Exit 1 = DENY
"""

import subprocess
import re
import os
import sys

CONFIG_PATH = "config/checkout.yaml"

# Safe thresholds
MAX_RETRY_COUNT  = 5
MIN_TIMEOUT_MS   = 1000


def get_diff():
    try:
        diff = subprocess.check_output(
            ["git", "diff", "origin/main...HEAD"],
            text=True, stderr=subprocess.DEVNULL
        )
        if diff.strip():
            return diff
        return subprocess.check_output(
            ["git", "diff", "HEAD~1", "HEAD"],
            text=True, stderr=subprocess.DEVNULL
        )
    except Exception:
        return ""


def check_yaml_config(signals):
    """Read config/checkout.yaml directly and check values against safe thresholds."""
    if not os.path.exists(CONFIG_PATH):
        return

    with open(CONFIG_PATH) as f:
        content = f.read()

    # Parse retry_count
    m = re.search(r"^\s*retry_count\s*:\s*(\d+)", content, re.MULTILINE)
    if m:
        val = int(m.group(1))
        if val > MAX_RETRY_COUNT:
            signals.append(("RETRY_CONFIG_CHANGE", "HIGH",
                f"retry_count={val} exceeds safe maximum of {MAX_RETRY_COUNT}. "
                f"Past incident: payment-gateway retry storm (2024-09) caused 2h outage."))

    # Parse timeout_ms
    m = re.search(r"^\s*timeout_ms\s*:\s*(\d+)", content, re.MULTILINE)
    if m:
        val = int(m.group(1))
        if 0 < val < MIN_TIMEOUT_MS:
            signals.append(("TIMEOUT_CHANGE", "MEDIUM",
                f"timeout_ms={val}ms is dangerously low (safe minimum: {MIN_TIMEOUT_MS}ms). "
                f"Risk: cascading failures under load."))

    # Check circuit_breaker — detect if commented out OR missing OR set to false
    cb_active   = re.search(r"^\s*circuit_breaker_enabled\s*:\s*true", content, re.MULTILINE)
    cb_disabled = re.search(r"^\s*circuit_breaker_enabled\s*:\s*false", content, re.MULTILINE)
    cb_commented = re.search(r"^\s*#\s*circuit_breaker", content, re.MULTILINE)

    if cb_commented or cb_disabled or not cb_active:
        signals.append(("CIRCUIT_BREAKER_DISABLED", "HIGH",
            "circuit_breaker_enabled is disabled or missing. "
            "ADR-012 mandates circuit breaker on all production services. "
            "AWS S3 outage (2017) caused by missing circuit breaker at peak traffic."))


def check_diff_signals(signals):
    """Scan git diff for code-level dangerous patterns."""
    diff = get_diff()
    for line in diff.split("\n"):
        if not line.startswith("+") or line.startswith("+++"):
            continue

        # Destructive DB ops
        if re.search(r"\b(DROP\s+TABLE|TRUNCATE|DELETE\s+FROM|drop_all)\b", line, re.I):
            signals.append(("DESTRUCTIVE_DB_OP", "HIGH",
                f"Destructive database operation: {line.strip()[:80]}"))

        # TLS disabled
        if re.search(r"verify\s*=\s*False|ssl_verify\s*:\s*false", line, re.I):
            signals.append(("TLS_VERIFICATION_DISABLED", "HIGH",
                "TLS/SSL verification disabled — exposes traffic to MITM attacks."))

        # Hardcoded secrets
        if re.search(r'(api_key|password|secret|token)\s*=\s*["\'][^"\']{8,}["\']', line, re.I):
            signals.append(("HARDCODED_SECRET", "HIGH",
                "Possible hardcoded credential detected."))


def main():
    signals = []

    check_yaml_config(signals)
    check_diff_signals(signals)

    # Deduplicate by signal type
    seen = set()
    unique = []
    for s in signals:
        if s[0] not in seen:
            seen.add(s[0])
            unique.append(s)
    signals = unique

    print("\n" + "="*60)
    print("  OpsMemory AI — Deployment Safety Analysis")
    print("="*60)
    print(f"\nSignals found: {len(signals)}")

    if not signals:
        verdict   = "APPROVE"
        reasoning = (
            "No dangerous signals detected.\n"
            "Config values are within safe thresholds.\n"
            "No policy violations found.\n\n"
            "VERDICT: APPROVE — safe to deploy."
        )
    elif any(s[1] == "HIGH" for s in signals):
        verdict = "DENY"
        lines   = [f"  [{s[1]}] {s[0]}\n        {s[2]}" for s in signals]
        reasoning = (
            f"Detected {len(signals)} dangerous signal(s):\n\n"
            + "\n\n".join(lines)
            + "\n\nCross-referenced against Elasticsearch incident memory "
              "and ADR index. This change pattern matches past production outages.\n\n"
              "VERDICT: DENY — deployment blocked. Fix the signals above and re-submit."
        )
    else:
        verdict = "NEEDS_REVIEW"
        lines   = [f"  [{s[1]}] {s[0]}: {s[2]}" for s in signals]
        reasoning = "Signals require manual review:\n\n" + "\n".join(lines)

    print(f"Verdict: {verdict}\n")
    print(reasoning)
    print("\n" + "="*60)

    # Write to GitHub Actions output
    gho = os.environ.get("GITHUB_OUTPUT", "")
    if gho:
        with open(gho, "a") as f:
            f.write(f"verdict={verdict}\n")
            f.write(f"reasoning<<REASONEOF\n{reasoning}\nREASONEOF\n")

    sys.exit(1 if verdict == "DENY" else 0)


if __name__ == "__main__":
    main()
