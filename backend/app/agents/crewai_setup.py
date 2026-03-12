from crewai import Agent, Crew, Process, Task
from langchain_community.llms import Ollama

from app.core.config import settings

ollama_lily = Ollama(
    model="Lily-Cybersecurity-7B:latest",
    base_url=settings.OLLAMA_BASE_URL
    )

scanner_agent = Agent(
    role='Lead Recon Specialist',
    goal='Map the entire attack surface of {target}',
    backstory='An elite network scout specializing in stealthy Nmap discovery.',
    llm=ollama_lily,
    allow_delegation=False
)

scan_task = Task(
    description='Perform a full service discovery on {target} and list versions.',
    expected_output='A structured list of ports, services, and versions.',
    agent=scanner_agent
)

pentest_crew = Crew(
    agents=[scanner_agent],
    tasks=[scan_task],
    process=Process.sequential
)

result = pentest_crew.kickoff(inputs={'target': '192.168.1.10'})
