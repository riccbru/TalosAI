import json
from typing import Optional

from crewai import Crew, Process, Task
from google import genai

from app.agents.tester import get_tester_agent
from app.core.config import settings


gemini_client = genai.Client()



class HybridOrchestrator:
    def __init__(self, target: str, user_prompt: Optional[str] = None):
        self.target = target
        self.local_executor = get_tester_agent()
        self.user_prompt = (
            user_prompt or "Perform a standard comprehensive security analysis."
        )

    def _emit_log(self, step_name: str, message: str, status: str = "running"):
        print(
            f"\n[TALOSAI_LOG] [{status.upper()}] {step_name} -> {message}", flush=True
        )

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
        try:
            self._emit_log(
                "Planner",
                f"Cyber planning: {self.target}",
            )

            planning_prompt = (
                f"You are the master planner for a "
                f"penetration test against: {self.target}.\n"
                f"User Directive: {self.user_prompt}\n"
                "Generate a clear, bulleted execution "
                "strategy for a local tool executor."
            )

            # self._emit_log(
            #     "Planner", f"[GEMINI API CALL] model={settings.GEMINI_MODEL}"
            # )
            print(f"[GEMINI API CALL] Planner Agent: model={settings.GEMINI_MODEL}")
            response_planner = gemini_client.models.generate_content(
                contents=planning_prompt,
                model=settings.GEMINI_MODEL,
            )
            if (
                response_planner is None
                or not hasattr(response_planner, "text")
                or response_planner.text is None
            ):
                return {
                    "code": 429,
                    "status": "failed",
                    "source": "google",
                    "details": {
                        "code": 429,
                        "status": "RESOURCE_EXHAUSTED",
                        "message": "Gemini returned an empty response. "
                        "Likely free tier quota limit hit.",
                    },
                }
            strategy = response_planner.text
            self._emit_log("Planner", "Cyber planning created", "completed")
            print(f"--- Chain of Thought ---\n{strategy}\n----------------")

            self._emit_log(
                "Executor", "Initializing local CrewAI for executing tasks..."
            )
            tasks = self._create_tasks(strategy)

            crew = Crew(
                tasks=tasks,
                verbose=True,
                process=Process.sequential,
                agents=[self.local_executor],
            )

            raw_execution_logs = crew.kickoff()
            raw_logs_text = (
                raw_execution_logs.raw
                if hasattr(raw_execution_logs, "raw")
                else str(raw_execution_logs)
            )

            self._emit_log(
                "Executor",
                "CrewAI completed commands execution.",
                "completed",
            )

            self._emit_log(
                "Critic",
                "Send raw logs to Gemini for anti-hallucinations audit...",
            )

            prompt_audit = (
                f"Analyze these raw terminal execution "
                f"logs for the target {self.target}:\n"
                f"{raw_logs_text}\n\n"
                "Extract confirmed findings. For each finding "
                "specify: port, service, and vulnerability."
            )

            # self._emit_log(
            #     "Critic", f"[GEMINI API CALL] model={settings.GEMINI_MODEL}"
            # )
            print(f"[GEMINI API CALL] Critic Agent: model={settings.GEMINI_MODEL}")
            response_critic = gemini_client.models.generate_content(
                contents=prompt_audit,
                model=settings.GEMINI_MODEL,
                config=genai.types.GenerateContentConfig(
                    response_mime_type="application/json",
                ),
            )
            if (
                response_critic is None
                or not hasattr(response_critic, "text")
                or response_critic.text is None
            ):
                return {
                    "status": "failed",
                    "source": "critic_empty",
                    "message":
                    "Gemini Critic returned an empty response. Cannot audit findings.",
                }

            try:
                validated_json = json.loads(response_critic.text)
            except json.JSONDecodeError as e:
                return {
                    "status": "failed",
                    "source": "critic_parse",
                    "message": f"Gemini returned non-JSON response: {e}",
                    "raw": response_critic.text,
                }
            except TypeError as e:
                return {
                    "status": "failed",
                    "source": "critic_type_error",
                    "message": f"Invalid data type received from Critic: {e}",
                }
            except Exception as e:
                return {
                    "status": "failed",
                    "source": "critic_generic_error",
                    "message": f"Unexpected error during JSON validation: {str(e)}",
                }

            self._emit_log("Critic", "Audit completed successfully", "success")

            return {
                "status": "completed",
                "target": self.target,
                "findings": validated_json,
            }

        except genai.errors.APIError as e:
            print(f"[TALOSAI_LOG] [GOOGLE_ERROR] {e.code} - {e.message}")

            return {
                "code": e.code,
                "status": "failed",
                "source": "google",
                "details": {
                    "code": e.code,
                    "status": getattr(e, "status", "failed"),
                    "message": e.message,
                }
            }

        except Exception as e:
            # self._emit_log("Error", f"Error during execution: {str(e)}", "failed")
            return {
                "code": 500,
                "status": "error",
                "source": "generic",
                "message": str(e)
            }
