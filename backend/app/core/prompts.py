"""Shared prompt building blocks distilled from HybridOrchestratorV2.

V2 is the reference implementation and is intentionally NOT modified. These
constants capture the command/exploitation discipline it encodes in its manager
prompt, so LocalOrchestrator and HybridOrchestratorV1 can share the exact same
guidance (non-interactive self-terminating commands, the msfconsole shape, the
whoami/id/uname -a proof clause, evidence-based confirmation).

Keep PROOF_COMMANDS in sync with HybridOrchestratorV2._PROOF_COMMANDS.
"""

# Proof-of-exploitation commands, in order.
PROOF_COMMANDS = ("whoami", "id", "uname -a")

EXPLOITATION_PLAYBOOK = (
    "COMMAND & EXPLOITATION RULES (non-negotiable):\n"
    "- Every command MUST be non-interactive and self-terminating: it must NEVER "
    "leave an open shell or console, or the run hangs.\n"
    "- Prefer Metasploit or target-specific automated tools over raw .py/.rb "
    "exploitdb scripts.\n"
    "- For Metasploit, use exactly this shape:\n"
    "  msfconsole -q -x \"use <module>; set RHOSTS <ip>; set RPORT <port>; "
    "<other options>; run -z; sessions -c whoami; sessions -c id; "
    "sessions -c 'uname -a'; exit -y\"\n"
    "    * 'run -z' backgrounds the session instead of dropping into an "
    "interactive shell.\n"
    "    * the proof clause runs whoami, id and 'uname -a' (single-quote any "
    "multi-token command) on the opened session, one 'sessions -c' per command.\n"
    "    * always finish with 'exit -y' so msfconsole quits.\n"
    "- Do NOT hardcode a payload name; let Metasploit use the module default, or "
    "prefer a Meterpreter payload for reliable interactive proof. Do not hardcode "
    "LHOST unless the module requires it.\n"
    "- A finding is CONFIRMED only on real execution evidence (e.g. 'uid=0(root)' "
    "from id, or 'session opened'). If the proof clause is silent, treat it as "
    "unconfirmed.\n"
    "- On failure (no session, timeout, silent failure), retry a DIFFERENT module "
    "or payload before moving on; do not give up after a single attempt.\n"
)
