import docker
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

# Hard cap per command: a tool that never returns (e.g. msfconsole holding an
# open session) would otherwise block the worker forever and make cancel/resume
# ineffective. `timeout` kills it, exec_run returns, and the worker unblocks.
CMD_TIMEOUT_SECONDS = 180
_TIMEOUT_EXIT_CODES = (124, 137)  # 124 = TERM on timeout, 137 = 128+9 (SIGKILL via -k)


class TerminalInput(BaseModel):
    command: str = Field(
        ..., description="The full bash command to run inside the Kali container."
    )


class KaliTerminalTool(BaseTool):
    name: str = "kali_terminal"
    args_schema: type[BaseModel] = TerminalInput
    description: str = (
        "Run ANY bash command inside the Kali Linux container. "
        "Use this for nmap, searchsploit, netcat, nikto, curl, and all security tools. "
        "To use this tool, set Action to 'kali_terminal' and Action Input to a JSON "
        "object with a single key 'command' containing the bash command string. "
        'Example: Action Input: {"command": "nmap -sV 172.21.0.2"} '
        'Example: Action Input: {"command": "searchsploit vsftpd 2.3.4"} '
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
                cmd=[
                    "timeout", "-k", "10", str(CMD_TIMEOUT_SECONDS),
                    "bash", "-c", command,
                ],
            )
            stdout = result.output[0].decode(errors="replace") if result.output[0] else ""
            stderr = result.output[1].decode(errors="replace") if result.output[1] else ""
            output = (stdout + stderr).strip()

            if result.exit_code in _TIMEOUT_EXIT_CODES:
                note = (
                    f"[TALOSAI] Command killed after exceeding "
                    f"{CMD_TIMEOUT_SECONDS}s timeout."
                )
                output = f"{output}\n\n{note}" if output else note

            return output if output else "Command returned no output."
        except docker.errors.NotFound:
            return "Error: talos_kali container not found. Is it running?"
        except docker.errors.APIError as e:
            return f"Docker API error: {str(e)}"
        except Exception as e:
            return f"Error executing command: {str(e)}"


kali_tool = KaliTerminalTool()
