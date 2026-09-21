"""
tools/mockgen/generate.py

Phase 1 mock data generator.
Produces 7 files with one coherent fraud ring + realistic decoys.
Seed is a parameter (default 42).

Output files:
  cdr_operator_a.csv     — CDR with IMEI/IMSI
  cdr_operator_b.csv     — CDR with different header names
  bank_statement_hdfc.xlsx
  upi_settlement.xlsx
  ground_truth.json      — planted ring, expected entities, expected links
"""
from __future__ import annotations

import csv
import json
import random
import string
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Dict

try:
    import openpyxl
    from openpyxl import Workbook
    _HAS_XLSX = True
except ImportError:
    _HAS_XLSX = False

SEED = 42

# ── Population sizes ──────────────────────────────────────────────────────────
N_INNOCENT_PHONES   = 80
N_MULE_L1           = 3
N_MULE_L2           = 2
N_CASHOUT           = 1

# ── Fraud ring timings ────────────────────────────────────────────────────────
FRAUD_BASE = datetime(2026, 9, 10, 10, 0, 0, tzinfo=timezone.utc)


def _rand_phone(rng: random.Random) -> str:
    return "+91" + "".join(str(rng.randint(0, 9)) for _ in range(10))


def _rand_imei(rng: random.Random) -> str:
    """Generate a syntactically valid IMEI (Luhn checksum)."""
    digits = [rng.randint(0, 9) for _ in range(14)]
    checksum = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2 == 0:
            d *= 2
            if d > 9:
                d -= 9
        checksum += d
    check_digit = (10 - (checksum % 10)) % 10
    return "".join(str(d) for d in digits) + str(check_digit)


def _rand_imsi(rng: random.Random) -> str:
    return "404" + "".join(str(rng.randint(0, 9)) for _ in range(12))


def _rand_account(rng: random.Random) -> str:
    return "".join(str(rng.randint(0, 9)) for _ in range(12))


def _rand_upi(phone: str, rng: random.Random) -> str:
    psp = rng.choice(["okaxis", "ybl", "paytm", "upi", "icici"])
    suffix = phone[-4:]
    return f"usr{suffix}@{psp}"


def generate(output_dir: Path, seed: int = SEED) -> Dict:
    rng = random.Random(seed)
    output_dir.mkdir(parents=True, exist_ok=True)

    # ── Identities ─────────────────────────────────────────────────────────
    victim_phone  = _rand_phone(rng)
    victim_acct   = _rand_account(rng)
    fraudster     = _rand_phone(rng)

    mule_l1_phones  = [_rand_phone(rng) for _ in range(N_MULE_L1)]
    mule_l2_phones  = [_rand_phone(rng) for _ in range(N_MULE_L2)]
    cashout_phone   = _rand_phone(rng)

    mule_l1_accts   = [_rand_account(rng) for _ in range(N_MULE_L1)]
    mule_l2_accts   = [_rand_account(rng) for _ in range(N_MULE_L2)]
    cashout_acct    = _rand_account(rng)

    # Two mules share one IMEI (planted hook for R06 / SHARED_IMEI)
    shared_imei     = _rand_imei(rng)
    # One IMEI with 4 IMSIs (planted hook for R05 / SIM-switch velocity)
    multi_imei      = _rand_imei(rng)
    multi_imsis     = [_rand_imsi(rng) for _ in range(4)]

    mule_l1_imeis   = [shared_imei, shared_imei, _rand_imei(rng)]
    mule_l1_imsis   = [_rand_imsi(rng) for _ in range(N_MULE_L1)]

    innocent_phones = [_rand_phone(rng) for _ in range(N_INNOCENT_PHONES)]
    innocent_imeis  = [_rand_imei(rng) for _ in range(N_INNOCENT_PHONES)]
    innocent_imsis  = [_rand_imsi(rng) for _ in range(N_INNOCENT_PHONES)]

    # ── CDR Operator A ─────────────────────────────────────────────────────
    cdr_a_rows: List[dict] = []

    def _cdr_row_a(caller, callee, start_dt, dur, imei, imsi, ctype):
        return {
            "A-PARTY NO": caller,
            "B-PARTY NO": callee,
            "CALL DATE": start_dt.strftime("%d/%m/%Y %H:%M:%S"),
            "DURATION": dur,
            "IMEI": imei,
            "IMSI": imsi,
            "CALL TYPE": ctype,
        }

    # Fraudster calls victim 9 min before first debit (R11)
    t0 = FRAUD_BASE
    cdr_a_rows.append(_cdr_row_a(fraudster, victim_phone, t0, rng.randint(60, 300),
                                  _rand_imei(rng), _rand_imsi(rng), "IN"))

    # Mule L1 call chains
    for i, mp in enumerate(mule_l1_phones):
        cdr_a_rows.append(_cdr_row_a(
            fraudster, mp, t0 + timedelta(minutes=2 + i), rng.randint(30, 120),
            mule_l1_imeis[i], mule_l1_imsis[i], "OUT",
        ))

    # Two mules share IMEI — extra calls
    for mp in mule_l1_phones[:2]:
        cdr_a_rows.append(_cdr_row_a(
            mp, cashout_phone, t0 + timedelta(minutes=8), rng.randint(10, 60),
            shared_imei, _rand_imsi(rng), "OUT",
        ))

    # Innocent background noise
    for i in range(40):
        ph_a = rng.choice(innocent_phones)
        ph_b = rng.choice(innocent_phones)
        if ph_a == ph_b:
            continue
        cdr_a_rows.append(_cdr_row_a(
            ph_a, ph_b,
            t0 - timedelta(hours=rng.randint(1, 48)),
            rng.randint(5, 600),
            rng.choice(innocent_imeis),
            rng.choice(innocent_imsis),
            rng.choice(["IN", "OUT"]),
        ))

    _write_csv(output_dir / "cdr_operator_a.csv", cdr_a_rows)

    # ── CDR Operator B — deliberately different headers ─────────────────────
    cdr_b_rows = []
    for i, mp in enumerate(mule_l2_phones):
        cdr_b_rows.append({
            "Calling Number": mule_l1_phones[i % N_MULE_L1],
            "Dialed Number":  mp,
            "Start Time":     (t0 + timedelta(minutes=5 + i)).strftime("%Y-%m-%d %H:%M:%S"),
            "Dur(s)":         rng.randint(10, 90),
            "Equipment ID":   _rand_imei(rng),
            "SIM ID":         _rand_imsi(rng),
            "In/Out":         "OUT",
        })
    for i in range(30):
        ph_a = rng.choice(innocent_phones)
        ph_b = rng.choice(innocent_phones)
        if ph_a == ph_b:
            continue
        cdr_b_rows.append({
            "Calling Number": ph_a,
            "Dialed Number":  ph_b,
            "Start Time":     (t0 - timedelta(hours=rng.randint(1, 72))).strftime("%Y-%m-%d %H:%M:%S"),
            "Dur(s)":         rng.randint(5, 400),
            "Equipment ID":   rng.choice(innocent_imeis),
            "SIM ID":         rng.choice(innocent_imsis),
            "In/Out":         rng.choice(["IN", "OUT"]),
        })
    _write_csv(output_dir / "cdr_operator_b.csv", cdr_b_rows)

    # ── Bank Statement HDFC ────────────────────────────────────────────────
    txn_time = t0 + timedelta(minutes=9)
    bank_rows = [
        # Victim debit
        {"Date": txn_time.strftime("%d/%m/%Y"),
         "Account No": victim_acct, "Narration": "UPI/P2P",
         "DR": 480000.0, "CR": "", "Balance": 20000.0,
         "Reference No": "UTR" + str(rng.randint(100000, 999999))},
        # Mule L1 receives and forwards
    ]
    hop_time = txn_time
    for i, (acct, next_acct) in enumerate(zip(
        mule_l1_accts,
        mule_l2_accts + [cashout_acct],
    )):
        hop_time += timedelta(minutes=2)
        pct = 0.96
        bank_rows.append({
            "Date": hop_time.strftime("%d/%m/%Y"),
            "Account No": acct,
            "Narration": f"IMPS/P2P layer-{i+1}",
            "DR": round(480000 * (pct ** (i + 1)), 2),
            "CR": "",
            "Balance": rng.randint(500, 5000),
            "Reference No": "UTR" + str(rng.randint(100000, 999999)),
        })
    # Innocent noise
    for _ in range(20):
        bank_rows.append({
            "Date": (t0 - timedelta(days=rng.randint(1, 30))).strftime("%d/%m/%Y"),
            "Account No": _rand_account(rng),
            "Narration": rng.choice(["SALARY", "GROCERY", "RECHARGE", "EMI"]),
            "DR": round(rng.uniform(100, 5000), 2),
            "CR": "",
            "Balance": round(rng.uniform(1000, 50000), 2),
            "Reference No": "UTR" + str(rng.randint(100000, 999999)),
        })

    if _HAS_XLSX:
        _write_xlsx(output_dir / "bank_statement_hdfc.xlsx", bank_rows)

    # ── UPI Settlement ─────────────────────────────────────────────────────
    victim_upi   = _rand_upi(victim_phone, rng)
    mule_l1_upis = [_rand_upi(p, rng) for p in mule_l1_phones]
    cashout_upi  = _rand_upi(cashout_phone, rng)

    upi_rows = []
    upi_time = txn_time
    for i, (src_upi, dst_upi) in enumerate(zip(
        [victim_upi] + mule_l1_upis[:2],
        mule_l1_upis[:2] + [cashout_upi],
    )):
        upi_rows.append({
            "Txn Date": (upi_time + timedelta(minutes=i)).strftime("%d/%m/%Y %H:%M:%S"),
            "Payer VPA": src_upi,
            "Payee VPA": dst_upi,
            "Amount": round(480000 * (0.96 ** i), 2),
            "UTR": "UTR" + str(rng.randint(100000, 999999)),
            "Channel": "UPI",
        })
    for _ in range(15):
        upi_rows.append({
            "Txn Date": (t0 - timedelta(hours=rng.randint(1, 72))).strftime("%d/%m/%Y %H:%M:%S"),
            "Payer VPA": _rand_upi(_rand_phone(rng), rng),
            "Payee VPA": _rand_upi(_rand_phone(rng), rng),
            "Amount": round(rng.uniform(50, 2000), 2),
            "UTR": "UTR" + str(rng.randint(100000, 999999)),
            "Channel": "UPI",
        })

    if _HAS_XLSX:
        _write_xlsx(output_dir / "upi_settlement.xlsx", upi_rows)

    # ── Ground truth ────────────────────────────────────────────────────────
    gt = {
        "seed": seed,
        "ring": {
            "victim_phone": victim_phone,
            "victim_account": victim_acct,
            "victim_upi": victim_upi,
            "fraudster_phone": fraudster,
            "mule_l1_phones": mule_l1_phones,
            "mule_l1_accounts": mule_l1_accts,
            "mule_l1_upis": mule_l1_upis,
            "mule_l2_phones": mule_l2_phones,
            "mule_l2_accounts": mule_l2_accts,
            "cashout_phone": cashout_phone,
            "cashout_account": cashout_acct,
            "cashout_upi": cashout_upi,
        },
        "hooks": {
            "shared_imei": shared_imei,
            "mules_sharing_imei": mule_l1_phones[:2],
            "multi_sim_imei": multi_imei,
            "multi_imsis": multi_imsis,
        },
        "expected_link_types": [
            "SHARED_IMEI", "FUND_FLOW", "RECURRING_BENEFICIARY",
        ],
        "decoy_note": (
            "innocent_phones are legitimate users with no ring connection. "
            "No link between any innocent_phone should appear in the output."
        ),
    }

    with open(output_dir / "ground_truth.json", "w", encoding="utf-8") as f:
        json.dump(gt, f, indent=2)

    print(f"[mockgen] Generated {len(cdr_a_rows)} CDR-A rows, "
          f"{len(cdr_b_rows)} CDR-B rows, "
          f"{len(bank_rows)} bank rows, "
          f"{len(upi_rows)} UPI rows.")
    print(f"[mockgen] Ground truth → {output_dir/'ground_truth.json'}")
    return gt


# ── File writers ─────────────────────────────────────────────────────────────

def _write_csv(path: Path, rows: List[dict]) -> None:
    if not rows:
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def _write_xlsx(path: Path, rows: List[dict]) -> None:
    if not rows or not _HAS_XLSX:
        return
    wb = Workbook()
    ws = wb.active
    headers = list(rows[0].keys())
    ws.append(headers)
    for row in rows:
        ws.append([row.get(h, "") for h in headers])
    wb.save(path)


if __name__ == "__main__":
    import sys
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else SEED
    out = Path(__file__).parent.parent.parent / "tests" / "mock_data"
    generate(out, seed=seed)
