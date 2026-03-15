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
            description=f"Target: {self.target}\nInstructions: {self.user_prompt}\nCreate a pentest strategy.", # noqa: E501
            expected_output="A prioritized list of scanning objectives.",
        )

        scan_task = Task(
            agent=self.scanner,
            context=[plan_task],
            description=f"Scan {self.target} using 'kali_terminal'. Run nmap -sV to find services.", # noqa: E501
            expected_output="The raw terminal output from the Nmap scan.",
        )

        tester_task = Task(
            agent=self.tester,
            context=[scan_task],
            description="Examine scan output. Use 'kali_terminal' to test for common vulnerabilities.", # noqa: E501
            expected_output="A list of confirmed vulnerabilities with terminal evidence.", # noqa: E501
        )

        critic_task = Task(
            agent=self.critic,
            context=[tester_task],
            description="Verify the findings. Check for hallucinations in the exploit reports.", # noqa: E501
            expected_output="A verified list of security flaws.",
        )

        report_task = Task(
            agent=self.reporter,
            context=[plan_task, scan_task, tester_task, critic_task],
            description="Create a final JSON report including target, ports, and vulnerabilities.", # noqa: E501
            expected_output="A raw JSON object containing the mission results without any markdown formatting.", # noqa: E501
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
