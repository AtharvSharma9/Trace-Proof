"""
Self-check script for Trace-Proof fixtures verification.
Validates that every risk reason and derived fact has an evidence reference (file, row, sha256).
Run directly: python views/_check_fixtures.py
"""

import sys
import os

# Add parent directory to path so views package imports work
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from views.mock.fixtures import (
    EVIDENCE_FILES, RISK_SCORES, EVENTS, LINKS, FILE_HASH_MAP
)

def run_checks():
    print("Running Trace-Proof Fixtures Verification...")
    errors = []

    # 1. Check Evidence Files
    print(f"[1/5] Checking {len(EVIDENCE_FILES)} Evidence Files...")
    for ef in EVIDENCE_FILES:
        if not ef.sha256 or len(ef.sha256) != 64:
            errors.append(f"Evidence file {ef.original_filename} has invalid SHA-256: '{ef.sha256}'")

    # 2. Check Risk Reasons Provenance
    print(f"[2/5] Checking Risk Reasons Provenance across {len(RISK_SCORES)} scored entities...")
    reasons_checked = 0
    for rs in RISK_SCORES:
        for rr in rs.reasons:
            reasons_checked += 1
            if not rr.evidence_refs:
                errors.append(f"RiskReason '{rr.rule_code}' ({rr.reason_text}) on entity {rs.entity_id} has NO evidence_refs!")
            for ref in rr.evidence_refs:
                if not ref.filename or ref.filename not in FILE_HASH_MAP:
                    errors.append(f"RiskReason '{rr.rule_code}' references unknown file: '{ref.filename}'")
                if ref.row_number <= 0:
                    errors.append(f"RiskReason '{rr.rule_code}' has invalid row_number: {ref.row_number}")
                if not ref.sha256 or len(ref.sha256) != 64:
                    errors.append(f"RiskReason '{rr.rule_code}' ref has invalid sha256: '{ref.sha256}'")
                if ref.filename in FILE_HASH_MAP and ref.sha256 != FILE_HASH_MAP[ref.filename]:
                    errors.append(f"RiskReason '{rr.rule_code}' ref sha256 mismatch for {ref.filename}")
    print(f"  Checked {reasons_checked} risk reasons.")

    # 3. Check Event Provenance
    print(f"[3/5] Checking Provenance on {len(EVENTS)} Events...")
    for evt in EVENTS:
        if not evt.source_filename or evt.source_filename not in FILE_HASH_MAP:
            errors.append(f"Event {evt.id} has invalid source_filename: '{evt.source_filename}'")
        if evt.source_row <= 0:
            errors.append(f"Event {evt.id} has invalid source_row: {evt.source_row}")
        if not evt.source_sha256 or len(evt.source_sha256) != 64:
            errors.append(f"Event {evt.id} has invalid source_sha256: '{evt.source_sha256}'")
        if evt.source_filename in FILE_HASH_MAP and evt.source_sha256 != FILE_HASH_MAP[evt.source_filename]:
            errors.append(f"Event {evt.id} source_sha256 mismatch for {evt.source_filename}")

    # 4. Check Link Provenance
    print(f"[4/5] Checking Supporting Evidence on {len(LINKS)} Entity Links...")
    for link in LINKS:
        if not link.supporting_evidence:
            errors.append(f"EntityLink {link.id} ({link.link_type}) has NO supporting_evidence!")
        for ref in link.supporting_evidence:
            if not ref.filename or ref.filename not in FILE_HASH_MAP:
                errors.append(f"EntityLink {link.id} references unknown file: '{ref.filename}'")
            if ref.row_number <= 0:
                errors.append(f"EntityLink {link.id} has invalid row_number: {ref.row_number}")
            if not ref.sha256 or len(ref.sha256) != 64:
                errors.append(f"EntityLink {link.id} has invalid sha256: '{ref.sha256}'")

    # 5. Summary
    print("[5/5] Finalizing verification results...")
    if errors:
        print(f"\nFAILED: Found {len(errors)} provenance errors:")
        for err in errors:
            print(f"  ❌ {err}")
        sys.exit(1)
    else:
        print("\nPASSED: Every risk reason and derived fact successfully verified with valid source file, row, and SHA-256 hash.")

if __name__ == "__main__":
    run_checks()
