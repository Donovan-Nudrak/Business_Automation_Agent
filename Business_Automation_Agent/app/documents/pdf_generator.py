from io import BytesIO

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from app.documents.report_generator import build_report_payload
from app.models.decision import Decision


def generate_pdf(decision: Decision) -> bytes:
    payload = build_report_payload(decision)
    recommendations = payload.get("recommendations") or []
    if isinstance(recommendations, list):
        recommendations_text = "<br/>".join(
            f"• {str(item)}" for item in recommendations
        ) or "No recommendations provided."
    else:
        recommendations_text = str(recommendations)

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )

    styles = getSampleStyleSheet()
    title_style = styles["Title"]
    heading_style = styles["Heading2"]
    body_style = ParagraphStyle(
        "ReportBody",
        parent=styles["Normal"],
        leading=14,
        spaceAfter=8,
    )

    story = [
        Paragraph("Business Automation Report", title_style),
        Spacer(1, 0.25 * inch),
        Paragraph("Event ID", heading_style),
        Paragraph(str(payload["event_id"]), body_style),
        Paragraph("Priority", heading_style),
        Paragraph(str(payload["priority"]), body_style),
        Paragraph("Classification", heading_style),
        Paragraph(str(payload["classification"]), body_style),
        Paragraph("Summary", heading_style),
        Paragraph(str(payload["summary"]), body_style),
        Paragraph("Recommendations", heading_style),
        Paragraph(recommendations_text, body_style),
        Paragraph("Rule Triggered", heading_style),
        Paragraph(str(payload.get("rule_triggered") or "N/A"), body_style),
        Paragraph("Created At", heading_style),
        Paragraph(str(payload["created_at"]), body_style),
    ]

    doc.build(story)
    return buffer.getvalue()
