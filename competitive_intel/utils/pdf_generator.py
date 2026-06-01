# Generates a downloadable PDF of the intelligence brief


from datetime import datetime
import re
from io import BytesIO


def clean_text(text: str) -> str:
    import unicodedata
    text = re.sub(r'#{1,6}\s', '', text)
    text = re.sub(r'\*{1,3}(.*?)\*{1,3}', r'\1', text)
    
    # Keep currency symbols instead of stripping all non-ASCII
    cleaned_chars = []
    for char in text:
        if ord(char) < 128:                              # standard ASCII
            cleaned_chars.append(char)
        elif unicodedata.category(char) == 'Sc':         # currency symbols $£€¥₹
            cleaned_chars.append(char)
        else:
            cleaned_chars.append('')                     # drop other non-ASCII
    text = ''.join(cleaned_chars)
    
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def generate_pdf(brief_text: str, competitors: list, focus_area: str) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.colors import HexColor
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
    from reportlab.lib.units import mm

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=20*mm,
        rightMargin=20*mm,
        topMargin=20*mm,
        bottomMargin=20*mm,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontSize=18,
        textColor=HexColor('#6366f1'),
        spaceAfter=4,
        alignment=1,
    )
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=9,
        textColor=HexColor('#888888'),
        spaceAfter=2,
        alignment=1,
    )
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Normal'],
        fontSize=11,
        textColor=HexColor('#6366f1'),
        fontName='Helvetica-Bold',
        spaceBefore=6,
        spaceAfter=3,
    )
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontSize=9,
        textColor=HexColor('#1e1e1e'),
        spaceAfter=3,
        leading=14,
    )

    story = []

    # Header
    story.append(Paragraph("Competitive Intelligence Brief", title_style))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y')}", subtitle_style))
    story.append(Paragraph(f"Tracking: {', '.join(competitors)}", subtitle_style))
    story.append(Paragraph(f"Focus: {focus_area}", subtitle_style))
    story.append(Spacer(1, 4*mm))
    story.append(HRFlowable(width="100%", thickness=1, color=HexColor('#6366f1')))
    story.append(Spacer(1, 4*mm))

    # Body
    cleaned = clean_text(brief_text)
    for line in cleaned.split('\n'):
        line = line.strip()
        if not line:
            story.append(Spacer(1, 2*mm))
            continue
        if line.endswith(':') or (line.isupper() and 3 < len(line) < 60):
            story.append(Paragraph(line, heading_style))
        else:
            story.append(Paragraph(line, body_style))

    doc.build(story)
    return buffer.getvalue()