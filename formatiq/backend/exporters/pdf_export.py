"""
PDF report generation per format point using reportlab.
"""
import io
import logging
from sqlalchemy.orm import Session

from database import Video, FormatPoint

logger = logging.getLogger(__name__)

try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        HRFlowable, KeepTogether
    )
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    logger.warning("reportlab not installed. PDF export will return placeholder.")


def generate_format_point_pdf(db: Session, format_point_id: int) -> bytes:
    if not REPORTLAB_AVAILABLE:
        return b"PDF export requires reportlab. Install with: pip install reportlab"

    fp = db.query(FormatPoint).filter_by(id=format_point_id).first()
    if not fp:
        return b"Format point not found"

    top_videos = (
        db.query(Video)
        .filter(Video.format_point_id == format_point_id, Video.analysis_status == "done")
        .order_by(Video.view_count.desc())
        .limit(10)
        .all()
    )

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.8*inch, bottomMargin=0.8*inch)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "FormatIQTitle",
        parent=styles["Title"],
        fontSize=24,
        textColor=colors.HexColor("#6366f1"),
        spaceAfter=6,
    )
    heading_style = ParagraphStyle(
        "FormatIQHeading",
        parent=styles["Heading2"],
        fontSize=14,
        textColor=colors.HexColor("#1e293b"),
        spaceBefore=16,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "FormatIQBody",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#334155"),
    )
    small_style = ParagraphStyle(
        "FormatIQSmall",
        parent=styles["Normal"],
        fontSize=8,
        textColor=colors.HexColor("#64748b"),
    )

    story = []

    # Header
    story.append(Paragraph("FormatIQ", title_style))
    story.append(Paragraph(f"Format Point #{fp.number}: {fp.name}", styles["Heading1"]))
    story.append(Paragraph(fp.description or "", body_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e2e8f0")))
    story.append(Spacer(1, 12))

    # Stats summary
    total = db.query(Video).filter_by(format_point_id=format_point_id).count()
    done = db.query(Video).filter_by(format_point_id=format_point_id, analysis_status="done").count()
    story.append(Paragraph(f"Videos collected: {total} | Analyzed: {done}", small_style))
    story.append(Spacer(1, 12))

    # Top 10 Videos
    story.append(Paragraph("Top 10 Performing Videos", heading_style))

    if top_videos:
        table_data = [["#", "Title", "Channel", "Views", "Concept"]]
        for i, v in enumerate(top_videos, 1):
            concept = ""
            if v.analysis and v.analysis.concept_summary:
                concept = v.analysis.concept_summary[:100] + "..." if len(v.analysis.concept_summary) > 100 else v.analysis.concept_summary
            table_data.append([
                str(i),
                Paragraph(v.title or "", small_style),
                Paragraph(v.channel_name or "", small_style),
                f"{v.view_count:,}",
                Paragraph(concept, small_style),
            ])

        table = Table(table_data, colWidths=[0.3*inch, 2.2*inch, 1.3*inch, 0.8*inch, 2.4*inch])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#6366f1")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("FONTSIZE", (0, 1), (-1, -1), 8),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(table)
    else:
        story.append(Paragraph("No analyzed videos yet for this format point.", body_style))

    story.append(Spacer(1, 16))

    # Best script excerpts
    story.append(Paragraph("Best Script Excerpts", heading_style))
    excerpts_found = False
    for v in top_videos[:5]:
        if v.analysis and v.analysis.best_moments:
            story.append(Paragraph(f"From: {v.title}", ParagraphStyle("bold", parent=body_style, fontName="Helvetica-Bold")))
            for moment in (v.analysis.best_moments or [])[:2]:
                ts = moment.get("timestamp", "")
                excerpt = moment.get("excerpt", "")
                note = moment.get("note", "")
                story.append(Paragraph(f"[{ts}] \"{excerpt}\"", body_style))
                if note:
                    story.append(Paragraph(f"  → {note}", small_style))
            story.append(Spacer(1, 6))
            excerpts_found = True

    if not excerpts_found:
        story.append(Paragraph("No script excerpts available yet.", body_style))

    # Footer
    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e2e8f0")))
    story.append(Paragraph("Generated by FormatIQ — YouTube Research & Strategy System", small_style))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
