import json
from typing import Optional

from crewai import Crew, Process, Task

from app.agents.critic import get_critic_agent
from app.agents.planner import get_planner_agent
from app.agents.reporter import get_reporter_agent
from app.agents.scanner import get_scanner_agent
from app.agents.summarizer import get_summarizer_agent
from app.agents.tester import get_tester_agent
from app.core.status import _utc_now


class Orchestrator:
    def __init__(self, target: str, user_prompt: Optional[str] = None):
        self.target = target
        self.planner = get_planner_agent()
        self.scanner = get_scanner_agent()
        self.tester = get_tester_agent()
        self.summarizer = get_summarizer_agent()
        self.critic = get_critic_agent()
        self.reporter = get_reporter_agent()
        self.user_prompt = (
            user_prompt or "Perform a standard comprehensive security analysis."
        )

    def _create_tasks(self):
        plan_task = Task(
            agent=self.planner,
            description=(
                f"Develop a phased penetration testing strategy for the target: {self.target}.\n"  # noqa: E501
                f"User objective: {self.user_prompt}\n\n"
                "Your plan MUST follow this structure:\n"
                "Phase 1 - Recon: passive information gathering objectives.\n"
                "Phase 2 - Enumeration: active service and version detection objectives.\n"  # noqa: E501
                "Phase 3 - Exploitation: vulnerability validation objectives.\n"
                "Phase 4 - Reporting: documentation objectives.\n\n"
                "OUTPUT FORMAT: Return a JSON object with keys: "
                "target, phases[], each phase containing: name, objectives[], suggested_tools[].\n"  # noqa: E501
                "Do NOT include any prose outside the JSON structure."
            ),
            expected_output=(
                "A valid JSON object with target and phases array, "
                "each phase containing name, objectives and suggested_tools."
            )
        )

        scan_task = Task(
            agent=self.scanner,
            context=[plan_task],
            description=(
                f"Execute service discovery and enumeration on {self.target}.\n\n"
                "REQUIRED STEPS:\n"
                f"1. Run: nmap -sC -sV {self.target} -p-\n"
                "2. Wait for the command to complete fully.\n"
                "3. If web ports are found, run: "
                f"gobuster dir -u http://{self.target} -w /usr/share/wordlists/dirb/common.txt\n"  # noqa: E501
                "4. Capture and return the complete raw terminal output of every command.\n\n"  # noqa: E501
                "CONSTRAINTS:\n"
                "- Return raw tool output only. No summaries, no interpretation.\n"
                f"- Only scan {self.target}. Never substitute or invent targets or addresses.\n"  # noqa: E501
                "- If a command fails, return the exact error message."
            ),
            expected_output=(
                "Raw nmap terminal output (containing open ports, services and versions,"  # noqa: E501
                "and any additional enumeration tools, prefixed with the command that was executed."  # noqa: E501
            )
        )

        tester_task = Task(
            agent=self.tester,
            context=[scan_task],
            description=(
                f"Analyze the nmap output for {self.target} and attempt to prove vulnerabilities.\n\n" # noqa: E501
                "TO USE THE TERMINAL, you MUST follow this exact format:\n"
                "Thought: [your reasoning]\n"
                "Action: kali_terminal\n"
                'Action Input: {"command": "your command here"}\n\n'
                "NEVER put the command directly as the Action. "
                "ALWAYS use 'kali_terminal' as the Action and put the command in Action Input.\n\n" # noqa: E501
                "FOR EVERY OPEN PORT FOUND:\n"
                '1. Action: kali_terminal / Action Input: {"command": "searchsploit <service> <version>"}\n' # noqa: E501
                '2. Action: kali_terminal / Action Input: {"command": "<verification command>"}\n' # noqa: E501
                "3. Capture complete raw output.\n\n"
                "OUTPUT FORMAT: Return a JSON array where each entry contains:\n"
                "port, service, version, searchsploit_output, "
                "verification_command, raw_output, confirmed (bool).\n\n"
                "CONSTRAINTS:\n"
                "- Never fabricate CVE IDs, exploit names, or tool output.\n"
                "- Never use placeholders. Every field must contain real data.\n"
                "- If no exploit is found, set confirmed=false and explain in raw_output.\n" # noqa: E501
                "- Only operate on ports and services present in the scanner context."
            ),
            expected_output=(
                "A JSON array of exploitation attempt objects, each containing "
                "port, service, version, searchsploit_output, verification_command, "
                "raw_output, and confirmed fields."
            )
        )

        summarize_task = Task(
            agent=self.summarizer,
            context=[scan_task, tester_task],
            description=(
                "You have been provided with raw scanner and tester output in your context.\n" # noqa: E501
                "DO NOT use your own knowledge under any circumstances.\n"
                "DO NOT invent services, ports, versions, or operating systems.\n\n"
                "STEP 1 — Read the scanner context carefully.\n"
                "STEP 2 — Extract ONLY lines containing the word 'open'.\n"
                "STEP 3 — For each line, parse the port number, service name, and version.\n" # noqa: E501
                "STEP 4 — Read the tester context and extract only commands that were actually executed.\n\n" # noqa: E501
                "If a port does not appear in the scanner context, it MUST NOT appear in your output.\n" # noqa: E501
                "If a service version does not appear in the scanner context, do not include it.\n\n" # noqa: E501
                "The target is a Linux machine. If you find yourself writing Windows services " # noqa: E501
                "(msrpc, microsoft-ds, ms-wbt-server), STOP — you are hallucinating.\n\n" # noqa: E501
                "OUTPUT FORMAT: Valid JSON only with open_ports[] and exploitation_attempts[].\n" # noqa: E501
                "No markdown. No prose. No code fences."
            ),
            expected_output=(
                "A compact JSON object derived exclusively from the provided scanner context, " # noqa: E501
                "with open_ports[] containing only ports that appear in the nmap output." # noqa: E501
            )
        )

        critic_task = Task(
            agent=self.critic,
            context=[summarize_task],
            description=(
                f"Audit all findings for target {self.target}.\n\n"
                "FOR EVERY FINDING IN THE TESTER OUTPUT:\n"
                "1. Verify the IP/hostname matches the target.\n"
                "2. Verify the port and service exist in the scanner output.\n"
                "3. Verify the raw_output is non-empty and non-generic.\n"
                "4. Flag any CVE or exploit name not supported by raw terminal evidence.\n\n" # noqa: E501
                "OUTPUT FORMAT: Return a JSON object with:\n"
                "validated_findings[], rejected_findings[], "
                "hallucination_flags[], overall_confidence_score (0.0-1.0).\n\n"
                "CONSTRAINTS:\n"
                "- Reject any finding where confirmed=true but raw_output is empty or generic.\n" # noqa: E501
                "- A confidence score above 0.7 requires at least one confirmed=true finding " # noqa: E501
                "with non-empty raw_output.\n"
                "- Do not add, infer, or enrich any finding. Only validate or reject."
            ),
            expected_output=(
                "A JSON audit report with validated_findings, rejected_findings, "
                "hallucination_flags, and overall_confidence_score."
            )
        )

        report_task = Task(
            agent=self.reporter,
            context=[plan_task, summarize_task, critic_task],
            description=(
                "Generate the final penetration test report from the validated data.\n\n"  # noqa: E501
                "OUTPUT FORMAT: Return a single valid JSON object with these exact keys:\n"  # noqa: E501
                "- target: string\n"
                f"- use this exact value for scan_date: {_utc_now()}\n"
                "- executive_summary: string, max 3 sentences\n"
                "- findings: array of validated findings from critic output\n"
                "- rejected_findings: array from critic output\n"
                "- recommendations: array of actionable strings\n"
                "- confidence_score: float from critic output\n\n"
                "CONSTRAINTS:\n"
                "- Use only data present in the context. Never add unreported vulnerabilities.\n"  # noqa: E501
                "- If findings is empty, reflect that accurately.\n"
                "- Output must be raw JSON only. No markdown, no prose, no code fences.\n"  # noqa: E501
                "- The output must be directly parseable by json.loads()."
            ),
            expected_output=(
                "A single valid JSON object with target, scan_date, executive_summary, "
                "findings, rejected_findings, recommendations, and confidence_score."
            )
        )

        return [
            plan_task,
            scan_task,
            tester_task,
            summarize_task,
            critic_task,
            report_task,
        ]

    def run(self) -> dict:
        tasks = self._create_tasks()

        talos_crew = Crew(
            tasks=tasks,
            verbose=True,
            memory=False,
            process=Process.sequential,
            agents=[
                self.planner,
                self.scanner,
                self.tester,
                self.summarizer,
                self.critic,
                self.reporter,
            ]
        )

        try:
            result = talos_crew.kickoff()
            return self._extract_json(str(result))
        except json.JSONDecodeError as e:
            return {
                "error": "reporter_json_parse_failed",
                "detail": str(e),
                "raw": str(result),
            }
        except Exception as e:
            return {
                "error": "pipeline_failed",
                "detail": str(e)
            }

    @staticmethod
    def _extract_json(raw: str) -> dict:
        import re
        cleaned = re.sub(r"```json|```", "", raw).strip()
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise ValueError(f"No valid JSON found in reporter output: {raw[:200]}")
