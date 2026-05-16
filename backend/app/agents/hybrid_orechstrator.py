import json
from typing import Optional

from crewai import Agent, Crew, Process, Task
from google import genai

from app.agents.tools import kali_tool


gemini_client = genai.Client()


def get_local_executor_agent() -> Agent:
    return Agent(
        role="Kali Linux Security Executor",
        goal="Execute low-level terminal commands like nmap "
        "or gobuster without interpreting them.",
        backstory="You are a precise command-line executor. "
        "You only care about terminal outputs.",
        verbose=True,
        allow_delegation=False,
        tools=[kali_tool],
    )


class HybridOrchestrator:
    def __init__(self, target: str, user_prompt: Optional[str] = None):
        self.target = target
        self.user_prompt = (
            user_prompt or "Perform a standard comprehensive security analysis."
        )
        self.local_executor = get_local_executor_agent()

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
                f"You are the master planner for a " \
                f"penetration test against: {self.target}.\n"
                f"User Directive: {self.user_prompt}\n"
                "Generate a clear, bulleted execution " \
                "strategy for a local tool executor."
            )

            response_planner = gemini_client.models.generate_content(
                model="gemini-2.0-flash",
                contents=planning_prompt,
            )
            strategy = response_planner.text
            self._emit_log("Planner", "Cyber planning created", "completed")
            print(
                f"--- Chain of Thought) ---\n{strategy}\n----------------"
            )

            self._emit_log(
                "Executor", "Initializing local CrewAI for executing tasks..."
            )
            tasks = self._create_tasks(strategy)

            crew = Crew(
                agents=[self.local_executor],
                tasks=tasks,
                process=Process.sequential,
                verbose=True,
            )

            raw_execution_logs = crew.kickoff()
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
                f"Analyze these raw terminal execution " \
                "logs for the target {self.target}:\n"
                f"{str(raw_execution_logs)}\n\n"
                "Extract confirmed findings. For each finding " \
                "specify: port, service, and vulnerability."
            )

            response_critic = gemini_client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt_audit,
                config=genai.types.GenerateContentConfig(
                    response_mime_type="application/json",
                ),
            )

            validated_json = json.loads(response_critic.text)
            self._emit_log(
                "Critic", "Audit completed successfully", "success"
            )

            return {
                "status": "completed",
                "target": self.target,
                "findings": validated_json,
            }

        except Exception as e:
            self._emit_log("Error", f"Errore during execution: {str(e)}", "failed")
            return {"status": "failed", "error": str(e)}
