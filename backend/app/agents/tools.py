import docker
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

# Hard cap per command: a tool that never returns (e.g. msfconsole holding an
# open session) would otherwise block the worker forever and make cancel/resume
# ineffective. `timeout` kills it, exec_run returns, and the worker unblocks.
CMD_TIMEOUT_SECONDS = 180
_TIMEOUT_EXIT_CODES = (124, 137)  # 124 = TERM on timeout, 137 = 128+9 (SIGKILL via -k)

KALI_CONTAINER = "talos_kali"

# --- Cached Docker client + container handles -------------------------------
# docker.from_env() opens a socket and containers.get() is a round-trip to the
# daemon; doing both on every command added real latency to a mission that runs
# dozens of commands. We cache the client and the container handle at module
# scope and reconnect defensively: when a container is restarted/recreated its
# id changes, so a cached handle starts raising NotFound — we drop the cache and
# re-resolve by name once (see `_reset`).
_client = None
_containers: dict[str, "docker.models.containers.Container"] = {}


def _get_client():
    global _client
    if _client is None:
        _client = docker.from_env()
    return _client


def _reset() -> None:
    """Drop cached client + container handles so the next call reconnects fresh."""
    global _client
    _client = None
    _containers.clear()


def _get_container(name: str):
    container = _containers.get(name)
    if container is None:
        container = _get_client().containers.get(name)
        _containers[name] = container
    return container


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

    def _exec(self, command: str) -> str:
        """Single exec attempt against the (possibly cached) container handle."""
        kali = _get_container(KALI_CONTAINER)
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

    def _run(self, command: str) -> str:
        try:
            return self._exec(command)
        except (docker.errors.NotFound, docker.errors.APIError):
            # Stale container id (restart/recreate) or a dropped socket: drop the
            # cache and retry exactly once against a freshly resolved handle.
            _reset()
            try:
                return self._exec(command)
            except docker.errors.NotFound:
                return (
                    f"Error: {KALI_CONTAINER} container not found. Is it running?"
                )
            except docker.errors.APIError as e:
                return f"Docker API error: {str(e)}"
            except Exception as e:  # noqa: BLE001
                return f"Error executing command: {str(e)}"
        except Exception as e:  # noqa: BLE001
            return f"Error executing command: {str(e)}"


def kali_lhost() -> str | None:
    """Kali's current IP on the target network — the correct LHOST for reverse
    shells. Resolved live (the cached handle is reload()ed) so it's always right
    even if Docker reassigns the address across restarts."""

    def _read() -> str | None:
        kali = _get_container(KALI_CONTAINER)
        kali.reload()  # refresh NetworkSettings on the cached handle
        nets = kali.attrs["NetworkSettings"]["Networks"]
        net = nets.get("talos_network") or next(iter(nets.values()), None)
        return net.get("IPAddress") if net else None

    try:
        return _read()
    except docker.errors.NotFound:
        _reset()
        try:
            return _read()
        except Exception:
            return None
    except Exception:
        return None


kali_tool = KaliTerminalTool()
