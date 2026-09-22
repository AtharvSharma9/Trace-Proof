"""
Trace-Proof Provenance & Table Captions (views/components/captions.py)
"""

def render_provenance_caption(filename: str, row_number: int, sha256: str) -> str:
    """
    Renders signature provenance caption string.
    Format: filename.ext · row N · sha256 12-char
    """
    short_hash = sha256[:12] + "…" if sha256 and len(sha256) > 12 else (sha256 or "N/A")
    formatted_row = f"{row_number:,}" if isinstance(row_number, int) else str(row_number)
    
    return f"""
    <div class='tp-provenance'>
        <span class='file-ref'>{filename}</span> · row <span style='font-family: "JetBrains Mono", monospace;'>{formatted_row}</span> · sha256 <span style='font-family: "JetBrains Mono", monospace;' title='Full SHA-256: {sha256}'>{short_hash}</span>
    </div>
    """

def render_table_header_caption(title: str, total_count: int, summary_extra: str = "") -> str:
    """
    Renders table group header with row count caption.
    """
    formatted_count = f"{total_count:,}" if isinstance(total_count, int) else str(total_count)
    return f"""
    <div class='tp-table-header'>
        <div style='font-size: 15px; font-weight: 600; color: var(--ink);'>{title}</div>
        <div class='count'>{formatted_count} rows {f"· {summary_extra}" if summary_extra else ""}</div>
    </div>
    """
