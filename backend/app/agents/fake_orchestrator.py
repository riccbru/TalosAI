"""A dependency-free stand-in for HybridOrchestratorV2.

Emits the exact same reporter calls (services_discovered -> port_status ->
finding -> ...) on a timer, with no Kali, Gemini or Metasploitable, and supports
cooperative cancel and resume identically to the real engine. Used by the tests
to exercise the orchestration mechanism; it is NOT wired into the running app.
"""
import time
from typing import Callable, List, Optional

from app.agents.mission_exceptions import MissionCancelled

# A small, realistic-looking roster (mirrors a Metasploitable-style target).
FAKE_SERVICES = [
    {"port": 21, "service_name": "ftp", "version": "vsftpd 2.3.4"},
    {"port": 22, "service_name": "ssh", "version": "OpenSSH 4.7p1"},
    {"port": 80, "service_name": "http", "version": "Apache httpd 2.2.8"},
]
STEP_DELAY_SECONDS = 1.5  # slow enough to watch the DB fill and to cancel mid-run
ATTEMPTS_PER_PORT = 2


class _PrintReporter:
    """Default sink when run standalone (no DB/stream)."""

    def log(self, step, message, status="running"):
        print(f"[FAKE] [{status.upper()}] {step} -> {message}", flush=True)

    def services_discovered(self, services):
        pass

    def finding(self, data):
        pass

    def port_status(self, port, status, attempts, history):
        pass

    def mission_status(self, status, error=None):
        pass


class FakeOrchestratorV2:
    def __init__(
        self,
        target: str,
        user_prompt: Optional[str] = None,
        reporter=None,
        initial_services: Optional[List[dict]] = None,
        should_cancel: Optional[Callable[[], bool]] = None,
    ):
        self.target = target
        self.user_prompt = user_prompt or "Fake comprehensive penetration test."
        self.reporter = reporter or _PrintReporter()
        self.initial_services = initial_services
        self._should_cancel = should_cancel or (lambda: False)

    def _check_cancel(self) -> None:
        if self._should_cancel():
            raise MissionCancelled()

    def run(self) -> dict:
        self._check_cancel()

        if self.initial_services:  # resume: reuse persisted roster
            services = self.initial_services
        else:
            self.reporter.log(
                "Manager", f"[FAKE] Starting discovery scan on {self.target}..."
            )
            time.sleep(STEP_DELAY_SECONDS)
            services = [
                {**svc, "status": "pending", "attempts": 0, "history": []}
                for svc in FAKE_SERVICES
            ]
            self.reporter.services_discovered(services)

        self.reporter.log(
            "Manager",
            f"Discovered {len(services)} services to investigate.",
            "completed",
        )

        for service in services:
            self._check_cancel()
            if service.get("status") == "completed":
                continue

            port = service["port"]
            name = service["service_name"]
            version = service["version"]
            history = list(service.get("history") or [])
            attempts = int(service.get("attempts") or 0)

            self.reporter.log(
                "Manager",
                f"Investigating Port {port} ({name} - Version: {version})...",
            )
            self.reporter.port_status(port, "in_progress", attempts, history)

            while attempts < ATTEMPTS_PER_PORT:
                self._check_cancel()
                attempts += 1
                command = f"[FAKE] probe {name} on {port} (attempt {attempts})"
                self.reporter.log(
                    f"Manager [Port {port}]",
                    f"Decision: EXECUTE_ATTACK -> simulated probe of {name}",
                )
                time.sleep(STEP_DELAY_SECONDS)

                output = (
                    f"[FAKE OUTPUT] {name} {version} responded on port {port} "
                    f"(attempt {attempts})"
                )
                history.append({"command_sent": command, "terminal_output": output})
                self.reporter.finding(
                    {
                        "port": port,
                        "service_name": name,
                        "action": "EXECUTE_ATTACK",
                        "command": command,
                        "output": output,
                        "reasoning": f"Simulated investigation of {name} {version}.",
                        "confirmed": port == 21,  # pretend the ftp backdoor is real
                    }
                )
                self.reporter.port_status(port, "in_progress", attempts, history)

            service["status"] = "completed"
            service["attempts"] = attempts
            service["history"] = history
            self.reporter.port_status(port, "completed", attempts, history)
            self.reporter.log(
                "Manager", f"Finished investigation on port {port}.", "success"
            )

        return {"status": "completed", "target": self.target, "services": len(services)}
