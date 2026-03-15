import docker
from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class TerminalInput(BaseModel):
    command: str = Field(
        ...,
        description="The full bash command to run inside the Kali container."
    )

class KaliTerminalTool(BaseTool):
    name: str = "kali_terminal"
    description: str = """
    Run ANY command inside the Kali Linux container.
    Use this for scanning and exploitation, using any security tool."""
    args_schema: type[BaseModel] = TerminalInput

    def _run(self, command: str) -> str:
        try:
            client = docker.from_env()
            kali = client.containers.get("talos_kali")

            result = kali.exec_run(command)
            output = result.output.decode()

            return output if output else "Command executed successfully (no output)."
        except Exception as e:
            return f"Error executing command: {str(e)}"

kali_tool = KaliTerminalTool()
