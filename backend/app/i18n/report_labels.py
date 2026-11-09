"""Localized labels for the PDF pentest report (``pentest_report.html``).

The Jinja2 template consumes a single ``t`` mapping and reads every fixed label
as ``t.<key>``. This module is the source of truth for those keys: one block per
language (``en``, ``it``, ``fr``), each defining the *exact* set of keys the
template references. Resolve a language with :func:`get_labels`, then pass the
result to the template as ``t``::

    from app.i18n import get_labels
    html = template.render(t=get_labels(lang), mission_id=..., ...)

Keep the key set in sync with the template. The template currently uses:
report_title, report_subtitle, confidential, page, mission_id, target, date,
findings_title, col_service, col_port, col_command, col_status, confirmed,
unconfirmed, no_command, no_findings.
"""

from typing import Dict

# Corporate baseline (MVE / Monaco) is French; use it as the fallback language.
DEFAULT_LANG = "fr"

TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "en": {
        # --- document chrome ---
        "report_title": "Penetration Test Report",
        "report_subtitle": "Automated Security Assessment",
        "confidential": "Confidential — MVE Services & Technologies",
        "page": "Page",
        # --- mission metadata labels ---
        "mission_id": "Mission ID",
        "target": "Target",
        "date": "Date",
        # --- findings section ---
        "findings_title": "Confirmed Findings",
        "col_service": "Service",
        "col_port": "Port",
        "col_command": "Validated Command",
        "col_status": "Status",
        "confirmed": "Confirmed",
        "unconfirmed": "Unconfirmed",
        "no_command": "—",
        "no_findings": "No confirmed vulnerabilities were found.",
    },
    "it": {
        # --- document chrome ---
        "report_title": "Rapporto di Penetration Test",
        "report_subtitle": "Valutazione di Sicurezza Automatizzata",
        "confidential": "Riservato — MVE Services & Technologies",
        "page": "Pagina",
        # --- mission metadata labels ---
        "mission_id": "ID Missione",
        "target": "Target",
        "date": "Data",
        # --- findings section ---
        "findings_title": "Vulnerabilità Confermate",
        "col_service": "Servizio",
        "col_port": "Porta",
        "col_command": "Comando Validato",
        "col_status": "Stato",
        "confirmed": "Confermato",
        "unconfirmed": "Non confermato",
        "no_command": "—",
        "no_findings": "Nessuna vulnerabilità confermata rilevata.",
    },
    "fr": {
        # --- document chrome ---
        "report_title": "Rapport d'Audit — Test d'Intrusion",
        "report_subtitle": "Évaluation de Sécurité Automatisée",
        "confidential": "Confidentiel — MVE Services & Technologies",
        "page": "Page",
        # --- mission metadata labels ---
        "mission_id": "ID de mission",
        "target": "Cible",
        "date": "Date",
        # --- findings section ---
        "findings_title": "Vulnérabilités Confirmées",
        "col_service": "Service",
        "col_port": "Port",
        "col_command": "Commande Validée",
        "col_status": "Statut",
        "confirmed": "Confirmé",
        "unconfirmed": "Non confirmé",
        "no_command": "—",
        "no_findings": "Aucune vulnérabilité confirmée n'a été détectée.",
    },
}

SUPPORTED_LANGS = tuple(TRANSLATIONS.keys())


def get_labels(lang: str | None) -> Dict[str, str]:
    """Return the label map for ``lang``, falling back to :data:`DEFAULT_LANG`.

    Resolution is case-insensitive and tolerant of region tags ("en-US" -> "en").
    The returned dict is a fresh copy layered over the default language, so an
    unknown language (or a translation missing a key) still yields every key the
    template needs instead of raising ``UndefinedError`` at render time.
    """
    base = dict(TRANSLATIONS[DEFAULT_LANG])
    if lang:
        code = lang.strip().lower().replace("_", "-").split("-", 1)[0]
        base.update(TRANSLATIONS.get(code, {}))
    return base
