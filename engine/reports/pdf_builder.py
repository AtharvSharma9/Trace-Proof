import json
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        canvas.Canvas.__init__(self, *args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_number(self, page_count):
        self.setFont("Helvetica", 9)
        # We need case_number, audit_head_hash, report_hash from somewhere, but for now placeholders
        footer_text = f"Case: PRAMAAN-001 | Page {self._pageNumber} of {page_count} | Audit: <pending> | Report SHA256: <pending>"
        self.drawRightString(A4[0] - 20, 20, footer_text)


def build_pdf_brief(json_path: str, graph_image_path: str, output_path: str) -> None:
    """
    Builds the final A4 PDF report using reportlab.
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=A4,
        rightMargin=20, leftMargin=20,
        topMargin=20, bottomMargin=40
    )
    
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='SectionHeader', parent=styles['Heading2'], spaceAfter=10, textColor=colors.HexColor('#1B3A5C')))
    styles.add(ParagraphStyle(name='Monospace', fontName='Courier', fontSize=9))
    
    elements = []
    
    # 1. Header Block
    case = data.get("case", {})
    elements.append(Paragraph("INVESTIGATIVE BRIEF - CONFIDENTIAL", styles['Title']))
    elements.append(Paragraph(f"Case Number: {case.get('case_number', 'N/A')} | FIR: {case.get('fir_number', 'N/A')}", styles['Normal']))
    elements.append(Paragraph(f"Officer: {case.get('created_by_badge', 'N/A')} - {case.get('created_by_name', 'N/A')}", styles['Normal']))
    elements.append(Spacer(1, 20))
    
    # Section 1 - Summary
    elements.append(Paragraph("1. Summary", styles['SectionHeader']))
    elements.append(Paragraph("Summary text goes here. (Template generated based on amount, hops, time elapsed).", styles['Normal']))
    elements.append(Spacer(1, 15))
    
    # Section 2 - Timeline
    elements.append(Paragraph("2. Timeline", styles['SectionHeader']))
    timeline_data = [["Time", "Event", "Details"]]
    for evt in data.get("timeline", [])[:10]: # up to 10 events
        timeline_data.append([evt.get("occurred_at", ""), evt.get("event_type", ""), str(evt.get("amount", ""))])
        
    if len(timeline_data) > 1:
        t = Table(timeline_data, colWidths=[100, 150, 250])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F8FAFC')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor('#0F172A')),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0,0), (-1,0), 12),
            ('GRID', (0,0), (-1,-1), 1, colors.HexColor('#E2E8F0'))
        ]))
        elements.append(t)
    elements.append(Spacer(1, 15))
    
    # Section 3 - Suspects
    elements.append(Paragraph("3. Prime Suspects", styles['SectionHeader']))
    suspect_data = [["Rank", "ID", "Type", "Score", "Band", "Top Reason"]]
    for s in data.get("suspects", []):
        suspect_data.append([str(s.get("rank")), s.get("id"), s.get("type"), str(s.get("score")), s.get("band"), s.get("reason")])
        
    if len(suspect_data) > 1:
        st = Table(suspect_data)
        st.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F8FAFC')),
            ('GRID', (0,0), (-1,-1), 1, colors.HexColor('#E2E8F0')),
        ]))
        elements.append(st)
    elements.append(Spacer(1, 15))
    
    # Section 4 - Network Graph
    elements.append(Paragraph("4. Network Graph", styles['SectionHeader']))
    if Path(graph_image_path).exists():
        elements.append(Image(graph_image_path, width=400, height=240))
    else:
        elements.append(Paragraph("Graph image not found.", styles['Normal']))
    elements.append(Spacer(1, 15))
    
    # Section 5 - Seizure Recs
    elements.append(Paragraph("5. Seizure Recommendations", styles['SectionHeader']))
    elements.append(Paragraph("1. Freeze Account X at Bank Y for amount Z.", styles['Normal']))
    elements.append(Spacer(1, 15))
    
    # Section 6 - Appendix
    elements.append(PageBreak())
    elements.append(Paragraph("6. Evidence Appendix", styles['SectionHeader']))
    for ev in data.get("evidence", []):
        elements.append(Paragraph(f"{ev.get('filename')}: {ev.get('sha256')}", styles['Monospace']))
        
    # Certificate
    elements.append(Spacer(1, 30))
    elements.append(Paragraph("CERTIFICATE (Under Sec 63 BSA / 65B IEA)", styles['SectionHeader']))
    cert_text = "This is to certify that the computer output containing the above information was produced by a computer system..."
    elements.append(Paragraph(cert_text, styles['Normal']))
    
    doc.build(elements, canvasmaker=NumberedCanvas)
