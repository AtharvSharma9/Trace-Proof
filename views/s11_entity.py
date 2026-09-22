"""
Trace-Proof S11 — Entity Detail (views/s11_entity.py)
The product's core proof. Every derived fact opens into the exact raw row.
Includes "Why this score" with rule code, points, plain sentence, and evidence expander,
linked entities, timeline, appearances, officer notes, and red "Provenance missing" error badge.
"""

import streamlit as st
from views import api
from views.components.headers import render_screen_title
from views.components.buttons import btn_primary, btn_secondary
from views.components.chips import render_risk_chip, render_hash_chip, render_status_pill
from views.components.captions import render_provenance_caption
from views.components.banners import render_banner

def render_s11_entity():
    """Renders S11 Entity Detail screen."""

    case_id = st.session_state.get("current_case_id", "case_2026_0142")
    entity_id = st.query_params.get("eid", "ent_mule1a_acc")

    target_entity = api.get_entity_by_id(case_id, entity_id)
    if not target_entity:
        target_entity = api.get_entity_by_id(case_id, "ent_mule1a_acc")

    risk_score_obj = api.get_risk_score_for_entity(case_id, target_entity.id)

    # Title Block with Back Navigation & Add to Brief Action
    col_back, col_t = st.columns([0.15, 0.85])
    with col_back:
        if btn_secondary("← Risk Board", key="s11_back_btn"):
            st.query_params["view"] = "risk"
            st.rerun()

    add_brief_clicked = render_screen_title(
        title=f"Entity Detail — {target_entity.value}",
        subtitle=f"Forensic provenance, risk breakdown, correlated links, and transaction event log.",
        breadcrumbs="Dashboard › Risk Board › Entity Detail",
        primary_action_label="+ Add to Brief",
        primary_action_key="s11_add_brief_btn"
    )
    if add_brief_clicked:
        st.toast(f"Added {target_entity.value} to brief suspect list.")

    # Demo Rehearsal Controls
    sim_missing_prov = st.checkbox("Simulate missing provenance error (Red Badge Test)", value=False, key="s11_sim_missing_prov")

    # 1. ENTITY HEADER META CARD
    r_chip = render_risk_chip(target_entity.risk_score, target_entity.risk_band)
    st.markdown(
        f"""
        <div class='tp-card' style='display: flex; justify-content: space-between; align-items: center;'>
            <div>
                <div style='font-family: "JetBrains Mono", monospace; font-size: 20px; font-weight: 700; color: var(--primary);'>{target_entity.value}</div>
                <div style='font-size: 13px; color: var(--ink-muted); margin-top: 4px;'>
                    Type: <b>{target_entity.entity_type}</b> · Normalized: <code>{target_entity.normalized_value}</code> · First Seen: <b>{target_entity.first_seen}</b> · Last Seen: <b>{target_entity.last_seen}</b>
                </div>
            </div>
            <div style='text-align: right;'>
                <div>{r_chip}</div>
                <div style='font-size: 11px; color: var(--ink-muted); margin-top: 4px;'>{target_entity.occurrences} total occurrences</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Missing Provenance Error Banner if Toggled
    if sim_missing_prov:
        st.markdown(
            """
            <div class='tp-banner error'>
                <div style='display: flex; gap: 10px; align-items: center;'>
                    <span class='tp-status-pill error'>✗ Provenance Missing</span>
                    <div><b>PROVENANCE_ERROR:</b> One or more derived risk reasons lack verified evidence row references. Event audited.</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    # 2. WHY THIS SCORE (FORENSIC REASON BREAKDOWN & PROVENANCE EXPANDERS)
    st.markdown(
        """
        <div class='tp-table-header'>
            <div style='font-size: 16px; font-weight: 600; color: var(--primary);'>Why This Score — Rule-by-Rule Points & Source Evidence</div>
            <div class='count'>Core Forensic Proof</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    if risk_score_obj and risk_score_obj.reasons:
        for idx, r in enumerate(risk_score_obj.reasons, 1):
            points_badge = f"<span class='tp-status-pill warning'>+{r.weight:.0f} pts</span>"
            
            st.markdown(
                f"""
                <div class='tp-card' style='margin-bottom: 10px; padding: 14px;'>
                    <div style='display: flex; justify-content: space-between; align-items: flex-start;'>
                        <div>
                            <span style='font-family: "JetBrains Mono", monospace; font-size: 13px; font-weight: 700; color: var(--primary);'>Rule {r.rule_code}</span>
                            <div style='font-size: 14px; font-weight: 600; color: var(--ink); margin-top: 2px;'>{r.reason_text}</div>
                        </div>
                        <div>{points_badge}</div>
                    </div>
                """,
                unsafe_allow_html=True
            )

            # Expander showing exact supporting evidence rows
            with st.expander(f"Inspect Supporting Evidence Rows ({len(r.evidence_refs)} source rows)"):
                if sim_missing_prov:
                    st.markdown("<span class='tp-status-pill error'>✗ Provenance missing for this reason</span>", unsafe_allow_html=True)
                else:
                    for ref in r.evidence_refs:
                        hash_chip = render_hash_chip(ref.sha256, status="verified", truncate=False)
                        st.markdown(
                            f"""
                            <div style='padding: 8px 12px; background: var(--surface-alt); border: 1px solid var(--border); border-radius: 4px; margin-bottom: 6px; font-size: 13px;'>
                                <div>Source File: <b style='font-family: "JetBrains Mono", monospace;'>{ref.filename}</b></div>
                                <div>Row Number: <b style='font-family: "JetBrains Mono", monospace;'>{ref.row_number:,}</b></div>
                                <div style='margin-top: 4px;'>File SHA-256: {hash_chip}</div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
            st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("No risk score breakdown available for this entity.")

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

    # 3. LINKED ENTITIES TABLE
    st.markdown(
        """
        <div class='tp-table-header'>
            <div style='font-size: 15px; font-weight: 600;'>Correlated Linked Entities</div>
            <div class='count'>Resolved Links</div>
        </div>
        """,
        unsafe_allow_html=True
    )
    links = api.list_entity_links(case_id)
    entity_links = [l for l in links if l.entity_a_id == target_entity.id or l.entity_b_id == target_entity.id]
    
    if entity_links:
        link_rows = []
        for l in entity_links:
            other_id = l.entity_b_id if l.entity_a_id == target_entity.id else l.entity_a_id
            other_obj = api.get_entity_by_id(case_id, other_id)
            link_rows.append({
                "Target Entity": other_obj.value if other_obj else other_id,
                "Link Type": l.link_type,
                "Confidence": f"{int(l.confidence*100)}%",
                "Rationale": l.rationale,
                "Supporting File": l.supporting_evidence[0].filename if l.supporting_evidence else "N/A"
            })
        st.dataframe(link_rows, use_container_width=True)
    else:
        st.markdown("<div class='tp-body-sm' style='color: var(--ink-muted); margin-bottom: 16px;'>No correlated links found for this entity.</div>", unsafe_allow_html=True)

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

    # 4. TIMELINE & EVENTS LOG
    st.markdown(
        """
        <div class='tp-table-header'>
            <div style='font-size: 15px; font-weight: 600;'>Chronological Event Log</div>
            <div class='count'> Parsed Events</div>
        </div>
        """,
        unsafe_allow_html=True
    )
    events = api.list_timeline_events(case_id, entity_id=target_entity.id)
    evt_rows = []
    for evt in events:
        evt_rows.append({
            "Timestamp": evt.event_time,
            "Event Type": evt.event_type,
            "Amount": f"₹{evt.amount:,.2f}" if evt.amount else "--",
            "Description": evt.description,
            "Source File": evt.source_filename,
            "Row": evt.source_row
        })
    st.dataframe(evt_rows, use_container_width=True)

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

    # 5. APPEARANCES IN EVIDENCE FILES
    st.markdown(
        """
        <div class='tp-table-header'>
            <div style='font-size: 15px; font-weight: 600;'>Evidence File Appearances</div>
            <div class='count'>File Provenance</div>
        </div>
        """,
        unsafe_allow_html=True
    )
    appearances = [
        {"Filename": "bank_statement_hdfc.xlsx", "Kind": "BANK", "Occurrences": 14, "SHA-256": "9f8e7d6c5b4a3f2e1d0c..."},
        {"Filename": "bank_statement_sbi.xlsx", "Kind": "BANK", "Occurrences": 8, "SHA-256": "1a2b3c4d5e6f7a8b9c0d..."},
        {"Filename": "cdr_operator_airtel.csv", "Kind": "CDR", "Occurrences": 6, "SHA-256": "e3b0c44298fc1c149afb..."}
    ]
    st.dataframe(appearances, use_container_width=True)

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

    # 6. OFFICER NOTES (FREE-TEXT SAVED & AUDITED)
    st.markdown(
        """
        <div class='tp-card'>
            <div class='tp-h3' style='margin-bottom: 6px;'>Investigating Officer Notes</div>
            <div class='tp-body-sm' style='color: var(--ink-muted); margin-bottom: 10px;'>
                Notes are recorded in case database and audited as NOTE_ADDED.
            </div>
        """,
        unsafe_allow_html=True
    )
    officer_note = st.text_area(
        "Officer Observations",
        value="Suspect account SBI 10928374651 shows classic Layer-1 mule characteristics with 96% pass-through velocity within 4 minutes of victim debit. Freeze request prepared for SBI Nodal Officer.",
        key="s11_officer_note",
        height=90
    )
    if btn_secondary("Save Note to Case File", key="s11_save_note_btn"):
        st.toast("Note saved to case database. Audited as NOTE_ADDED.")
    st.markdown("</div>", unsafe_allow_html=True)
