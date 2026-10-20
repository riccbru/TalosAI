import json
import time
from typing import List, Optional

from crewai import Crew, Process, Task
from google import genai

# Read-only reuse of V2's default sink. Importing it does NOT modify V2.
from app.agents.hybrid_orchestrator_v2 import NoOpReporter
from app.agents.mission_exceptions import MissionCancelled
from app.agents.tester import get_tester_agent
from app.agents.usage import extract_usage
from app.core import errors
from app.core.config import settings


gemini_client = genai.Client()

_GEMINI_PROVIDER = "gemini"


class HybridOrchestratorV1:
    """Legacy hybrid pipeline (Planner -> CrewAI executor -> Critic), adapted to
    emit through the same reporter sink as V2.

    This makes a V1 run persist as a mission and expose the *identical*
    ``{mission, ports, findings, models, metrics}`` envelope as V2, so results
    can be compared side by side. V1 is architecturally different, though: it
    does not run per-port exploits, so each finding carries the Critic's analysis
    (no executed per-finding ``command``/``output``) and the ports roster is
    derived from the findings themselves. V2 is never touched by this class.
    """

    def __init__(
        self,
        target: str,
        user_prompt: Optional[str] = None,
        reporter=None,
        should_cancel=None,
        **_ignored,  # tolerate extra kwargs (e.g. initial_services) harmlessly
    ):
        self.target = target
        self.local_executor = get_tester_agent()
        self.user_prompt = (
            user_prompt or "Perform a standard comprehensive security analysis."
        )
        self.reporter = reporter or NoOpReporter()
        self._should_cancel = should_cancel or (lambda: False)

    def _check_cancel(self) -> None:
        if self._should_cancel():
            raise MissionCancelled()

    def _emit_log(self, step: str, message: str, status: str = "running") -> None:
        self.reporter.log(step, message, status)

    # --- usage tracking (same accounting as V2, per logical agent) ---

    def _record_gemini_usage(self, agent: str, resp, latency: float) -> None:
        prompt_tokens, completion_tokens, total_tokens = extract_usage(
            resp, _GEMINI_PROVIDER
        )
        self.reporter.record_usage(
            agent=agent,
            model=settings.GEMINI_MODEL,
            provider=_GEMINI_PROVIDER,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            latency_seconds=latency,
        )

    def _record_crew_usage(self, agent: str, crew, result, latency: float) -> None:
        """CrewAI exposes aggregate token usage after kickoff; attribute it to the
        Ollama-backed executor. Field names vary across versions, so read
        defensively and skip silently if unavailable (never break the mission)."""
        usage = getattr(crew, "usage_metrics", None) or getattr(
            result, "token_usage", None
        )
        if usage is None:
            return
        prompt_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
        completion_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
        total_tokens = int(
            getattr(usage, "total_tokens", 0) or (prompt_tokens + completion_tokens)
        )
        self.reporter.record_usage(
            agent=agent,
            model=settings.MODEL_ASSIGNMENT["tester"].model,
            provider="ollama",
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            latency_seconds=latency,
        )

    # --- findings normalization (Critic JSON is free-form) ---

    @staticmethod
    def _normalize_findings(validated) -> List[dict]:
        items: list = []
        if isinstance(validated, list):
            items = validated
        elif isinstance(validated, dict):
            for key in ("findings", "results", "vulnerabilities", "confirmed_findings"):
                if isinstance(validated.get(key), list):
                    items = validated[key]
                    break
            else:
                items = [validated]

        findings = []
        for it in items:
            if not isinstance(it, dict):
                continue
            findings.append(
                {
                    "port": it.get("port"),
                    "service_name": it.get("service") or it.get("service_name"),
                    "action": "ANALYSIS",
                    "command": None,  # V1 has no executed per-finding command
                    "output": (
                        it.get("evidence")
                        or it.get("raw_output")
                        or json.dumps(it, ensure_ascii=False)
                    ),
                    "reasoning": (
                        it.get("vulnerability")
                        or it.get("description")
                        or it.get("reason")
                    ),
                    "confirmed": bool(it.get("confirmed", False)),
                }
            )
        return findings

    @staticmethod
    def _ports_from_findings(findings: List[dict]) -> List[dict]:
        seen: dict = {}
        for f in findings:
            port = f.get("port")
            if port is None or port in seen:
                continue
            seen[port] = {
                "port": port,
                "service_name": f.get("service_name"),
                "version": None,
                "status": "completed",
                "attempts": 0,
                "history": [],
            }
        return list(seen.values())

    def _create_tasks(self, strategy_text: str):
        scan_task = Task(
            agent=self.local_executor,
            description=(
                f"Based on this strategy:\n{strategy_text}\n"
                f"Execute the initial service discovery on {self.target} using nmap."
            ),
            expected_output="Raw terminal output from the executed commands.",
        )
        return [scan_task]

    def run(self) -> dict:
        self._check_cancel()
        self._emit_log("Planner", f"Cyber planning: {self.target}")
        planning_prompt = (
            f"You are the master planner for a penetration test against: {self.target}.\n"  # noqa: E501
            f"User Directive: {self.user_prompt}\n"
            "Generate a clear, bulleted execution strategy for a local tool executor."  # noqa: E501
        )
        started = time.monotonic()
        response_planner = gemini_client.models.generate_content(
            contents=planning_prompt,
            model=settings.GEMINI_MODEL,
        )
        self._record_gemini_usage("planner", response_planner, time.monotonic() - started)
        if response_planner is None or not getattr(response_planner, "text", None):
            raise RuntimeError(
                "Gemini planner returned an empty response (likely free-tier quota)."
            )
        strategy = response_planner.text
        self._emit_log("Planner", "Cyber planning created", "completed")

        self._check_cancel()
        self._emit_log("Executor", "Initializing local CrewAI for executing tasks...")
        crew = Crew(
            tasks=self._create_tasks(strategy),
            verbose=True,
            process=Process.sequential,
            agents=[self.local_executor],
        )
        started = time.monotonic()
        raw_execution = crew.kickoff()
        self._record_crew_usage("tester", crew, raw_execution, time.monotonic() - started)
        raw_logs_text = (
            raw_execution.raw if hasattr(raw_execution, "raw") else str(raw_execution)
        )
        self._emit_log("Executor", "CrewAI completed commands execution.", "completed")

        self._check_cancel()
        self._emit_log(
            "Critic", "Send raw logs to Gemini for anti-hallucinations audit..."
        )
        prompt_audit = (
            f"Analyze these raw terminal execution logs for the target {self.target}:\n"  # noqa: E501
            f"{raw_logs_text}\n\n"
            "Extract confirmed findings. For each finding specify: port, service, and vulnerability."  # noqa: E501
        )
        started = time.monotonic()
        response_critic = gemini_client.models.generate_content(
            contents=prompt_audit,
            model=settings.GEMINI_MODEL,
            config=genai.types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )
        self._record_gemini_usage("critic", response_critic, time.monotonic() - started)
        if response_critic is None or not getattr(response_critic, "text", None):
            raise RuntimeError("Gemini critic returned an empty response.")
        try:
            validated_json = json.loads(response_critic.text)
        except (json.JSONDecodeError, TypeError) as e:
            errors.log_detail("HybridOrchestratorV1 critic returned non-JSON", e)
            validated_json = []

        findings = self._normalize_findings(validated_json)
        ports = self._ports_from_findings(findings)
        if ports:
            self.reporter.services_discovered(ports)
        for finding in findings:
            self.reporter.finding(finding)
        self._emit_log("Critic", "Audit completed successfully", "success")

        return {"status": "completed", "target": self.target, "findings": len(findings)}
