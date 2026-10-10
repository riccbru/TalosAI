import json
import re
import time
from typing import Callable, List, Optional

# from crewai import Crew, Task
from google import genai
from pydantic import BaseModel, Field

from app.agents.mission_exceptions import MissionCancelled  # noqa: F401 (re-export)
from app.agents.tester import get_tester_agent
from app.agents.tools import kali_tool
from app.core.config import settings


gemini_client = genai.Client()

# Gemini free tier allows ~15 requests/min per model. Stay safely under that with a
# client-side throttle, and retry on 429 (RESOURCE_EXHAUSTED) instead of letting it
# bubble up as a 500. ~4.5s spacing => <14 calls/min.
_MIN_SECONDS_BETWEEN_CALLS = 4.5
_MAX_RETRIES_ON_429 = 5
_last_call_ts = 0.0


class DiscoveredService(BaseModel):
    port: int
    service_name: str
    version: str


class InitialScanOutput(BaseModel):
    hosts_up: bool
    services: List[DiscoveredService]


class NextStepDecision(BaseModel):
    action: str = Field(
        description="Possible values:" \
        "'COMPLETED', 'SEARCH_EXPLOIT', 'EXECUTE_ATTACK', or 'NEXT_PORT'"
    )
    target_port: Optional[int]
    specific_command: Optional[str] = Field(
        description="Il comando esatto che il Tester deve eseguire sul terminale"
    )
    reasoning: str = Field(description="Perché il manager ha preso questa decisione")


class NoOpReporter:
    """Default sink: prints logs, persists nothing. Used when running standalone."""

    def log(self, step: str, message: str, status: str = "running") -> None:
        print(
            f"\n[TALOSAI_LOG] [{status.upper()}] {step} -> {message}", flush=True
        )

    def services_discovered(self, services: list) -> None:
        pass

    def finding(self, data: dict) -> None:
        pass

    def port_status(
        self, port: int, status: str, attempts: int, history: list
    ) -> None:
        pass

    def mission_status(self, status: str, error: Optional[str] = None) -> None:
        pass


class HybridOrchestratorV2:
    def __init__(
        self,
        target: str,
        user_prompt: Optional[str] = None,
        reporter=None,
        initial_services: Optional[List[dict]] = None,
        should_cancel: Optional[Callable[[], bool]] = None,
    ):
        self.target = target
        self.local_executor = get_tester_agent()
        self.user_prompt = (
            user_prompt or "Perform a comprehensive structural penetration test."
        )
        self.reporter = reporter or NoOpReporter()
        # When provided (resume), discovery is skipped and these per-port states
        # (each: port, service_name, version, status, attempts, history) are used.
        self.initial_services = initial_services
        # Cooperative cancellation: checked at safe checkpoints (between ports and
        # between attempts). A long in-flight command finishes before the stop takes.
        self._should_cancel = should_cancel or (lambda: False)

    def _emit_log(self, step_name: str, message: str, status: str = "running"):
        self.reporter.log(step_name, message, status)

    def _check_cancel(self) -> None:
        if self._should_cancel():
            raise MissionCancelled()

    # def _execute_micro_task(
    #     self, command_to_run: str, expected_description: str
    # ) -> str:
    #     micro_task = Task(
    #         agent=self.local_executor,
    #         description=
    #         f"Execute this exact command inside Kali container: {command_to_run}. " \
    #         f"Context: {expected_description}",
    #         expected_output="The raw command-line stdout/stderr output.",
    #     )
    #     crew = Crew(tasks=[micro_task], agents=[self.local_executor], verbose=False)
    #     output = crew.kickoff()
    #     return output.raw if hasattr(output, "raw") else str(output)

    def _execute_micro_task(
            self, command_to_run: str, expected_description: str
        ) -> str:
        self._emit_log("Tester", f"Running directly via Docker: {command_to_run}")
        output = kali_tool._run(command=command_to_run)
        return output

    @staticmethod
    def _parse_retry_delay(message: str, fallback: float = 30.0) -> float:
        # Gemini surfaces the suggested wait either as "Please retry in 30.04s"
        # or as a RetryInfo "retryDelay": "30s" field. Honor whichever is present.
        for pattern in (r"retry in ([\d.]+)s", r"retryDelay'?:\s*'?(\d+(?:\.\d+)?)s"):
            match = re.search(pattern, message)
            if match:
                return float(match.group(1)) + 1.0  # small cushion
        return fallback

    def _generate(self, prompt: str, schema, _retry: int = 0) -> dict:
        global _last_call_ts

        wait = _MIN_SECONDS_BETWEEN_CALLS - (time.monotonic() - _last_call_ts)
        if wait > 0:
            time.sleep(wait)

        try:
            resp = gemini_client.models.generate_content(
                contents=prompt,
                model=settings.GEMINI_MODEL,
                config=genai.types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=schema,
                ),
            )
            return json.loads(resp.text)
        except Exception as e:
            msg = str(e)
            is_rate_limit = "429" in msg or "RESOURCE_EXHAUSTED" in msg
            if is_rate_limit and _retry < _MAX_RETRIES_ON_429:
                delay = self._parse_retry_delay(msg)
                self._emit_log(
                    "Manager",
                    f"Gemini rate limit hit; backing off {delay:.0f}s "
                    f"(retry {_retry + 1}/{_MAX_RETRIES_ON_429})...",
                )
                time.sleep(delay)
                return self._generate(prompt, schema, _retry=_retry + 1)
            raise
        finally:
            _last_call_ts = time.monotonic()

    def _discover_services(self) -> List[dict]:
        """Run nmap, parse it, and return per-port working state (fresh run)."""
        self._check_cancel()
        self._emit_log(
            "Manager",
            f"Starting initial service discovery scan on {self.target}...",
        )
        raw_nmap_output = self._execute_micro_task(
            command_to_run=f"nmap -sV -sC -F {self.target}",
            expected_description="Initial fast service verification scan.",
        )

        self._emit_log("Manager", "Parsing raw Nmap output with Gemini...")
        parse_prompt = (
            "Analyze this raw Nmap output and extract all active "
            f"services:\n{raw_nmap_output}"
        )
        scan_data = self._generate(parse_prompt, InitialScanOutput)

        services = [
            {
                "port": s["port"],
                "service_name": s["service_name"],
                "version": s["version"],
                "status": "pending",
                "attempts": 0,
                "history": [],
            }
            for s in scan_data.get("services", [])
        ]
        # Persist the port roster immediately so a crash right after discovery
        # still leaves a resumable mission.
        self.reporter.services_discovered(services)
        return services

    def run(self) -> dict:
        self._check_cancel()
        # Resume reuses the persisted roster; a fresh run (or a resume of a
        # mission that crashed before any port was saved) runs discovery.
        if self.initial_services:
            services = self.initial_services
        else:
            services = self._discover_services()

        self._emit_log(
            "Manager",
            f"Discovered {len(services)} services to investigate.",
            "completed",
        )

        for service in services:
            self._check_cancel()
            # Resume: ports already finished are skipped.
            if service.get("status") == "completed":
                continue

            port = service["port"]
            name = service["service_name"]
            version = service["version"]
            history_of_this_port = list(service.get("history") or [])
            attempts = int(service.get("attempts") or 0)

            self._emit_log(
                "Manager",
                f"Investigating Port {port} ({name} - Version: {version})...",
                "running",
            )
            self.reporter.port_status(
                port, "in_progress", attempts, history_of_this_port
            )

            port_completed = False
            while not port_completed and attempts < 5:
                self._check_cancel()
                attempts += 1

                manager_prompt = (
                    f"You are the Lead Pentester managing an attack loop against target {self.target}.\n"  # noqa: E501
                    f"Current Focus -> Port: {port}, Service: {name}, Version: {version}.\n"  # noqa: E501
                    f"What we tried so far on this port:\n{json.dumps(history_of_this_port, indent=2)}\n\n"  # noqa: E501
                    f"Decide the next step. If you found a vulnerability/access point or concluded it is not vulnerable, "  # noqa: E501
                    f"set action to 'NEXT_PORT' or 'COMPLETED'. Otherwise, provide the exact 'specific_command' for the tester.\n\n"  # noqa: E501
                    "Rules for 'specific_command' (the tester runs it verbatim, and the pentester must be able to copy-paste it to reproduce the finding):\n"  # noqa: E501
                    "- Prefer Metasploit or target-specific automated tools over raw .py/.rb exploitdb scripts.\n"  # noqa: E501
                    "- The command MUST be non-interactive and self-terminating: it must NEVER leave an open shell or console (that hangs the run).\n"  # noqa: E501
                    "- For Metasploit, use exactly this shape:\n"
                    "  msfconsole -q -x \"use <module>; set RHOSTS <ip>; set RPORT <port>; <other options>; run -z; sessions -c id; exit -y\"\n"  # noqa: E501
                    "    * 'run -z' opens the session in the background instead of dropping into an interactive shell.\n"  # noqa: E501
                    "    * 'sessions -c id' proves exploitation by running a command on the opened session and printing its output.\n"  # noqa: E501
                    "    * always finish with 'exit -y' so msfconsole quits.\n"
                    "- Do NOT guess or hardcode a payload name. Let Metasploit use the module's DEFAULT payload (always compatible). Only set a payload if the module has none by default, and then pick from the module's own compatible family (for Unix command-injection modules: cmd/unix/*, e.g. cmd/unix/reverse); never set a Meterpreter or exotic payload on a command-injection module. Do not hardcode LHOST unless required; let Metasploit auto-detect the local interface.\n"  # noqa: E501
                    "- Consider the exploit successful ONLY if the output shows a session opened AND the proof command ('id'/'whoami') returned output; otherwise treat the service as not vulnerable and move on.\n"  # noqa: E501
                )

                decision = self._generate(manager_prompt, NextStepDecision)

                self._emit_log(
                    f"Manager [Port {port}]",
                    f"Decision: {decision['action']} -> {decision['reasoning']}",
                )

                if decision["action"] in ["NEXT_PORT", "COMPLETED"]:
                    port_completed = True
                    continue

                if decision["specific_command"]:
                    cmd_output = self._execute_micro_task(
                        command_to_run=decision["specific_command"],
                        expected_description=f"Testing vulnerability on port {port}",  # noqa: E501
                    )

                    history_of_this_port.append(
                        {
                            "command_sent": decision["specific_command"],
                            "terminal_output": cmd_output[:2000],
                        }
                    )

                    # Each executed step is a durable finding, pushed live and
                    # persisted the moment it happens.
                    self.reporter.finding(
                        {
                            "port": port,
                            "service_name": name,
                            "action": decision["action"],
                            "command": decision["specific_command"],
                            "output": cmd_output[:4000],
                            "reasoning": decision["reasoning"],
                            "confirmed": False,
                        }
                    )
                    self.reporter.port_status(
                        port, "in_progress", attempts, history_of_this_port
                    )

            service["status"] = "completed"
            service["attempts"] = attempts
            service["history"] = history_of_this_port
            self.reporter.port_status(
                port, "completed", attempts, history_of_this_port
            )
            self._emit_log(
                "Manager", f"Finished investigation on port {port}.", "success"
            )

        return {"status": "completed", "target": self.target, "services": len(services)}
