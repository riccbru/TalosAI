import json
import time
from typing import List, Optional

from crewai import Crew, Process, Task

from app.agents.critic import get_critic_agent
# Read-only reuse of V2's default sink. Importing it does NOT modify V2.
from app.agents.hybrid_orchestrator_v2 import NoOpReporter
from app.agents.mission_exceptions import MissionCancelled
from app.agents.planner import get_planner_agent
from app.agents.reporter import get_reporter_agent
from app.agents.scanner import get_scanner_agent
from app.agents.summarizer import get_summarizer_agent
from app.agents.tester import get_tester_agent
from app.agents.usage import extract_usage  # noqa: F401 (kept for symmetry/future use)
from app.core import errors
from app.core.config import settings  # noqa: F401 (kept for symmetry/future use)
from app.core.status import _utc_now


class LocalOrchestrator:
    """Air-gapped CrewAI pipeline (Planner -> Scanner -> Tester -> Summarizer ->
    Critic -> Reporter), adapted to emit through the same reporter sink as V1/V2.

    It persists as a mission and exposes the identical
    ``{mission, ports, findings, models, metrics}`` envelope, so all three
    orchestrators are directly comparable. The LLM `reporter` AGENT stays on
    ``self.reporter``; the result/telemetry sink is ``self._sink`` to avoid any
    name clash. V2 is never touched by this class.
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
        self.planner = get_planner_agent()
        self.scanner = get_scanner_agent()
        self.tester = get_tester_agent()
        self.summarizer = get_summarizer_agent()
        self.critic = get_critic_agent()
        self.reporter = get_reporter_agent()  # CrewAI reporter agent (unchanged)
        self.user_prompt = (
            user_prompt or "Perform a standard comprehensive security analysis."
        )
        self._sink = reporter or NoOpReporter()  # result/telemetry sink (DBReporter)
        self._should_cancel = should_cancel or (lambda: False)

    def _check_cancel(self) -> None:
        if self._should_cancel():
            raise MissionCancelled()

    def _emit_log(self, step: str, message: str, status: str = "running") -> None:
        self._sink.log(step, message, status)

    def _record_crew_usage(self, agent: str, crew, result, latency: float) -> None:
        """Attribute the CrewAI aggregate token usage to a single pipeline agent.

        CrewAI reports usage in aggregate (not per sub-agent), so this is one row
        with provider 'ollama'; names vary across versions, so read defensively."""
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
        self._sink.record_usage(
            agent=agent,
            model="crewai-local-pipeline (multi-model)",
            provider="ollama",
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            latency_seconds=latency,
        )

    @staticmethod
    def _normalize_findings(report) -> List[dict]:
        """Map the Reporter agent's final JSON findings into the shared finding
        shape. The Reporter output is LLM-produced, so read keys defensively."""
        if not isinstance(report, dict):
            return []
        items = report.get("findings")
        if not isinstance(items, list):
            items = []
        findings = []
        for it in items:
            if not isinstance(it, dict):
                continue
            findings.append(
                {
                    "port": it.get("port"),
                    "service_name": it.get("service") or it.get("service_name"),
                    "action": "ANALYSIS",
                    "command": it.get("verification_command") or it.get("command"),
                    "output": (
                        it.get("raw_output")
                        or it.get("evidence")
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

    def _create_tasks(self):
        plan_task = Task(
            agent=self.planner,
            description=(
                f"Develop a phased penetration testing strategy for the target: {self.target}.\n"  # noqa: E501
                f"User objective: {self.user_prompt}\n\n"
                "Your plan MUST follow this structure:\n"
                "Phase 1 - Recon: passive information gathering objectives.\n"
                "Phase 2 - Enumeration: active service and version detection objectives.\n"  # noqa: E501
                "Phase 3 - Exploitation: vulnerability validation objectives.\n"
                "Phase 4 - Reporting: documentation objectives.\n\n"
                "OUTPUT FORMAT: Return a JSON object with keys: "
                "target, phases[], each phase containing: name, objectives[], suggested_tools[].\n"  # noqa: E501
                "Do NOT include any prose outside the JSON structure."
            ),
            expected_output=(
                "A valid JSON object with target and phases array, "
                "each phase containing name, objectives and suggested_tools."
            ),
        )

        scan_task = Task(
            agent=self.scanner,
            context=[plan_task],
            description=(
                f"Execute service discovery and enumeration on {self.target}.\n\n"
                "REQUIRED STEPS:\n"
                f"1. Run: nmap -sC -sV {self.target} -p-\n"
                "2. Wait for the command to complete fully.\n"
                "3. If web ports are found, run: "
                f"gobuster dir -u http://{self.target} -w /usr/share/wordlists/dirb/common.txt\n"  # noqa: E501
                "4. Capture and return the complete raw terminal output of every command.\n\n"  # noqa: E501
                "CONSTRAINTS:\n"
                "- Return raw tool output only. No summaries, no interpretation.\n"
                f"- Only scan {self.target}. Never substitute or invent targets or addresses.\n"  # noqa: E501
                "- If a command fails, return the exact error message."
            ),
            expected_output=(
                "Raw nmap terminal output (containing open ports, services and versions,"  # noqa: E501
                "and any additional enumeration tools, prefixed with the command that was executed."  # noqa: E501
            ),
        )

        tester_task = Task(
            agent=self.tester,
            context=[scan_task],
            description=(
                f"Analyze the nmap output for {self.target} and attempt to prove vulnerabilities.\n\n"  # noqa: E501
                "TO USE THE TERMINAL, you MUST follow this exact format:\n"
                "Thought: [your reasoning]\n"
                "Action: kali_terminal\n"
                'Action Input: {"command": "your command here"}\n\n'
                "NEVER put the command directly as the Action. "
                "ALWAYS use 'kali_terminal' as the Action and put the command in Action Input.\n\n"  # noqa: E501
                "FOR EVERY OPEN PORT FOUND:\n"
                '1. Action: kali_terminal / Action Input: {"command": "searchsploit <service> <version>"}\n'  # noqa: E501
                '2. Action: kali_terminal / Action Input: {"command": "<verification command>"}\n'  # noqa: E501
                "3. Capture complete raw output.\n\n"
                "OUTPUT FORMAT: Return a JSON array where each entry contains:\n"
                "port, service, version, searchsploit_output, "
                "verification_command, raw_output, confirmed (bool).\n\n"
                "CONSTRAINTS:\n"
                "- Never fabricate CVE IDs, exploit names, or tool output.\n"
                "- Never use placeholders. Every field must contain real data.\n"
                "- If no exploit is found, set confirmed=false and explain in raw_output.\n"  # noqa: E501
                "- Only operate on ports and services present in the scanner context."
            ),
            expected_output=(
                "A JSON array of exploitation attempt objects, each containing "
                "port, service, version, searchsploit_output, verification_command, "
                "raw_output, and confirmed fields."
            ),
        )

        summarize_task = Task(
            agent=self.summarizer,
            context=[scan_task, tester_task],
            description=(
                "You have been provided with raw scanner and tester output in your context.\n"  # noqa: E501
                "DO NOT use your own knowledge under any circumstances.\n"
                "DO NOT invent services, ports, versions, or operating systems.\n\n"
                "STEP 1 — Read the scanner context carefully.\n"
                "STEP 2 — Extract ONLY lines containing the word 'open'.\n"
                "STEP 3 — For each line, parse the port number, service name, and version.\n"  # noqa: E501
                "STEP 4 — Read the tester context and extract only commands that were actually executed.\n\n"  # noqa: E501
                "If a port does not appear in the scanner context, it MUST NOT appear in your output.\n"  # noqa: E501
                "If a service version does not appear in the scanner context, do not include it.\n\n"  # noqa: E501
                "The target is a Linux machine. If you find yourself writing Windows services "  # noqa: E501
                "(msrpc, microsoft-ds, ms-wbt-server), STOP — you are hallucinating.\n\n"  # noqa: E501
                "OUTPUT FORMAT: Valid JSON only with open_ports[] and exploitation_attempts[].\n"  # noqa: E501
                "No markdown. No prose. No code fences."
            ),
            expected_output=(
                "A compact JSON object derived exclusively from the provided scanner context, "  # noqa: E501
                "with open_ports[] containing only ports that appear in the nmap output."  # noqa: E501
            ),
        )

        critic_task = Task(
            agent=self.critic,
            context=[summarize_task],
            description=(
                f"Audit all findings for target {self.target}.\n\n"
                "FOR EVERY FINDING IN THE TESTER OUTPUT:\n"
                "1. Verify the IP/hostname matches the target.\n"
                "2. Verify the port and service exist in the scanner output.\n"
                "3. Verify the raw_output is non-empty and non-generic.\n"
                "4. Flag any CVE or exploit name not supported by raw terminal evidence.\n\n"  # noqa: E501
                "OUTPUT FORMAT: Return a JSON object with:\n"
                "validated_findings[], rejected_findings[], "
                "hallucination_flags[], overall_confidence_score (0.0-1.0).\n\n"
                "CONSTRAINTS:\n"
                "- Reject any finding where confirmed=true but raw_output is empty or generic.\n"  # noqa: E501
                "- A confidence score above 0.7 requires at least one confirmed=true finding "  # noqa: E501
                "with non-empty raw_output.\n"
                "- Do not add, infer, or enrich any finding. Only validate or reject."
            ),
            expected_output=(
                "A JSON audit report with validated_findings, rejected_findings, "
                "hallucination_flags, and overall_confidence_score."
            ),
        )

        report_task = Task(
            agent=self.reporter,
            context=[plan_task, summarize_task, critic_task],
            description=(
                "Generate the final penetration test report from the validated data.\n\n"  # noqa: E501
                "OUTPUT FORMAT: Return a single valid JSON object with these exact keys:\n"  # noqa: E501
                "- target: string\n"
                f"- use this exact value for scan_date: {_utc_now()}\n"
                "- executive_summary: string, max 3 sentences\n"
                "- findings: array of validated findings from critic output\n"
                "- rejected_findings: array from critic output\n"
                "- recommendations: array of actionable strings\n"
                "- confidence_score: float from critic output\n\n"
                "CONSTRAINTS:\n"
                "- Use only data present in the context. Never add unreported vulnerabilities.\n"  # noqa: E501
                "- If findings is empty, reflect that accurately.\n"
                "- Output must be raw JSON only. No markdown, no prose, no code fences.\n"  # noqa: E501
                "- The output must be directly parseable by json.loads()."
            ),
            expected_output=(
                "A single valid JSON object with target, scan_date, executive_summary, "
                "findings, rejected_findings, recommendations, and confidence_score."
            ),
        )

        return [
            plan_task,
            scan_task,
            tester_task,
            summarize_task,
            critic_task,
            report_task,
        ]

    def run(self) -> dict:
        self._check_cancel()
        tasks = self._create_tasks()

        talos_crew = Crew(
            tasks=tasks,
            verbose=True,
            memory=False,
            process=Process.sequential,
            agents=[
                self.planner,
                self.scanner,
                self.tester,
                self.summarizer,
                self.critic,
                self.reporter,
            ],
        )

        self._emit_log("Planner", "Running local CrewAI pipeline...")
        started = time.monotonic()
        result = talos_crew.kickoff()
        self._record_crew_usage(
            "local_pipeline", talos_crew, result, time.monotonic() - started
        )

        # The Reporter agent emits the final JSON report; parse defensively so a
        # malformed report degrades to zero findings instead of failing the run.
        try:
            report = self._extract_json(str(result))
        except (json.JSONDecodeError, ValueError) as e:
            errors.log_detail("LocalOrchestrator reporter JSON parse failed", e)
            report = {}

        findings = self._normalize_findings(report)
        ports = self._ports_from_findings(findings)
        if ports:
            self._sink.services_discovered(ports)
        for finding in findings:
            self._sink.finding(finding)

        self._emit_log("Reporter", "Final report generated.", "success")
        return {"status": "completed", "target": self.target, "findings": len(findings)}

    @staticmethod
    def _extract_json(raw: str) -> dict:
        import re

        cleaned = re.sub(r"```json|```", "", raw).strip()
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise ValueError(f"No valid JSON found in reporter output: {raw[:200]}")
