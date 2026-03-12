AGENT_CONFIGS = {
    "planner": {
        "model": "deepseek-r1:14b",
        "system_prompt": "You are the Architect. Plan the attack.",
        "options": {"temperature": 0.6, "num_ctx": 8192}
    },
    "scanner": {
        "model": "Lily-Cybersecurity-7B:latest",
        "system_prompt": "You are the Scout. Generate CLI commands.",
        "options": {"temperature": 0.0}
    },
    "tester": {
        "model": "White-Rabbit-Neo-13B:latest",
        "system_prompt": "You are the Infiltrator. Brainstorm exploits.",
        "options": {"temperature": 0.8}
    },
    "reporter": {
        "model": "mistral-nemo:12b",
        "system_prompt": "You are the Reporter. Output valid JSON.",
        "options": {"temperature": 0.3}
    }
}
