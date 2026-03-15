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
            description=(
                "You are now in the EXPLOITATION PHASE. Follow these steps exactly:\n"
                "1. Read the Port/Service table from the Nmap output.\n"
                "2. For EACH open port:\n" # noqa: E501
                "   a. Use 'searchsploit' in the kali_terminal to find a specific exploit for that version.\n" # noqa: E501
                "   b. Execute a verification command (e.g., 'nc -zv', 'smbclient -L', or 'msfconsole -x', and others).\n" # noqa: E501
                "3. When you find a shell: execute 'whoami; hostname' as a proof of concept.\n" # noqa: E501
                "4. Capture the RAW output for every attempt. If an exploit fails, state WHY based on the terminal logs.\n" # noqa: E501
                "DO NOT skip any services. If you cannot exploit it, you must prove you at least scanned it." # noqa: E501
            ),
            expected_output="A step-by-step log of exploitation attempts for every discovered service, including raw command responses." # noqa: E501
        )

        critic_task = Task(
            agent=self.critic,
            context=[tester_task],
            description=(
                "Audit the Tester's work. Compare the list of ports found by the Scanner " # noqa: E501
                "against the exploits attempted by the Tester. \n"
                "If the Tester missed ANY port (especially 1524 or 6667), send the task back " # noqa: E501
                "or flag it as 'Incomplete Coverage'."
            ),
            expected_output="A coverage report confirming that all 20+ open ports were evaluated." # noqa: E501
        )

        report_task = Task(
            agent=self.reporter,
            context=[plan_task, scan_task, tester_task, critic_task],
            description=(
                "You are a strict technical reporter. You must ONLY report services and versions " # noqa: E501
                "found in the RAW Nmap output. \n"
                "STRICT RULES:\n"
                "1. DO NOT mention serices that are NOT included in the nmap report.\n" # noqa: E501
                "2. Include the exact port numbers found (21, 22, 23, 25, 80, 1524, etc.).\n" # noqa: E501
                "3. Output MUST be valid JSON."
    ),
    expected_output="A JSON object mirroring the REAL technical data found in the terminal logs." # noqa: E501
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
