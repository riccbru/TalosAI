import json
import subprocess
from typing import List, Optional

# from crewai import Crew, Task
from google import genai
from pydantic import BaseModel, Field

from app.agents.tester import get_tester_agent
from app.core.config import settings


gemini_client = genai.Client()


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


class HybridOrchestratorV2:
    def __init__(self, target: str, user_prompt: Optional[str] = None):
        self.target = target
        self.local_executor = get_tester_agent()  # Il nostro Braccio (Kali Terminal)
        self.user_prompt = (
            user_prompt or "Perform a comprehensive structural penetration test."
        )
        self.mission_findings = []

    def _emit_log(self, step_name: str, message: str, status: str = "running"):
        print(
            f"\n[TALOSAI_LOG] [{status.upper()}] {step_name} -> {message}", flush=True
        )

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
        TIMEOUT = 200
        try:
            full_cmd = ["docker", "exec", "talos_kali", "bash", "-c", command_to_run]

            result = subprocess.run(
                full_cmd,
                text=True,
                timeout=TIMEOUT,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            output = result.stdout + result.stderr
            return output if output.strip() else "Command executed with no output."

        except subprocess.TimeoutExpired:
            return f"ERROR: Command execution timed out after {TIMEOUT} seconds."
        except Exception as e:
            return f"ERROR: Failed to run command via Docker: {str(e)}"

    def run(self) -> dict:
        try:
            self._emit_log(
                "Manager",
                f"Starting initial service discovery scan on {self.target}...",
            )

            raw_nmap_output = self._execute_micro_task(
                command_to_run=f"nmap -sV -sC -F {self.target}",
                expected_description="Initial fast service verification scan.",
            )

            self._emit_log("Manager", "Parsing raw Nmap output with Gemini...")
            parse_prompt = f"Analyze this raw Nmap output and " \
            f"extract all active services:\n{raw_nmap_output}"

            response = gemini_client.models.generate_content(
                contents=parse_prompt,
                model=settings.GEMINI_MODEL,
                config=genai.types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=InitialScanOutput,
                ),
            )
            scan_data = json.loads(response.text)
            services_to_test = scan_data.get("services", [])

            self._emit_log(
                "Manager",
                f"Discovered {len(services_to_test)} services to investigate.",
                "completed",
            )

            for service in services_to_test:
                port = service["port"]
                name = service["service_name"]
                version = service["version"]

                self._emit_log(
                    "Manager",
                    f"Investigating Port {port} ({name} - Version: {version})...",
                    "running",
                )

                history_of_this_port = []
                port_completed = False
                attempts = 0

                while not port_completed and attempts < 5:
                    attempts += 1

                    manager_prompt = (
                        f"You are the Lead Pentester managing an attack loop against target {self.target}.\n"  # noqa: E501
                        f"Current Focus -> Port: {port}, Service: {name}, Version: {version}.\n"  # noqa: E501
                        f"What we tried so far on this port:\n{json.dumps(history_of_this_port, indent=2)}\n\n"  # noqa: E501
                        f"Decide the next step. If you found a vulnerability/access point or concluded it is not vulnerable, "  # noqa: E501
                        f"set action to 'NEXT_PORT' or 'COMPLETED'. Otherwise, provide the exact 'specific_command' for the tester."  # noqa: E501
                    )

                    decision_resp = gemini_client.models.generate_content(
                        contents=manager_prompt,
                        model=settings.GEMINI_MODEL,
                        config=genai.types.GenerateContentConfig(
                            response_mime_type="application/json",
                            response_schema=NextStepDecision,
                        ),
                    )
                    decision = json.loads(decision_resp.text)

                    self._emit_log(
                        f"Manager [Port {port}]",
                        f"Decision: {decision['action']} -> {decision['reasoning']}",
                    )

                    if decision["action"] in ["NEXT_PORT", "COMPLETED"]:
                        port_completed = True
                        continue

                    if decision["specific_command"]:
                        self._emit_log(
                            "Tester",
                            f"Executing requested command: {decision['specific_command']}",  # noqa: E501
                        )
                        cmd_output = self._execute_micro_task(
                            command_to_run=decision["specific_command"],
                            expected_description=f"Testing vulnerability on port {port}",  # noqa: E501
                        )

                        history_of_this_port.append(
                            {
                                "command_sent": decision["specific_command"],
                                "terminal_output": cmd_output[
                                    :2000
                                ],
                            }
                        )

                self._emit_log(
                    "Manager", f"Finished investigation on port {port}.", "success"
                )

            return {
                "status": "completed",
                "target": self.target,
                "findings": self.mission_findings,
            }

        except Exception as e:
            return {
                "code": 500,
                "status": "error",
                "source": "orchestrator",
                "message": str(e),
            }
