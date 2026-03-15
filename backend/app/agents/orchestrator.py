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
            description=(
                f"Target: {self.target}\n"
                f"User Instructions: {self.user_prompt}\n\n"
                "Develop a high-level pentest strategy. Focus on identifying the most "
                "vulnerable entry points (e.g., outdated services on Metasploitable)."
            ),
            expected_output="A prioritized list of scanning objectives and OODA-based strategy.", # noqa: E501
        )

        scan_task = Task(
            agent=self.scanner,
            context=[plan_task],
            description=(
                f"Identify services on {self.target}. USE the 'kali_terminal' tool to "
                "execute Nmap. Start with a fast scan, then probe versions (-sV) for "
                "discovered open ports."
            ),
            expected_output="Raw Nmap output showing open ports and service versions."
        )

        tester_task = Task(
            agent=self.tester,
            context=[scan_task],
            description=(
                "Analyze the scan results for vulnerabilities. USE the 'kali_terminal' "
                "tool to verify exploits (e.g., searchsploit, check for default creds, "
                "or version-specific vulnerabilities like vsftpd 2.3.4)."
            ),
            expected_output="Detailed evidence of vulnerabilities found, including command outputs." # noqa: E501
        )

        critic_task = Task(
            agent=self.critic,
            context=[tester_task],
            description=(
                "Review the findings from the tester. Verify if the conclusions match "
                "the technical evidence provided in the terminal output. Flag any "
                "hallucinations or false positives."
            ),
            expected_output="A verified and filtered list of confirmed security flaws."
        )

        report_task = Task(
            agent=self.reporter,
            # IMPORTANT: Reporter needs context from the Critic and Plan
            context=[plan_task, scan_task, tester_task, critic_task],
            description=(
                "Compile the mission results into a structured JSON report. "
                "Include the target IP, discovered ports, and confirmed vulnerabilities." # noqa: E501
            ),
            expected_output=(
                "A raw, valid JSON object. No markdown, no conversational filler. "
                "Structure: {'target': str, 'ports': list, 'vulnerabilities': list, 'summary': str}" # noqa: E501
            )
        )

        return [plan_task, scan_task, tester_task, critic_task, report_task]

    # def _create_tasks(self):
    #     plan_task = Task(
    #         agent=self.planner,
    #         description=(
    #             f"""Target: {self.target}\n
    #             User Instructions: {self.user_prompt}\n\n
    #             Develop a high-level pentest strategy based on these instructions."""
    #         ),
    #         expected_output="""A prioritized list of scanning objectives
    #         and OODA-based strategy.""",
    #     )

    #     scan_task = Task(
    #         agent=self.scanner,
    #         context=[plan_task],
    #         description=(
    #             f"Based on the strategy, USE the 'kali_terminal' tool to execute "
    #             f"the necessary Nmap/recon commands against {self.target}. "
    #             f"Do not just list the commands; run them and provide the raw output."
    #         ),
    #         expected_output="The actual results/output from the terminal commands executed." # noqa: E501
    #     )

    #     tester_task = Task(
    #         agent=self.tester,
    #         context=[scan_task],
    #         description=(
    #             "Review the scan results. USE the 'kali_terminal' tool to run "
    #             "vulnerability checks (like searchsploit or specific service probes) "
    #             "to confirm potential CVEs on the target."
    #         ),
    #         expected_output="A list of confirmed vulnerabilities with evidence from the terminal." # noqa: E501
    #     )

    #     critic_task = Task(
    #         agent=self.critic,
    #         context=[tester_task],
    #         description="""Review the commands generated by the scanner.
    #         Ensure they are safe and syntactically correct.""",
    #         expected_output="A list of approved, safe-to-execute commands."
    #     )

    #     report_task = Task(
    #         agent=self.reporter,
    #         context=[plan_task, critic_task],
    #         description="""Summarize the entire mission strategy
    #         and the approved technical steps.""",
    #         expected_output="""A raw, valid JSON object.
    #         IMPORTANT: Do not wrap the output in markdown code blocks (no ```json).
    #         Do not include any conversational text before or after the JSON.
    #         Ensure all strings are plain text without unnecessary escape sequences."""
    #     )

    #     return [plan_task, scan_task, tester_task, critic_task, report_task]

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
