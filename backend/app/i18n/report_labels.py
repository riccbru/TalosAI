"""Localized labels for the PDF pentest report (``pentest_report.html``).

The Jinja2 template consumes a single ``t`` mapping and reads every fixed label
as ``t.<key>``. This module is the source of truth for those keys: one block per
language (``en``, ``it``, ``fr``), each defining the *exact* set of keys the
template references. Resolve a language with :func:`get_labels`, then pass the
result to the template as ``t``::

    from app.i18n import get_labels
    html = template.render(t=get_labels(lang), mission_id=..., ...)

Mission statuses are localized separately via :func:`get_status_label`, since
their values come from the DB (``completed``, ``interrupted``, ...), not the
template.
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
        "operator": "Launched by",
        "engine": "Engine",
        "status": "Status",
        "started": "Started",
        "finished": "Finished",
        "duration": "Duration",
        "generated": "Generated on",
        "date": "Date",
        "not_available": "N/A",
        # --- findings section ---
        "findings_title": "Confirmed Findings",
        "findings_summary": "confirmed vulnerabilities identified.",
        "not_hacked_title": "Services Not Compromised",
        "not_hacked_none": "Every discovered service was compromised.",
        "col_service": "Service",
        "col_version": "Version",
        "col_port": "Port",
        "col_command": "Validated Command",
        "col_output": "Output / Evidence",
        "analysis": "Analysis",
        "col_status": "Status",
        "confirmed": "Confirmed",
        "unconfirmed": "Unconfirmed",
        "no_command": "—",
        "no_output": "No output captured.",
        "no_findings": "No confirmed vulnerabilities were found.",
        # --- FinOps / resource usage ---
        "finops_title": "Resource Usage (FinOps)",
        "col_agent": "Agent",
        "col_model": "Model",
        "col_provider": "Provider",
        "col_prompt_tokens": "Prompt",
        "col_completion_tokens": "Completion",
        "col_total_tokens": "Tokens",
        "col_calls": "Calls",
        "col_latency": "Latency (s)",
        "total_row": "Total",
        "finops_none": "No model usage recorded.",
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
        "operator": "Avviato da",
        "engine": "Motore",
        "status": "Stato",
        "started": "Inizio",
        "finished": "Fine",
        "duration": "Durata",
        "generated": "Generato il",
        "date": "Data",
        "not_available": "N/D",
        # --- findings section ---
        "findings_title": "Vulnerabilità Confermate",
        "findings_summary": "vulnerabilità confermate identificate.",
        "not_hacked_title": "Servizi Non Compromessi",
        "not_hacked_none": "Tutti i servizi rilevati sono stati compromessi.",
        "col_service": "Servizio",
        "col_version": "Versione",
        "col_port": "Porta",
        "col_command": "Comando Validato",
        "col_output": "Output / Evidenza",
        "analysis": "Analisi",
        "col_status": "Stato",
        "confirmed": "Confermato",
        "unconfirmed": "Non confermato",
        "no_command": "—",
        "no_output": "Nessun output catturato.",
        "no_findings": "Nessuna vulnerabilità confermata rilevata.",
        # --- FinOps / resource usage ---
        "finops_title": "Consumo Risorse (FinOps)",
        "col_agent": "Agente",
        "col_model": "Modello",
        "col_provider": "Provider",
        "col_prompt_tokens": "Prompt",
        "col_completion_tokens": "Completion",
        "col_total_tokens": "Token",
        "col_calls": "Chiamate",
        "col_latency": "Latenza (s)",
        "total_row": "Totale",
        "finops_none": "Nessun consumo registrato.",
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
        "operator": "Lancé par",
        "engine": "Moteur",
        "status": "Statut",
        "started": "Début",
        "finished": "Fin",
        "duration": "Durée",
        "generated": "Généré le",
        "date": "Date",
        "not_available": "N/D",
        # --- findings section ---
        "findings_title": "Vulnérabilités Confirmées",
        "findings_summary": "vulnérabilités confirmées identifiées.",
        "not_hacked_title": "Services Non Compromis",
        "not_hacked_none": "Tous les services détectés ont été compromis.",
        "col_service": "Service",
        "col_version": "Version",
        "col_port": "Port",
        "col_command": "Commande Validée",
        "col_output": "Sortie / Preuve",
        "analysis": "Analyse",
        "col_status": "Statut",
        "confirmed": "Confirmé",
        "unconfirmed": "Non confirmé",
        "no_command": "—",
        "no_output": "Aucune sortie capturée.",
        "no_findings": "Aucune vulnérabilité confirmée n'a été détectée.",
        # --- FinOps / resource usage ---
        "finops_title": "Consommation de Ressources (FinOps)",
        "col_agent": "Agent",
        "col_model": "Modèle",
        "col_provider": "Fournisseur",
        "col_prompt_tokens": "Prompt",
        "col_completion_tokens": "Completion",
        "col_total_tokens": "Jetons",
        "col_calls": "Appels",
        "col_latency": "Latence (s)",
        "total_row": "Total",
        "finops_none": "Aucune consommation enregistrée.",
    },
}

# Mission status values (as stored in the DB) -> localized display text.
STATUS_LABELS: Dict[str, Dict[str, str]] = {
    "en": {
        "pending": "Pending",
        "running": "Running",
        "completed": "Completed",
        "interrupted": "Interrupted",
        "failed": "Failed",
        "cancelled": "Cancelled",
    },
    "it": {
        "pending": "In attesa",
        "running": "In corso",
        "completed": "Completato",
        "interrupted": "Interrotto",
        "failed": "Fallito",
        "cancelled": "Annullato",
    },
    "fr": {
        "pending": "En attente",
        "running": "En cours",
        "completed": "Terminé",
        "interrupted": "Interrompu",
        "failed": "Échoué",
        "cancelled": "Annulé",
    },
}

SUPPORTED_LANGS = tuple(TRANSLATIONS.keys())


def _norm(lang: str | None) -> str:
    """Normalize a language tag to a supported code, falling back to default."""
    if lang:
        code = lang.strip().lower().replace("_", "-").split("-", 1)[0]
        if code in TRANSLATIONS:
            return code
    return DEFAULT_LANG


def get_labels(lang: str | None) -> Dict[str, str]:
    """Return the label map for ``lang``, falling back to :data:`DEFAULT_LANG`.

    Resolution is case-insensitive and tolerant of region tags ("en-US" -> "en").
    The returned dict is a fresh copy layered over the default language, so an
    unknown language (or a translation missing a key) still yields every key the
    template needs instead of raising ``UndefinedError`` at render time.
    """
    base = dict(TRANSLATIONS[DEFAULT_LANG])
    base.update(TRANSLATIONS[_norm(lang)])
    return base


def get_status_label(status: str | None, lang: str | None) -> str:
    """Localize a mission status; unknown values pass through capitalized."""
    if not status:
        return TRANSLATIONS[_norm(lang)]["not_available"]
    return STATUS_LABELS[_norm(lang)].get(status.lower(), status.capitalize())
