import html
from datetime import UTC, datetime
from typing import Any

from app.models.decision import Decision
from app.models.report import Report

PRIORITY_STYLES: dict[str, dict[str, str]] = {
    "high": {
        "background": "#fde8e8",
        "color": "#b42318",
        "border": "#f5c2c7",
    },
    "medium": {
        "background": "#fff4e5",
        "color": "#b54708",
        "border": "#fcd9a8",
    },
    "low": {
        "background": "#e8f5e9",
        "color": "#2e7d32",
        "border": "#a5d6a7",
    },
}

DEFAULT_PRIORITY_STYLE = {
    "background": "#eef2f6",
    "color": "#344054",
    "border": "#d0d5dd",
}


def format_utc_timestamp(value: datetime | None) -> str:
    if value is None:
        value = datetime.now(UTC)
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    else:
        value = value.astimezone(UTC)
    return value.strftime("%Y-%m-%d %H:%M:%S UTC")


def resolve_email_timestamp(decision: Decision, report: Report | None) -> str:
    source = report.created_at if report is not None else decision.created_at
    return format_utc_timestamp(source)


def build_email_header(timestamp_utc: str) -> str:
    return f"""
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
           style="background-color:#1f2937;border-radius:8px 8px 0 0;">
      <tr>
        <td style="padding:24px 28px;font-family:Arial,Helvetica,sans-serif;">
          <div style="font-size:22px;line-height:28px;font-weight:bold;color:#ffffff;">
            Business Automation Agent
          </div>
          <div style="font-size:14px;line-height:20px;color:#d1d5db;margin-top:6px;">
            Automated Business Decision Report
          </div>
          <div style="font-size:12px;line-height:18px;color:#9ca3af;margin-top:12px;">
            {html.escape(timestamp_utc)}
          </div>
        </td>
      </tr>
    </table>"""


def build_priority_badge(priority: str) -> str:
    normalized = (priority or "medium").strip().lower()
    styles = PRIORITY_STYLES.get(normalized, DEFAULT_PRIORITY_STYLE)
    label = html.escape(normalized.upper())

    return f"""
    <span style="display:inline-block;padding:6px 12px;border-radius:999px;
                 font-family:Arial,Helvetica,sans-serif;font-size:12px;
                 font-weight:bold;letter-spacing:0.4px;
                 background-color:{styles['background']};color:{styles['color']};
                 border:1px solid {styles['border']};">
      {label}
    </span>"""


def build_report_button(access_url: str) -> str:
    safe_url = html.escape(access_url, quote=True)
    return f"""
    <table role="presentation" cellpadding="0" cellspacing="0" border="0"
           style="margin:20px 0;">
      <tr>
        <td align="center" bgcolor="#2563eb"
            style="border-radius:6px;background-color:#2563eb;">
          <a href="{safe_url}" target="_blank"
             style="display:inline-block;padding:14px 28px;
                    font-family:Arial,Helvetica,sans-serif;
                    font-size:15px;font-weight:bold;color:#ffffff;text-decoration:none;
                    border-radius:6px;">
            View Report
          </a>
        </td>
      </tr>
    </table>"""


def build_report_status(
    report: Report | None,
    report_access_url: str | None = None,
) -> tuple[str, str]:
    if report is not None and report.s3_url and report_access_url:
        link = build_report_link(report_access_url)
        return "Available", link
    return "Not Available", ""


def build_report_link(access_url: str) -> str:
    safe_url = html.escape(access_url, quote=True)
    return (
        f'<a href="{safe_url}" target="_blank" '
        f'style="color:#2563eb;font-weight:bold;text-decoration:none;">'
        f"Report Available</a>"
    )


def _normalize_recommendations(
    recommendations: list[Any] | dict[str, Any] | None,
) -> list[str]:
    if recommendations is None:
        return []
    if isinstance(recommendations, dict):
        return [str(recommendations)]
    if isinstance(recommendations, list):
        return [str(item) for item in recommendations]
    return [str(recommendations)]


def build_recommendations_section(
    recommendations: list[Any] | dict[str, Any] | None,
) -> str:
    items = _normalize_recommendations(recommendations)
    if not items:
        items = ["No recommendations provided."]

    rows = "".join(
        f"<li style='margin-bottom:8px;'>{html.escape(item)}</li>" for item in items
    )
    return f"""
    <h3 style="margin:24px 0 10px;font-family:Arial,Helvetica,sans-serif;
               font-size:16px;color:#111827;">
      Recommendations
    </h3>
    <ol style="margin:0;padding-left:22px;font-family:Arial,Helvetica,sans-serif;
               font-size:14px;line-height:22px;color:#374151;">
      {rows}
    </ol>"""


def build_details_table(
    decision: Decision,
    report_status: str,
    report_link_html: str,
) -> str:
    badge = build_priority_badge(decision.priority)
    status_text = html.escape(report_status)
    if report_link_html:
        status_text = f"{status_text} — {report_link_html}"

    return f"""
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
           style="border:1px solid #e5e7eb;border-radius:8px;overflow:hidden;">
      <tr>
        <td style="padding:12px 16px;background-color:#f9fafb;width:38%;
                   font-family:Arial,Helvetica,sans-serif;font-size:13px;
                   color:#6b7280;border-bottom:1px solid #e5e7eb;">
          <strong>Event ID</strong>
        </td>
        <td style="padding:12px 16px;
                   font-family:Arial,Helvetica,sans-serif;font-size:13px;
                   color:#111827;border-bottom:1px solid #e5e7eb;word-break:break-all;">
          {html.escape(str(decision.event_id))}
        </td>
      </tr>
      <tr>
        <td style="padding:12px 16px;background-color:#f9fafb;
                   font-family:Arial,Helvetica,sans-serif;
                   font-size:13px;color:#6b7280;border-bottom:1px solid #e5e7eb;">
          <strong>Priority</strong>
        </td>
        <td style="padding:12px 16px;border-bottom:1px solid #e5e7eb;">
          {badge}
        </td>
      </tr>
      <tr>
        <td style="padding:12px 16px;background-color:#f9fafb;
                   font-family:Arial,Helvetica,sans-serif;
                   font-size:13px;color:#6b7280;border-bottom:1px solid #e5e7eb;">
          <strong>Classification</strong>
        </td>
        <td style="padding:12px 16px;
                   font-family:Arial,Helvetica,sans-serif;font-size:13px;
                   color:#111827;border-bottom:1px solid #e5e7eb;">
          {html.escape(decision.classification)}
        </td>
      </tr>
      <tr>
        <td style="padding:12px 16px;background-color:#f9fafb;
                   font-family:Arial,Helvetica,sans-serif;
                   font-size:13px;color:#6b7280;border-bottom:1px solid #e5e7eb;">
          <strong>Rule Triggered</strong>
        </td>
        <td style="padding:12px 16px;
                   font-family:Arial,Helvetica,sans-serif;font-size:13px;
                   color:#111827;border-bottom:1px solid #e5e7eb;">
          {html.escape(decision.rule_triggered or "N/A")}
        </td>
      </tr>
      <tr>
        <td style="padding:12px 16px;background-color:#f9fafb;
                   font-family:Arial,Helvetica,sans-serif;
                   font-size:13px;color:#6b7280;">
          <strong>Report Status</strong>
        </td>
        <td style="padding:12px 16px;
                   font-family:Arial,Helvetica,sans-serif;font-size:13px;
                   color:#111827;">
          {status_text}
        </td>
      </tr>
    </table>"""


def build_decision_email_html(
    decision: Decision,
    report: Report | None = None,
    report_access_url: str | None = None,
) -> str:
    timestamp_utc = resolve_email_timestamp(decision, report)
    report_status, report_link_html = build_report_status(report, report_access_url)
    header = build_email_header(timestamp_utc)
    details = build_details_table(decision, report_status, report_link_html)
    recommendations = build_recommendations_section(decision.recommendations)

    report_button = ""
    if report_access_url:
        report_button = build_report_button(report_access_url)

    return f"""<!DOCTYPE html>
<html>
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Business Automation Agent Alert</title>
  </head>
  <body style="margin:0;padding:0;background-color:#f3f4f6;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
           style="background-color:#f3f4f6;padding:24px 12px;">
      <tr>
        <td align="center">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
                 border="0"
                 style="max-width:600px;width:100%;background-color:#ffffff;
                        border-radius:8px;overflow:hidden;
                        box-shadow:0 1px 3px rgba(0,0,0,0.08);">
            <tr>
              <td>
                {header}
              </td>
            </tr>
            <tr>
              <td style="padding:24px 28px;font-family:Arial,Helvetica,sans-serif;">
                <p style="margin:0 0 18px;font-size:14px;line-height:22px;
                          color:#4b5563;">
                  A new automated business decision requires your attention.
                </p>
                {details}
                <h3 style="margin:24px 0 10px;font-size:16px;color:#111827;">
                  Summary
                </h3>
                <p style="margin:0;font-size:14px;line-height:22px;color:#374151;">
                  {html.escape(decision.summary)}
                </p>
                {report_button}
                {recommendations}
              </td>
            </tr>
            <tr>
              <td style="padding:16px 28px;background-color:#f9fafb;
                         border-top:1px solid #e5e7eb;
                         font-family:Arial,Helvetica,sans-serif;font-size:12px;line-height:18px;
                         color:#6b7280;">
                This message was generated automatically by Business Automation Agent.
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>"""


def build_decision_email_subject(decision: Decision) -> str:
    priority = decision.priority.upper()
    classification = decision.classification
    return f"[{priority}] {classification} — Event {decision.event_id}"
