"""PDF report generation for a mission.

Renders the Jinja2 template ``templates/pentest_report.html`` with the labels of
the requested language (see :mod:`app.i18n`) and compiles it to a PDF with
WeasyPrint. Only *confirmed* findings (validated commands) are reported.

WeasyPrint is imported lazily inside :func:`render_report_pdf` so that a missing
native dependency (pango/cairo/gdk-pixbuf) degrades to a clear error on the
report endpoint only, instead of crashing application import at startup.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, List

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.i18n import get_labels

if TYPE_CHECKING:  # type-only; findings/mission are duck-typed at runtime
    from app.models.missions import Finding, Mission

# backend/app/services/report_service.py -> parents[2] == backend/
TEMPLATES_DIR = Path(__file__).resolve().parents[2] / "templates"
REPORT_TEMPLATE = "pentest_report.html"

# autoescape=True: finding commands are attacker-influenced strings rendered into
# HTML, so they must be escaped to avoid breaking the layout / markup injection.
_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
)


def _report_date(mission: Mission) -> str:
    """Human date for the report header: the mission's finish time if available,
    else its creation time, else today. Formatted YYYY-MM-DD."""
    dt = getattr(mission, "finished_at", None) or getattr(mission, "created_at", None)
    if isinstance(dt, datetime):
        return dt.strftime("%Y-%m-%d")
    return datetime.utcnow().strftime("%Y-%m-%d")


def _shape_findings(findings: List[Finding]) -> List[dict]:
    """Map ORM findings to the keys the template reads (service/port/command)."""
    return [
        {
            "service": f.service_name,
            "port": f.port,
            "command": f.command,
            "confirmed": f.confirmed,
        }
        for f in findings
    ]


def build_report_html(mission: Mission, findings: List[Finding], lang: str) -> str:
    """Render the report template to an HTML string."""
    template = _env.get_template(REPORT_TEMPLATE)
    return template.render(
        lang=lang,
        t=get_labels(lang),
        mission_id=str(mission.uuid),
        target=mission.target,
        date=_report_date(mission),
        findings=_shape_findings(findings),
    )


def render_report_pdf(mission: Mission, findings: List[Finding], lang: str) -> bytes:
    """Render the localized report and compile it to PDF bytes.

    ``base_url`` is set to the templates directory so the relative asset paths in
    the template (e.g. ``assets/logo.png``, ``assets/talos_logo.png``) resolve.
    """
    import weasyprint  # lazy: see module docstring

    html_content = build_report_html(mission, findings, lang)
    return weasyprint.HTML(
        string=html_content,
        base_url=str(TEMPLATES_DIR),
    ).write_pdf()
