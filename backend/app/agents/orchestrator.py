from typing import Optional

from crewai import Crew, Process, Task

from app.agents.critic import get_critic_agent
from app.agents.planner import get_planner_agent
from app.agents.reporter import get_reporter_agent
from app.agents.scanner import get_scanner_agent
from app.agents.tester import get_tester_agent


class Orchestrator:
    def __init__(self, target: str, user_prompt: Optional[str] = None):
        self.target = target
        self.planner = get_planner_agent()
        self.scanner = get_scanner_agent()
        self.tester = get_tester_agent()
        self.critic = get_critic_agent()
        self.reporter = get_reporter_agent()
        self.user_prompt = user_prompt or \
        """Perform a standard comprehensive security analysis."""

    def _create_tasks(self):
        plan_task = Task(
            agent=self.planner,
            description=f"Develop a phased pentest strategy for the target: {self.target}. Logic: {self.user_prompt}", # noqa: E501
            expected_output="A list of technical objectives for reconnaissance and validation." # noqa: E501
        )

        scan_task = Task(
            agent=self.scanner,
            context=[plan_task],
            description=(
                f"Execute service discovery and version detection on {self.target} via 'kali_terminal'." # noqa: E501
                "Use 'nmap -sC -sV'. Output MUST be the raw tool response."
            ),
            expected_output="Raw terminal output from the discovery tools."
        )

        tester_task = Task(
            agent=self.tester,
            context=[scan_task],
            description=(
                f"Analyze the raw logs for {self.target}. For every open port found:\n"
                "1. Search for exploits via 'searchsploit'.\n"
                "2. Execute a verification command in 'kali_terminal' to prove the vulnerability.\n" # noqa: E501
                "3. Capture raw terminal output. NO SUMMARIES. NO PLACEHOLDERS."
            ),
            expected_output="Detailed execution logs showing the results of every probe." # noqa: E501
        )

        critic_task = Task(
            agent=self.critic,
            context=[scan_task, tester_task],
            description=f"AUDIT MODE: Ensure all findings belong to {self.target}. Reject any generic data or unreachable IPs.", # noqa: E501
            expected_output="A confirmation that all data is grounded in terminal evidence.", # noqa: E501
        )

        report_task = Task(
            agent=self.reporter,
            context=[plan_task, scan_task, tester_task, critic_task],
            description="Transform the validated terminal logs into a structured JSON report. Mirror the raw data exactly.", # noqa: E501
            expected_output="A valid JSON object containing verified target data." # noqa: E501
        )

        return [plan_task, scan_task, tester_task, critic_task, report_task]

    def run(self):
        tasks = self._create_tasks()

        talos_crew = Crew(
            tasks=tasks,
            verbose=True,
            memory=False,
            process=Process.sequential,
            agents=[self.planner, self.scanner, self.tester, self.critic, self.reporter]
        )

        return talos_crew.kickoff()
