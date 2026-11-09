"""PDF report generation for a mission.

Renders the Jinja2 template ``templates/pentest_report.html`` with the labels of
the requested language (see :mod:`app.i18n`) and compiles it to a PDF with
WeasyPrint. Only *confirmed* findings (validated commands) are reported.

WeasyPrint is imported lazily inside :func:`render_report_pdf` so that a missing
native dependency (pango/cairo/gdk-pixbuf) degrades to a clear error on the
report endpoint only, instead of crashing application import at startup.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.i18n import get_labels, get_status_label

if TYPE_CHECKING:  # type-only; findings/mission are duck-typed at runtime
    from app.models.missions import Finding, Mission

# backend/app/services/report_service.py -> parents[2] == backend/
TEMPLATES_DIR = Path(__file__).resolve().parents[2] / "templates"
REPORT_TEMPLATE = "pentest_report.html"

# Captured command output can be long; the orchestrator already tail-truncates,
# but cap again defensively so one noisy finding can't bloat the PDF.
_MAX_OUTPUT_CHARS = 2000
# Manager reasoning is prose; keep it short so the report stays readable.
_MAX_REASONING_CHARS = 600

# orchestrator_version (DB) -> human-friendly engine name shown in the report.
_ENGINE_NAMES = {
    "v1": "Hybrid v1",
    "v2": "Hybrid v2",
    "local": "Local (offline)",
}

# A finding whose command is just an exploit *search* (msfconsole `search`, or
# `searchsploit`) is reconnaissance, not an actual compromise — it must not count
# as a hacked service. Real exploitation uses `use <module>; run; sessions ...`.
_SEARCH_RE = re.compile(r"\bsearch(?:sploit)?\b", re.IGNORECASE)


def _is_real_exploit(command: Optional[str]) -> bool:
    """True only for an actual exploitation command (not a search/recon one)."""
    if not command or not command.strip():
        return False
    return _SEARCH_RE.search(command) is None

# autoescape=True: finding commands/output are attacker-influenced strings
# rendered into HTML, so they must be escaped to avoid markup injection.
_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
)


def _fmt_dt(dt: Optional[datetime]) -> Optional[str]:
    """Format a timezone-aware datetime as 'YYYY-MM-DD HH:MM:SS UTC' (or None)."""
    if not isinstance(dt, datetime):
        return None
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _fmt_duration(start: Optional[datetime], end: Optional[datetime]) -> Optional[str]:
    """Human HH:MM:SS between two datetimes, or None if either is missing."""
    if not isinstance(start, datetime) or not isinstance(end, datetime):
        return None
    secs = int((end - start).total_seconds())
    if secs < 0:
        return None
    h, rem = divmod(secs, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def _target_display(mission: Mission) -> str:
    """'metasploitable (172.20.0.4)' when an IP is known, else just the target."""
    target = mission.target or "—"
    ip = getattr(mission, "target_ip", None)
    if ip and ip != target:
        return f"{target} ({ip})"
    return target


def _clip_output(text: Optional[str]) -> Optional[str]:
    """Keep the tail of long output (where proof lands), marking truncation."""
    if not text:
        return None
    if len(text) > _MAX_OUTPUT_CHARS:
        return "[…]\n" + text[-_MAX_OUTPUT_CHARS:]
    return text


def _clip_reasoning(text: Optional[str]) -> Optional[str]:
    """Trim the head of long manager reasoning, marking truncation."""
    if not text:
        return None
    text = text.strip()
    if len(text) > _MAX_REASONING_CHARS:
        return text[:_MAX_REASONING_CHARS].rstrip() + " […]"
    return text


def _clean(value: Optional[str], fallback: str = "—") -> str:
    """Normalize an nmap-ish field; 'unknown'/empty -> fallback."""
    if not value or str(value).strip().lower() in ("unknown", "tcpwrapped", ""):
        return fallback
    return str(value)


def _port_map(ports: Optional[List[dict]]) -> dict:
    """{port_number: serialized_port} for version/service lookups."""
    return {p.get("port"): p for p in (ports or []) if p.get("port") is not None}


def _shape_findings(findings: List[Finding], pmap: dict) -> List[dict]:
    """Keep only real exploitation findings and enrich each with the service
    version discovered on its port. Search/recon commands are dropped."""
    shaped = []
    for f in findings:
        if not _is_real_exploit(getattr(f, "command", None)):
            continue
        port_info = pmap.get(f.port, {})
        shaped.append({
            "service": f.service_name or port_info.get("service_name") or "—",
            "version": _clean(port_info.get("version")),
            "port": f.port,
            "command": f.command,
            "output": _clip_output(f.output),
            "reasoning": _clip_reasoning(getattr(f, "reasoning", None)),
            "confirmed": f.confirmed,
        })
    return shaped


def _not_hacked(ports: Optional[List[dict]], hacked_ports: set) -> List[dict]:
    """Discovered services whose port was NOT successfully exploited."""
    rows = []
    for p in ports or []:
        if p.get("port") in hacked_ports:
            continue
        rows.append({
            "port": p.get("port"),
            "service": _clean(p.get("service_name")),
            "version": _clean(p.get("version")),
        })
    return rows


def build_report_html(
    mission: Mission,
    findings: List[Finding],
    lang: str,
    operator_email: Optional[str] = None,
    usage_table: Optional[dict] = None,
    ports: Optional[List[dict]] = None,
) -> str:
    """Render the report template to an HTML string."""
    template = _env.get_template(REPORT_TEMPLATE)
    engine = _ENGINE_NAMES.get(
        getattr(mission, "orchestrator_version", None) or "",
        getattr(mission, "orchestrator_version", None) or "—",
    )
    labels = get_labels(lang)
    pmap = _port_map(ports)
    shaped_findings = _shape_findings(findings, pmap)
    hacked_ports = {f["port"] for f in shaped_findings}
    return template.render(
        lang=lang,
        t=labels,
        mission_id=str(mission.uuid),
        target=_target_display(mission),
        operator=operator_email or labels["not_available"],
        engine=engine,
        status=get_status_label(getattr(mission, "status", None), lang),
        started=_fmt_dt(getattr(mission, "started_at", None)) or labels["not_available"],
        finished=_fmt_dt(getattr(mission, "finished_at", None)) or labels["not_available"],
        duration=_fmt_duration(
            getattr(mission, "started_at", None), getattr(mission, "finished_at", None)
        ) or labels["not_available"],
        generated=_fmt_dt(datetime.now(timezone.utc)),
        findings=shaped_findings,
        not_hacked=_not_hacked(ports, hacked_ports),
        finops=usage_table or {"rows": [], "total": {}},
    )


def render_report_pdf(
    mission: Mission,
    findings: List[Finding],
    lang: str,
    operator_email: Optional[str] = None,
    usage_table: Optional[dict] = None,
    ports: Optional[List[dict]] = None,
) -> bytes:
    """Render the localized report and compile it to PDF bytes.

    ``base_url`` is set to the templates directory so the relative asset paths in
    the template (e.g. ``assets/logo.png``, ``assets/talos_logo.png``) resolve.
    """
    import weasyprint  # lazy: see module docstring

    html_content = build_report_html(
        mission, findings, lang, operator_email, usage_table, ports
    )
    return weasyprint.HTML(
        string=html_content,
        base_url=str(TEMPLATES_DIR),
    ).write_pdf()
