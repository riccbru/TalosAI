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
    args_schema: type[BaseModel] = TerminalInput
    description: str = (
        "Run ANY bash command inside the Kali Linux container. "
        "Use this for nmap, searchsploit, netcat, nikto, curl, and all security tools. "
        "To use this tool, set Action to 'kali_terminal' and Action Input to a JSON "
        "object with a single key 'command' containing the bash command string. "
        "Example: Action Input: {\"command\": \"nmap -sV 172.21.0.2\"} "
        "Example: Action Input: {\"command\": \"searchsploit vsftpd 2.3.4\"} "
        "NEVER put the command itself as the Action name. "
        "ALWAYS use 'kali_terminal' as the Action and put the command in Action Input."
    )

    def _run(self, command: str) -> str:
        try:
            client = docker.from_env()
            kali = client.containers.get("talos_kali")

            result = kali.exec_run(
                tty=False,
                demux=True,
                stdin=False,
                cmd=["bash", "-c", command],
            )
            stdout = result.output[0].decode() if result.output[0] else ""
            stderr = result.output[1].decode() if result.output[1] else ""
            output = stdout + stderr

            return output.strip() if output.strip() else "Command returned no output."
        except docker.errors.NotFound:
            return "Error: talos_kali container not found. Is it running?"
        except docker.errors.APIError as e:
            return f"Docker API error: {str(e)}"
        except Exception as e:
            return f"Error executing command: {str(e)}"

kali_tool = KaliTerminalTool()
