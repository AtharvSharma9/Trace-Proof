"""
tools/mockgen/generate.py
=========================
Phase 1 -- Mock data generator.

Produces 7 synthetic evidence files (~130k rows total) with a single
planted fraud ring and realistic decoys, plus a ground-truth manifest.

Files produced (in sample_data/ by default):
  1. cdr_operator_a.csv          -- CDR with Airtel-style headers
  2. cdr_operator_b.csv          -- CDR with Jio-style headers (deliberately different cols)
  3. ipdr_sample.csv             -- IP Detail Records
  4. bank_statement_hdfc.xlsx    -- HDFC bank statement
  5. upi_settlement.xlsx         -- NPCI UPI settlement sheet
  6. phishing_mail.eml           -- Phishing email: SPF-fail + spoofed call timing
  7. android_dump.json           -- Android forensic dump

ground_truth.json               -- Planted ring oracle (entities + links)

Usage:
    python tools/mockgen/generate.py --seed 42
    python tools/mockgen/generate.py --seed 42 --out sample_data
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import string
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List

try:
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment
except ImportError:
    raise SystemExit("openpyxl is required: pip install openpyxl")

# ---------------------------------------------------------------------------
# Constants -- fraud ring topology
# ---------------------------------------------------------------------------
DEFAULT_SEED = 42
DEFAULT_OUT  = "sample_data"

# Fraud timeline anchor (UTC); funds gone in 11 min
# 2026-03-04 04:53:00 UTC  ==  10:23:00 IST
T0 = datetime(2026, 3, 4, 4, 53, 0, tzinfo=timezone.utc)

VICTIM_PHONE    = "9811100001"
FRAUDSTER_PHONE = "9900099001"   # contacts victim, poses as bank helpdesk

L1_PHONES   = ["9811100101", "9811100102", "9811100103"]
L1_ACCOUNTS = ["HDFC0001001001", "HDFC0001001002", "HDFC0001001003"]
L1_UPI      = ["mule1@ybl", "mule2@ybl", "mule3@ybl"]

L2_PHONES   = ["9811100201", "9811100202"]
L2_ACCOUNTS = ["HDFC0002001001", "HDFC0002001002"]
L2_UPI      = ["layer2a@paytm", "layer2b@paytm"]

CASHOUT_PHONE   = "9811100301"
CASHOUT_ACCOUNT = "HDFC0003001001"
CASHOUT_UPI     = "cashout@upi"

VICTIM_ACCOUNT = "HDFC0000000001"
VICTIM_UPI     = "victim@okicici"
VICTIM_EMAIL   = "victim.customer@gmail.com"

FRAUDSTER_EMAIL = "no-reply@hdfc-bank-helpdesk.in"   # lookalike domain

# Correlation hook 1: two L1 mules share one handset IMEI
SHARED_IMEI = "351234567890001"

# Correlation hook 2: one IMEI paired with 4 IMSIs (SIM-swap indicator)
MULTI_IMSI_IMEI = "351234567890099"
MULTI_IMSI_LIST = [
    "404100000000101", "404100000000102",
    "404100000000103", "404100000000104",
]

# Correlation hook 3: recurring UPI beneficiary across 3 unrelated victims
RECURRING_UPI     = "recurring.mule@ybl"
UNRELATED_VICTIMS = ["9833300001", "9833300002", "9833300003"]

# Decoy 1: legitimate high-fan-in business (must NOT be flagged)
DECOY_BIZ_PHONE   = "9855500001"
DECOY_BIZ_ACCOUNT = "ICICI0099990001"
DECOY_BIZ_UPI     = "merchant.legitbiz@icici"

# Decoy 2: family sharing one handset
FAMILY_PHONES = ["9877700001", "9877700002"]
FAMILY_IMEI   = "351234560000001"

# Decoy 3: two innocent people on same CGNAT /24
CGNAT_PREFIX = "100.64.12."
CGNAT_USERS  = ["9866600001", "9866600002"]

INNOCENT_COUNT      = 200
INNOCENT_BANK_COUNT = 150
INNOCENT_UPI_COUNT  = 80


# ---------------------------------------------------------------------------
# Random helpers
# ---------------------------------------------------------------------------

def _rng(seed: int) -> random.Random:
    return random.Random(seed)


def rand_imei(r: random.Random) -> str:
    return "".join(str(r.randint(0, 9)) for _ in range(15))


def rand_imsi(r: random.Random) -> str:
    return "404" + "".join(str(r.randint(0, 9)) for _ in range(12))


def rand_phone(r: random.Random, prefix: str = "98") -> str:
    return prefix + "".join(str(r.randint(0, 9)) for _ in range(8))


def rand_account(r: random.Random, bank: str = "SBI") -> str:
    return bank + "".join(str(r.randint(0, 9)) for _ in range(10))


def rand_upi(r: random.Random, handle: str = "upi") -> str:
    user = "".join(r.choices(string.ascii_lowercase, k=8))
    return f"{user}@{handle}"


def rand_ip(r: random.Random) -> str:
    return f"{r.randint(1,254)}.{r.randint(0,254)}.{r.randint(0,254)}.{r.randint(1,254)}"


def rand_mac(r: random.Random) -> str:
    return ":".join(f"{r.randint(0,255):02x}" for _ in range(6))


def rand_utr(r: random.Random) -> str:
    return "UTR" + "".join(str(r.randint(0, 9)) for _ in range(12))


def rand_rrn(r: random.Random) -> str:
    return "".join(str(r.randint(0, 9)) for _ in range(12))


def cell_id(r: random.Random) -> str:
    return f"{r.randint(1000, 9999)}-{r.randint(10000, 99999)}"


def fmt_dt(dt: datetime, fmt: str = "%d/%m/%Y %H:%M:%S") -> str:
    """Convert UTC to IST (+05:30), then format."""
    ist = dt + timedelta(hours=5, minutes=30)
    return ist.strftime(fmt)


# ---------------------------------------------------------------------------
# Background population
# ---------------------------------------------------------------------------

def build_population(r: random.Random) -> Dict[str, Any]:
    return {
        "phones":   [rand_phone(r) for _ in range(INNOCENT_COUNT)],
        "accounts": [rand_account(r) for _ in range(INNOCENT_BANK_COUNT)],
        "upis":     [rand_upi(r) for _ in range(INNOCENT_UPI_COUNT)],
        "imeis":    [rand_imei(r) for _ in range(60)],
        "imsis":    [rand_imsi(r) for _ in range(60)],
    }


# ---------------------------------------------------------------------------
# CDR -- Operator A (Airtel-style headers)
# ---------------------------------------------------------------------------

def generate_cdr_operator_a(r: random.Random, pop: Dict, out: Path) -> List[Dict]:
    rows: List[Dict] = []

    def row(caller, callee, dt, dur, imei, imsi, cid, ctype):
        return {
            "A Party No": caller, "B Party No": callee,
            "Call Date": fmt_dt(dt), "Duration": dur,
            "IMEI": imei, "IMSI": imsi, "Cell ID": cid, "Call Type": ctype,
        }

    # Hook: fraudster calls victim 9 min before T0 (spoofed call)
    rows.append(row(FRAUDSTER_PHONE, VICTIM_PHONE,
                    T0 - timedelta(minutes=9), 312,
                    rand_imei(r), rand_imsi(r), cell_id(r), "OUT"))

    # Hook: L1[0] and L1[1] share SHARED_IMEI
    for i, ph in enumerate(L1_PHONES):
        imei = SHARED_IMEI if i < 2 else rand_imei(r)
        rows.append(row(ph, FRAUDSTER_PHONE,
                        T0 + timedelta(minutes=r.randint(1, 5)), r.randint(30, 120),
                        imei, rand_imsi(r), cell_id(r), "OUT"))
        if i < len(L1_PHONES) - 1:
            rows.append(row(ph, L1_PHONES[i + 1],
                            T0 + timedelta(minutes=r.randint(2, 8)), r.randint(20, 60),
                            imei, rand_imsi(r), cell_id(r), "OUT"))

    for j, ph in enumerate(L2_PHONES):
        rows.append(row(ph, L1_PHONES[j % len(L1_PHONES)],
                        T0 + timedelta(minutes=r.randint(6, 10)), r.randint(15, 45),
                        rand_imei(r), rand_imsi(r), cell_id(r), "IN"))

    # Hook: one IMEI with 4 different IMSIs
    for imsi in MULTI_IMSI_LIST:
        rows.append(row(r.choice(pop["phones"]), r.choice(pop["phones"]),
                        T0 - timedelta(hours=r.randint(1, 48)), r.randint(10, 300),
                        MULTI_IMSI_IMEI, imsi, cell_id(r), r.choice(["IN", "OUT"])))

    # Decoy: family sharing FAMILY_IMEI (innocent calls)
    for fph in FAMILY_PHONES:
        for _ in range(r.randint(5, 10)):
            rows.append(row(fph, r.choice(pop["phones"]),
                            T0 - timedelta(hours=r.randint(2, 200)), r.randint(10, 600),
                            FAMILY_IMEI, rand_imsi(r), cell_id(r), r.choice(["IN", "OUT"])))

    # Background noise ~50 000 rows
    all_ph = pop["phones"] + L1_PHONES + L2_PHONES + FAMILY_PHONES
    for _ in range(50_000):
        a = r.choice(all_ph)
        b = r.choice(all_ph)
        while b == a:
            b = r.choice(all_ph)
        rows.append(row(a, b,
                        T0 - timedelta(hours=r.randint(0, 720)), r.randint(5, 900),
                        r.choice(pop["imeis"]), r.choice(pop["imsis"]),
                        cell_id(r), r.choice(["IN", "OUT"])))

    _write_csv(rows, out / "cdr_operator_a.csv")
    return rows


# ---------------------------------------------------------------------------
# CDR -- Operator B (Jio-style headers -- deliberately different)
# ---------------------------------------------------------------------------

def generate_cdr_operator_b(r: random.Random, pop: Dict, out: Path) -> List[Dict]:
    rows: List[Dict] = []

    def row(caller, callee, dt, dur, imei, imsi, cid, ctype):
        return {
            "MSISDN": caller, "Dialed Number": callee,
            "Start Time": fmt_dt(dt, "%Y-%m-%d %H:%M:%S"), "Dur(s)": dur,
            "Equipment ID": imei, "SIM ID": imsi, "First CGI": cid, "Type": ctype,
        }

    rows.append(row(FRAUDSTER_PHONE, VICTIM_PHONE,
                    T0 - timedelta(minutes=4), 178,
                    rand_imei(r), rand_imsi(r), cell_id(r), "MOC"))

    for ph in L2_PHONES:
        rows.append(row(ph, CASHOUT_PHONE,
                        T0 + timedelta(minutes=r.randint(8, 11)), r.randint(10, 60),
                        rand_imei(r), rand_imsi(r), cell_id(r), "MOC"))

    # Fraudster calls 3 unrelated victims (recurring-UPI campaign link)
    for uv in UNRELATED_VICTIMS:
        rows.append(row(FRAUDSTER_PHONE, uv,
                        T0 - timedelta(days=r.randint(1, 30)), r.randint(60, 400),
                        rand_imei(r), rand_imsi(r), cell_id(r), "MOC"))

    # Background ~30 000
    all_ph = pop["phones"] + L1_PHONES + L2_PHONES + UNRELATED_VICTIMS
    for _ in range(30_000):
        a = r.choice(all_ph)
        b = r.choice(all_ph)
        while b == a:
            b = r.choice(all_ph)
        rows.append(row(a, b,
                        T0 - timedelta(hours=r.randint(0, 720)), r.randint(5, 900),
                        r.choice(pop["imeis"]), r.choice(pop["imsis"]),
                        cell_id(r), r.choice(["MOC", "MTC"])))

    _write_csv(rows, out / "cdr_operator_b.csv")
    return rows


# ---------------------------------------------------------------------------
# IPDR
# ---------------------------------------------------------------------------

def generate_ipdr(r: random.Random, pop: Dict, out: Path) -> List[Dict]:
    PAYMENT_GW = "103.51.4.2"
    rows: List[Dict] = []

    def row(phone, dt_start, dur_min, src_ip, mac, up_kb, dn_kb, dst_ip):
        dt_end = dt_start + timedelta(minutes=dur_min)
        return {
            "MSISDN": phone,
            "Start Time": fmt_dt(dt_start, "%Y-%m-%d %H:%M:%S"),
            "End Time": fmt_dt(dt_end, "%Y-%m-%d %H:%M:%S"),
            "IP Address": src_ip, "MAC Address": mac,
            "Data Uploaded (KB)": up_kb, "Data Downloaded (KB)": dn_kb,
            "Destination IP": dst_ip,
        }

    # All L1 mules hit payment gateway during fraud window
    for ph in L1_PHONES:
        rows.append(row(ph, T0 + timedelta(seconds=r.randint(30, 120)),
                        r.randint(1, 3),
                        f"49.36.{r.randint(1,254)}.{r.randint(1,254)}",
                        rand_mac(r), r.randint(10, 100), r.randint(50, 500), PAYMENT_GW))

    for ph in L2_PHONES + [CASHOUT_PHONE]:
        rows.append(row(ph, T0 + timedelta(minutes=r.randint(5, 11)), 2,
                        f"49.36.{r.randint(1,254)}.{r.randint(1,254)}",
                        rand_mac(r), r.randint(5, 50), r.randint(20, 200), PAYMENT_GW))

    # Decoy: CGNAT same /24 but unrelated activity
    macs = [rand_mac(r), rand_mac(r)]
    for i, ph in enumerate(CGNAT_USERS):
        for _ in range(r.randint(5, 15)):
            rows.append(row(ph, T0 - timedelta(hours=r.randint(1, 100)),
                            r.randint(5, 60),
                            CGNAT_PREFIX + str(r.randint(1, 254)),
                            macs[i], r.randint(100, 5000), r.randint(500, 50000),
                            rand_ip(r)))

    # Background ~20 000
    for _ in range(20_000):
        rows.append(row(r.choice(pop["phones"]),
                        T0 - timedelta(hours=r.randint(0, 720)),
                        r.randint(1, 120), rand_ip(r), rand_mac(r),
                        r.randint(10, 10000), r.randint(100, 100000), rand_ip(r)))

    _write_csv(rows, out / "ipdr_sample.csv")
    return rows


# ---------------------------------------------------------------------------
# Bank statement -- HDFC style (xlsx)
# ---------------------------------------------------------------------------

def generate_bank_statement(r: random.Random, pop: Dict, out: Path) -> List[Dict]:
    FRAUD_AMT = 480_000   # Rs 4.8 lakh
    rows: List[Dict] = []

    def row(dt, src, dst, amt, dr_cr, ref, bal, chan, narr):
        return {
            "Txn Date": fmt_dt(dt, "%d/%m/%Y %H:%M:%S"),
            "Account No": src, "Beneficiary Account": dst,
            "Amount": round(amt, 2), "Dr/Cr": dr_cr,
            "Reference No": ref, "Balance": round(bal, 2),
            "Channel": chan, "Narration": narr,
        }

    balances: Dict[str, float] = {
        acc: r.uniform(1_000, 50_000)
        for acc in [VICTIM_ACCOUNT] + L1_ACCOUNTS + L2_ACCOUNTS + [CASHOUT_ACCOUNT]
    }

    # Hop 0: Victim debit at T0
    balances[VICTIM_ACCOUNT] += FRAUD_AMT
    rows.append(row(T0, VICTIM_ACCOUNT, L1_ACCOUNTS[0], FRAUD_AMT, "DR",
                    rand_utr(r), balances[VICTIM_ACCOUNT] - FRAUD_AMT,
                    "NET_BANKING", "NEFT/Fund Transfer"))
    balances[VICTIM_ACCOUNT] -= FRAUD_AMT

    # Hop 1: L1 fan-out, 96% pass-through
    t_l1 = T0 + timedelta(minutes=1)
    per_l1 = round(FRAUD_AMT * 0.96 / len(L1_ACCOUNTS), 2)
    for i, l1 in enumerate(L1_ACCOUNTS):
        balances[l1] += per_l1
        rows.append(row(t_l1 + timedelta(seconds=i * 30),
                        L1_ACCOUNTS[0], l1, per_l1, "CR",
                        rand_utr(r), balances[l1], "IMPS", "IMPS/Layering"))
        t_fwd = t_l1 + timedelta(minutes=r.randint(2, 5))
        fwd = round(per_l1 * 0.96, 2)
        l2 = L2_ACCOUNTS[i % len(L2_ACCOUNTS)]
        rows.append(row(t_fwd, l1, l2, fwd, "DR",
                        rand_utr(r), balances[l1] - fwd, "IMPS", "IMPS/Transfer"))
        balances[l1] -= fwd
        balances[l2] += fwd

    # Hop 2: L2 -> Cashout
    for l2 in L2_ACCOUNTS:
        t_cash = T0 + timedelta(minutes=r.randint(7, 11))
        cash_amt = round(balances[l2] * 0.96, 2)
        rows.append(row(t_cash, l2, CASHOUT_ACCOUNT, cash_amt, "DR",
                        rand_utr(r), balances[l2] - cash_amt, "IMPS", "IMPS/Cashout"))
        balances[l2] -= cash_amt
        balances[CASHOUT_ACCOUNT] += cash_amt

    # Hook: recurring mule receives from 3 unrelated victim accounts
    for uv in UNRELATED_VICTIMS:
        uv_acc = rand_account(r, "SBI")
        t_rv = T0 - timedelta(days=r.randint(5, 60))
        amt = r.uniform(10_000, 200_000)
        rows.append(row(t_rv, uv_acc,
                        "HDFC" + RECURRING_UPI.replace("@", "")[:10],
                        amt, "DR", rand_utr(r), r.uniform(1_000, 50_000),
                        "UPI", f"UPI/{RECURRING_UPI}"))

    # Decoy: high-fan-in business (many customers paying)
    for _ in range(r.randint(80, 150)):
        t_biz = T0 - timedelta(hours=r.randint(1, 720))
        amt = r.uniform(500, 10_000)
        rows.append(row(t_biz, rand_account(r), DECOY_BIZ_ACCOUNT, amt, "DR",
                        rand_utr(r), r.uniform(5_000, 200_000),
                        r.choice(["UPI", "NET_BANKING", "NEFT"]), "Payment/Merchant"))

    # Background ~20 000
    accs_all = pop["accounts"] + L1_ACCOUNTS + L2_ACCOUNTS + [CASHOUT_ACCOUNT]
    for _ in range(20_000):
        src = r.choice(accs_all)
        dst = r.choice(accs_all)
        while dst == src:
            dst = r.choice(accs_all)
        amt = r.uniform(100, 500_000)
        t_bg = T0 - timedelta(hours=r.randint(0, 2160))
        rows.append(row(t_bg, src, dst, amt, r.choice(["DR", "CR"]),
                        rand_utr(r), r.uniform(100, 100_000),
                        r.choice(["NET_BANKING", "IMPS", "NEFT", "UPI"]), "Transfer"))

    _write_xlsx(rows, out / "bank_statement_hdfc.xlsx",
                sheet="HDFC Statement", hfill="1F4E79", hfont="FFFFFF")
    return rows


# ---------------------------------------------------------------------------
# UPI settlement (xlsx)
# ---------------------------------------------------------------------------

def generate_upi_settlement(r: random.Random, pop: Dict, out: Path) -> List[Dict]:
    FRAUD_AMT = 480_000
    rows: List[Dict] = []

    def row(dt, payer, payee, amt, utr, chan):
        return {
            "Settlement Date": fmt_dt(dt, "%d/%m/%Y %H:%M:%S"),
            "Payer VPA": payer, "Payee VPA": payee,
            "Txn Amount": round(amt, 2), "UTR": utr, "Channel": chan,
        }

    rows.append(row(T0, VICTIM_UPI, L1_UPI[0], FRAUD_AMT, rand_rrn(r), "UPI"))

    per_l1 = round(FRAUD_AMT * 0.96 / len(L1_UPI), 2)
    for i, l1 in enumerate(L1_UPI):
        t_fwd = T0 + timedelta(minutes=r.randint(1, 4))
        rows.append(row(t_fwd, l1, L2_UPI[i % len(L2_UPI)], per_l1, rand_rrn(r), "UPI"))

    for l2 in L2_UPI:
        t_cash = T0 + timedelta(minutes=r.randint(6, 11))
        rows.append(row(t_cash, l2, CASHOUT_UPI,
                        round(per_l1 * 0.96, 2), rand_rrn(r), "UPI"))

    # Recurring mule from 3 unrelated victims
    for uv in UNRELATED_VICTIMS:
        uv_upi = f"uvic{uv[-4:]}@okaxis"
        t_rv = T0 - timedelta(days=r.randint(3, 90))
        rows.append(row(t_rv, uv_upi, RECURRING_UPI,
                        r.uniform(5_000, 100_000), rand_rrn(r), "UPI"))

    # Decoy merchant
    handles = ["ybl", "okaxis", "okicici", "paytm"]
    for _ in range(r.randint(100, 200)):
        t_biz = T0 - timedelta(hours=r.randint(1, 2000))
        rows.append(row(t_biz,
                        rand_upi(r, r.choice(handles)), DECOY_BIZ_UPI,
                        r.uniform(100, 5_000), rand_rrn(r), "UPI"))

    # Background ~10 000
    for _ in range(10_000):
        payer = r.choice(pop["upis"])
        payee = r.choice(pop["upis"])
        while payee == payer:
            payee = r.choice(pop["upis"])
        rows.append(row(T0 - timedelta(hours=r.randint(0, 2160)),
                        payer, payee, r.uniform(10, 200_000),
                        rand_rrn(r), r.choice(["UPI", "BHIM"])))

    _write_xlsx(rows, out / "upi_settlement.xlsx",
                sheet="UPI Settlement", hfill="1B5E20", hfont="FFFFFF")
    return rows


# ---------------------------------------------------------------------------
# Phishing email (.eml)
# ---------------------------------------------------------------------------

def generate_phishing_email(out: Path) -> None:
    fraud_ts = (T0 - timedelta(minutes=9)).strftime("%a, %d %b %Y %H:%M:%S +0000")
    eml = (
        f"From: HDFC Bank Customer Care <customercare@hdfcbank.com>\n"
        f"To: {VICTIM_EMAIL}\n"
        f"Subject: URGENT: Your account access has been restricted - Verify immediately\n"
        f"Date: {fraud_ts}\n"
        f"Message-ID: <fraud.{uuid.uuid4().hex}@hdfc-bank-helpdesk.in>\n"
        f"MIME-Version: 1.0\n"
        f"Return-Path: <no-reply@hdfc-bank-helpdesk.in>\n"
        f"Received: from mail.hdfc-bank-helpdesk.in (mail.hdfc-bank-helpdesk.in [185.220.101.42])\n"
        f"        by mx.gmail.com (Postfix) with ESMTP\n"
        f"        for <{VICTIM_EMAIL}>; {fraud_ts}\n"
        f"Received: from [192.168.1.10] (fraudster-machine.local [192.168.1.10])\n"
        f"        by mail.hdfc-bank-helpdesk.in (Postfix) with ESMTP\n"
        f"        for <{VICTIM_EMAIL}>; {fraud_ts}\n"
        f"Authentication-Results: mx.gmail.com;\n"
        f"       spf=fail (google.com: domain of no-reply@hdfc-bank-helpdesk.in does not"
        f" designate 185.220.101.42 as permitted sender)"
        f" smtp.mailfrom=no-reply@hdfc-bank-helpdesk.in;\n"
        f"       dkim=none header.d=hdfc-bank-helpdesk.in;\n"
        f"       dmarc=fail (p=REJECT sp=REJECT dis=NONE) header.from=hdfcbank.com\n"
        f"X-Mailer: PHPMailer 6.0 (fraudkit)\n"
        f"Content-Type: text/html; charset=UTF-8\n"
        f"\n"
        f"<!DOCTYPE html>\n"
        f"<html><head><title>Account Verification Required</title></head><body>\n"
        f"<p>Dear Valued Customer,</p>\n"
        f"<p>We have detected <b>suspicious activity</b> on your HDFC Bank account ending"
        f" in 0001. Your account has been temporarily restricted.</p>\n"
        f"<p>To restore access, please call our helpdesk immediately:"
        f" <b>+91-{FRAUDSTER_PHONE}</b></p>\n"
        f"<p>Failure to verify within 2 hours will result in permanent account suspension.</p>\n"
        f"<p>HDFC Bank Security Team</p>\n"
        f"</body></html>\n"
    )
    (out / "phishing_mail.eml").write_text(eml, encoding="utf-8")


# ---------------------------------------------------------------------------
# Android forensic dump (.json)
# ---------------------------------------------------------------------------

def generate_android_dump(r: random.Random, out: Path) -> None:
    dump = {
        "dump_metadata": {
            "tool": "UFED Physical Analyzer 7.x",
            "device": "Xiaomi Redmi Note 12",
            "dump_time": fmt_dt(T0 + timedelta(hours=6), "%Y-%m-%dT%H:%M:%SZ"),
            "examiner": "Forensic Lab Officer",
            "case_ref": "CASE/2026/CYBER/001",
        },
        "device_info": {
            "imei":          SHARED_IMEI,        # correlation hook -- also on L1[1]
            "imei2":         rand_imei(r),
            "imsi":          MULTI_IMSI_LIST[0], # correlation hook -- multi-IMSI
            "android_id":    uuid.uuid4().hex,
            "model":         "Redmi Note 12",
            "android_ver":   "13",
            "last_known_ip": f"49.36.{r.randint(1,254)}.{r.randint(1,254)}",
            "mac_address":   rand_mac(r),
            "phone_number":  L1_PHONES[0],
        },
        "installed_apps": [
            {"package": "com.phonepe.app",        "version": "4.8.1",   "first_install": "2025-11-12"},
            {"package": "com.google.android.gm",  "version": "2023.05", "first_install": "2025-09-01"},
            {"package": "com.hdfc.mobilebanking", "version": "3.2.0",   "first_install": "2026-02-15"},
            {
                "package":             "com.remoteadmin.rat",
                "version":             "1.0.1",
                "first_install":       "2026-01-30",
                "certificate_sha256":  "ab12cd34ef56gh78ij90kl12mn34op56qr78st90uv12wx34yz56ab78cd90ef12",
                "risky_permissions":   [
                    "READ_SMS", "RECEIVE_SMS", "READ_CALL_LOG",
                    "ACCESSIBILITY_SERVICE", "SYSTEM_ALERT_WINDOW",
                ],
            },
        ],
        "contacts": [
            {"name": "Boss",    "number": FRAUDSTER_PHONE, "added": fmt_dt(T0 - timedelta(days=30))},
            {"name": "Layer2A", "number": L2_PHONES[0],   "added": fmt_dt(T0 - timedelta(days=15))},
            {"name": "Layer2B", "number": L2_PHONES[1],   "added": fmt_dt(T0 - timedelta(days=15))},
            {"name": "Family",  "number": FAMILY_PHONES[0], "added": fmt_dt(T0 - timedelta(days=200))},
        ],
        "call_log": [
            {"number": FRAUDSTER_PHONE, "type": "INCOMING",
             "date": fmt_dt(T0 - timedelta(minutes=9)), "duration": 312},
            {"number": L2_PHONES[0],   "type": "OUTGOING",
             "date": fmt_dt(T0 + timedelta(minutes=3)), "duration": 45},
            {"number": VICTIM_PHONE,   "type": "MISSED",
             "date": fmt_dt(T0 + timedelta(hours=1)),   "duration": 0},
        ],
        "sms_messages": [
            {
                "from": "HDFCBK", "to": L1_PHONES[0],
                "date": fmt_dt(T0 - timedelta(seconds=30)),
                "body": "HDFC: OTP for transaction is 847291. Valid for 10 mins. Do NOT share.",
            },
            {
                "from": FRAUDSTER_PHONE, "to": L1_PHONES[0],
                "date": fmt_dt(T0 + timedelta(minutes=1)),
                "body": "Amount aa gaya. Aage bhej do jaldi.",
            },
            {
                "from": "PHONEPE", "to": L1_PHONES[0],
                "date": fmt_dt(T0 + timedelta(minutes=2)),
                "body": f"Rs.{int(480000*0.96/3)} credited to your PhonePe wallet from {VICTIM_UPI}.",
            },
        ],
        "apk_artifacts": [
            {
                "filename":            "RemoteAdmin_v1.0.1.apk",
                "package":             "com.remoteadmin.rat",
                "sha256":              "ab12cd34ef56gh78ij90kl12mn34op56qr78st90uv12wx34yz56ab78cd90ef12",
                "signing_cert_issuer": "CN=FraudKit Dev, O=Unknown",
                "embedded_urls":       ["http://185.220.101.42/cmd", "http://185.220.101.42/upload"],
                "permissions":         [
                    "READ_SMS", "RECEIVE_SMS", "READ_CALL_LOG",
                    "ACCESSIBILITY_SERVICE", "SYSTEM_ALERT_WINDOW",
                ],
            }
        ],
    }
    (out / "android_dump.json").write_text(
        json.dumps(dump, indent=2, ensure_ascii=False), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# Ground truth oracle
# ---------------------------------------------------------------------------

def write_ground_truth(out: Path) -> None:
    gt = {
        "_description": "Ground truth for Trace-Proof Phase 1 mock dataset (seed=42).",
        "fraud_ring": {
            "summary": (
                "Victim duped into transferring Rs 4.8L; layered through "
                "3 L1 mules + 2 L2 mules to ATM cashout in 11 minutes."
            ),
            "timeline_minutes":  11,
            "total_amount_inr":  480_000,
            "pass_through_ratio": 0.96,
            "hops": 3,
        },
        "entities": {
            "victim": {
                "phone": VICTIM_PHONE, "account": VICTIM_ACCOUNT,
                "upi": VICTIM_UPI, "email": VICTIM_EMAIL, "role": "VICTIM",
            },
            "fraudster": {
                "phone": FRAUDSTER_PHONE, "email": FRAUDSTER_EMAIL, "role": "FRAUDSTER",
            },
            "l1_mules": [
                {"phone": L1_PHONES[i], "account": L1_ACCOUNTS[i],
                 "upi": L1_UPI[i], "role": "L1_MULE"} for i in range(3)
            ],
            "l2_mules": [
                {"phone": L2_PHONES[i], "account": L2_ACCOUNTS[i],
                 "upi": L2_UPI[i], "role": "L2_MULE"} for i in range(2)
            ],
            "cashout": {
                "phone": CASHOUT_PHONE, "account": CASHOUT_ACCOUNT,
                "upi": CASHOUT_UPI, "role": "CASHOUT",
            },
        },
        "correlation_hooks": [
            {
                "type": "SHARED_IMEI", "imei": SHARED_IMEI,
                "phones": [L1_PHONES[0], L1_PHONES[1]],
                "description": "Two L1 mules share one handset IMEI.",
            },
            {
                "type": "MULTI_IMSI", "imei": MULTI_IMSI_IMEI,
                "imsis": MULTI_IMSI_LIST,
                "description": "One IMEI paired with 4 IMSIs -- SIM-swapping indicator.",
            },
            {
                "type": "RECURRING_BENEFICIARY", "upi": RECURRING_UPI,
                "victims": UNRELATED_VICTIMS,
                "description": "Same UPI beneficiary appears across 3 unrelated victims.",
            },
            {
                "type": "PHISHING_EMAIL",
                "sender": FRAUDSTER_EMAIL, "recipient": VICTIM_EMAIL,
                "spf": "fail", "dkim": "none",
                "timing_minutes_before_debit": 9,
                "description": "SPF-failing email from lookalike domain 9 min before victim debit.",
            },
            {
                "type": "SPOOFED_CALL",
                "caller": FRAUDSTER_PHONE, "callee": VICTIM_PHONE,
                "minutes_before_debit": 9,
                "description": "Fraudster calls victim 9 min before first debit.",
            },
        ],
        "decoys": [
            {
                "type": "HIGH_FAN_IN_BUSINESS",
                "phone": DECOY_BIZ_PHONE, "account": DECOY_BIZ_ACCOUNT,
                "upi": DECOY_BIZ_UPI,
                "description": "Legitimate merchant with 100+ customers. Must NOT be flagged.",
            },
            {
                "type": "FAMILY_SHARED_HANDSET", "imei": FAMILY_IMEI,
                "phones": FAMILY_PHONES,
                "description": "Family sharing one handset. SHARED_IMEI but innocent.",
            },
            {
                "type": "CGNAT_SHARED_SUBNET", "subnet": CGNAT_PREFIX + "0/24",
                "phones": CGNAT_USERS,
                "description": "Two innocent users on same CGNAT /24. IP alone must NOT trigger.",
            },
        ],
        "expected_links": [
            {"link_type": "SHARED_IMEI",
             "a": L1_PHONES[0], "b": L1_PHONES[1],
             "confidence": "HIGH", "must_find": True},
            {"link_type": "FUND_FLOW",
             "a": VICTIM_ACCOUNT, "b": L1_ACCOUNTS[0],
             "confidence": "HIGH", "must_find": True},
            {"link_type": "FUND_FLOW",
             "a": L1_ACCOUNTS[0], "b": L2_ACCOUNTS[0],
             "confidence": "HIGH", "must_find": True},
            {"link_type": "FUND_FLOW",
             "a": L2_ACCOUNTS[0], "b": CASHOUT_ACCOUNT,
             "confidence": "HIGH", "must_find": True},
            {"link_type": "RECURRING_BENEFICIARY",
             "upi": RECURRING_UPI, "victims": UNRELATED_VICTIMS,
             "confidence": "HIGH", "must_find": True},
            {"link_type": "SHARED_IMEI",
             "a": FAMILY_PHONES[0], "b": FAMILY_PHONES[1],
             "confidence": "MEDIUM", "must_find": False,
             "note": "DECOY -- family shared handset, should score LOW risk"},
        ],
        "false_link_checks": [
            {
                "desc": "CGNAT /24 alone must NOT produce FUND_FLOW or SHARED_IMEI",
                "phones": CGNAT_USERS,
                "allowed_link_types": ["SHARED_IP_SUBNET"],
            },
            {
                "desc": "Decoy merchant must NOT be classified as mule",
                "phone": DECOY_BIZ_PHONE,
                "expected_risk_band": "LOW",
            },
        ],
    }
    (out / "ground_truth.json").write_text(
        json.dumps(gt, indent=2, ensure_ascii=False), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------

def _write_csv(rows: List[Dict], path: Path) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    kb = path.stat().st_size / 1024
    print(f"  + {path.name:<44} {len(rows):>8,} rows   {kb:>7.0f} KB")


def _write_xlsx(rows: List[Dict], path: Path,
                sheet: str = "Sheet1",
                hfill: str = "1F4E79",
                hfont: str = "FFFFFF") -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = sheet
    headers = list(rows[0].keys())
    fill = PatternFill("solid", fgColor=hfill)
    font = Font(bold=True, color=hfont)
    for ci, h in enumerate(headers, 1):
        c = ws.cell(row=1, column=ci, value=h)
        c.fill = fill
        c.font = font
        c.alignment = Alignment(horizontal="center")
    for row_data in rows:
        ws.append([row_data[h] for h in headers])
    wb.save(path)
    kb = path.stat().st_size / 1024
    print(f"  + {path.name:<44} {len(rows):>8,} rows   {kb:>7.0f} KB")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(
        description="Trace-Proof Phase 1 -- Synthetic evidence generator"
    )
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED,
                    help=f"Random seed (default: {DEFAULT_SEED})")
    ap.add_argument("--out",  type=str, default=DEFAULT_OUT,
                    help=f"Output directory (default: {DEFAULT_OUT})")
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    r = _rng(args.seed)
    print(f"\nTrace-Proof Mock Generator  |  seed={args.seed}  |  out={out.resolve()}\n")

    print("Building background population...")
    pop = build_population(r)
    print(f"  {INNOCENT_COUNT} phones, {INNOCENT_BANK_COUNT} accounts, "
          f"{INNOCENT_UPI_COUNT} UPI handles, 60 IMEIs, 60 IMSIs\n")

    print("Generating evidence files...")
    ra  = generate_cdr_operator_a(r, pop, out)
    rb  = generate_cdr_operator_b(r, pop, out)
    ri  = generate_ipdr(r, pop, out)
    rb2 = generate_bank_statement(r, pop, out)
    ru  = generate_upi_settlement(r, pop, out)

    generate_phishing_email(out)
    print(f"  + {'phishing_mail.eml':<44}        1 email")

    generate_android_dump(r, out)
    print(f"  + {'android_dump.json':<44}        1 dump")

    write_ground_truth(out)
    print(f"  + {'ground_truth.json':<44}       oracle")

    total = sum(len(x) for x in [ra, rb, ri, rb2, ru])
    print(f"\n  {'-'*60}")
    print(f"  Total CSV/XLSX rows : {total:,}")
    print(f"  Output              : {out.resolve()}")
    print()
    print(f"  Planted ring  : victim -> fraudster -> 3xL1 -> 2xL2 -> cashout")
    print(f"  Amount        : Rs 4,80,000  |  Window: 11 min  |  Pass-through: 96%")
    print(f"  Hooks planted : SHARED_IMEI, MULTI_IMSI, RECURRING_UPI, SPF_FAIL, SPOOFED_CALL")
    print(f"  Decoys        : HIGH_FAN_IN_BIZ, FAMILY_IMEI, CGNAT_/24")
    print(f"\n  Phase 1 complete.\n")


if __name__ == "__main__":
    main()

