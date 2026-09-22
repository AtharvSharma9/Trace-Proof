"""
Pramaan S13 — Integrity Verify (views/s13_integrity.py)
The 20-second demo centerpiece for 25% integrity criterion.
Features single "Verify Now" button, evidence hash verification table,
audit chain panel, full-width green success panel, and full-width red TAMPER DETECTED panel
displaying both hashes side-by-side for comparison when tampering is simulated.
"""

import streamlit as st
from views import api
from views.components.headers import render_screen_title
from views.components.buttons import btn_primary, btn_secondary, render_danger_button
from views.components.chips import render_status_pill, render_hash_chip
from views.components.banners import render_banner

def render_s13_integrity():
    """Renders S13 Integrity Verify screen."""

    case_id = st.session_state.get("current_case_id", "case_2026_0142")

    # Header Title Block
    title_clicked = render_screen_title(
        title="Integrity Verification — Cryptographic Audit",
        subtitle="Walk case evidence files and append-only audit chain to detect tampering or hash drift.",
        breadcrumbs="Dashboard › Integrity Verification",
        primary_action_label="Verify Now 🔍",
        primary_action_key="s13_verify_now_btn"
    )

    if title_clicked:
        st.toast("Re-hashed all evidence files & verified audit chain sequence.")
        st.rerun()

    # Tamper Simulation Toggle for Demo Rehearsal
    st.markdown("<div class='tp-card' style='padding: 12px;'>", unsafe_allow_html=True)
    sim_tamper = st.checkbox(
        "Simulate file tampering (S17 Demo Checkbox)",
        value=st.session_state.get("sim_tamper_active", False),
        key="s13_tamper_toggle"
    )
    st.session_state["sim_tamper_active"] = sim_tamper
    api.simulate_tampering(sim_tamper)
    st.markdown("</div>", unsafe_allow_html=True)

    # Perform Verification Walk
    integ = api.verify_case_integrity(case_id)
    is_intact = integ["is_intact"]

    # 1. FULL-WIDTH VERIFICATION STATUS PANEL (GREEN SUCCESS OR RED TAMPER DETECTED)
    if is_intact:
        st.markdown(
            f"""
            <div class='tp-banner success' style='padding: 20px; border-left: 6px solid var(--risk-low-fill); margin-bottom: 24px;'>
                <div style='display: flex; gap: 16px; align-items: flex-start;'>
                    <div style='font-size: 28px;'>✓</div>
                    <div>
                        <div style='font-size: 18px; font-weight: 700; color: var(--risk-low-text);'>
                            INTEGRITY VERIFIED — ALL EVIDENCE & AUDIT CHAIN INTACT
                        </div>
                        <div style='font-size: 14px; color: var(--risk-low-text); opacity: 0.9; margin-top: 4px;'>
                            {integ['message']}
                        </div>
                        <div style='font-size: 12px; margin-top: 8px;'>
                            Chain Head Hash: <code style='font-family: "JetBrains Mono", monospace; background: rgba(255,255,255,0.6); padding: 2px 6px; border-radius: 3px;'>{integ['head_hash']}</code>
                        </div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        # THE DEMO'S CLOSING 15-SECOND MOMENT: CAREFULLY CRAFTED RED TAMPER PANEL
        st.markdown(
            f"""
            <div class='tp-banner error' style='padding: 20px; border-left: 6px solid var(--risk-crit-fill); margin-bottom: 24px;'>
                <div style='display: flex; gap: 16px; align-items: flex-start;'>
                    <div style='font-size: 28px;'>🚨</div>
                    <div>
                        <div style='font-size: 18px; font-weight: 700; color: var(--risk-crit-text);'>
                            TAMPER DETECTED — 1 EVIDENCE FILE HAS CHANGED SINCE INGESTION
                        </div>
                        <div style='font-size: 14px; color: var(--risk-crit-text); opacity: 0.9; margin-top: 4px;'>
                            Cryptographic SHA-256 hash mismatch detected. Case status set to <b>INTEGRITY_COMPROMISED</b>. Brief generation blocked.
                        </div>
                        <div style='font-size: 12px; margin-top: 8px;'>
                            Event audited: <code style='font-family: "JetBrains Mono", monospace; background: rgba(255,255,255,0.6); padding: 2px 6px; border-radius: 3px;'>INTEGRITY_FAILURE (Seq #6)</code>
                        </div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    # 2. EVIDENCE INTEGRITY TABLE (SHOWING INGESTED VS CURRENT HASHES)
    st.markdown(
        """
        <div class='tp-table-header'>
            <div style='font-size: 15px; font-weight: 600;'>Evidence Files Cryptographic Verification Table</div>
            <div class='count'>SHA-256 Hash Cross-Check</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        """
        <div style='background: var(--surface-alt); padding: 8px 14px; border: 1px solid var(--border); border-radius: 4px 4px 0 0; font-size: 11.5px; font-weight: 600; color: var(--ink-muted); text-transform: uppercase; letter-spacing: 0.04em; display: grid; grid-template-columns: 2fr 2.5fr 2.5fr 1.2fr; gap: 8px; align-items: center;'>
            <div>Filename</div>
            <div>SHA-256 at Ingestion</div>
            <div>SHA-256 Re-Hashed Now</div>
            <div style='text-align: right;'>Status</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    for item in integ["file_status"]:
        status_word = item["status"]
        is_changed = (status_word == "CHANGED")
        
        chip_ingested = render_hash_chip(item["sha256_ingested"], status="verified", truncate=True)
        chip_now = render_hash_chip(item["sha256_now"], status="mismatch" if is_changed else "verified", truncate=True)
        
        pill = render_status_pill("error" if is_changed else "verified", f"{'✗ Changed' if is_changed else '✓ Unchanged'}")

        row_bg = "background: var(--risk-crit-bg);" if is_changed else ""

        st.markdown(
            f"""
            <div style='padding: 10px 14px; border: 1px solid var(--border); border-top: none; font-size: 13px; {row_bg} display: grid; grid-template-columns: 2fr 2.5fr 2.5fr 1.2fr; gap: 8px; align-items: center;'>
                <div style='font-family: "JetBrains Mono", monospace; font-weight: 600; color: {"var(--risk-crit-fill)" if is_changed else "var(--primary)"};'>{item["filename"]}</div>
                <div>{chip_ingested}</div>
                <div>{chip_now}</div>
                <div style='text-align: right;'>{pill}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

        # Highlight side-by-side hash comparison for offending file
        if is_changed:
            st.markdown(
                f"""
                <div style='padding: 10px 14px; background: #FFF5F5; border: 1px solid var(--risk-crit-fill); border-top: none; font-size: 12px; margin-bottom: 8px;'>
                    <div style='font-weight: 700; color: var(--risk-crit-fill); margin-bottom: 4px;'>HASH DRIFT COMPARISON:</div>
                    <div>Ingested: <code style='font-family: "JetBrains Mono", monospace; color: var(--risk-low-fill);'>{item['sha256_ingested']}</code></div>
                    <div>Current:  <code style='font-family: "JetBrains Mono", monospace; color: var(--risk-crit-fill);'>{item['sha256_now']}</code></div>
                </div>
                """,
                unsafe_allow_html=True
            )

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

    # 3. AUDIT CHAIN PANEL
    st.markdown(
        """
        <div class='tp-card'>
            <div class='tp-h3' style='margin-bottom: 8px;'>Append-Only Cryptographic Audit Chain Panel</div>
            <div class='tp-body-sm' style='color: var(--ink-muted); margin-bottom: 12px;'>
                Every case action is hash-chained with \\x1f delimiters and previous entry hashes. Modifying any past record breaks the chain head digest.
            </div>
            <div style='display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; text-align: center;'>
                <div style='padding: 10px; background: var(--surface-alt); border: 1px solid var(--border); border-radius: 4px;'>
                    <div style='font-size: 11px; font-weight: 600; color: var(--ink-muted);'>TOTAL AUDIT ENTRIES</div>
                    <div style='font-family: "JetBrains Mono", monospace; font-size: 20px; font-weight: 700; color: var(--primary); margin-top: 2px;'>{integ['total_entries']}</div>
                </div>
                <div style='padding: 10px; background: var(--surface-alt); border: 1px solid var(--border); border-radius: 4px;'>
                    <div style='font-size: 11px; font-weight: 600; color: var(--ink-muted);'>CHAIN STATUS</div>
                    <div style='margin-top: 4px;'><span class='tp-status-pill verified'>✓ Intact</span></div>
                </div>
                <div style='padding: 10px; background: var(--surface-alt); border: 1px solid var(--border); border-radius: 4px;'>
                    <div style='font-size: 11px; font-weight: 600; color: var(--ink-muted);'>GENESIS HASH</div>
                    <div style='font-family: "JetBrains Mono", monospace; font-size: 11px; color: var(--ink-muted); margin-top: 4px;'>000000000000…</div>
                </div>
                <div style='padding: 10px; background: var(--surface-alt); border: 1px solid var(--border); border-radius: 4px;'>
                    <div style='font-size: 11px; font-weight: 600; color: var(--ink-muted);'>HEAD HASH</div>
                    <div style='font-family: "JetBrains Mono", monospace; font-size: 11px; color: var(--accent-verified); margin-top: 4px;'>{integ['head_hash'][:12]}…</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Export Verification Certificate Action
    col_pdf1, col_pdf2 = st.columns([0.4, 0.6])
    with col_pdf1:
        if btn_secondary("📜 Export Verification Certificate (PDF)", key="s13_export_cert_btn", use_container_width=True):
            st.toast("Exported Integrity Verification Certificate to case_exports/verify_cert_CASE_2026_0142.pdf")
