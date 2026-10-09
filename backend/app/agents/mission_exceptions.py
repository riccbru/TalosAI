class MissionCancelled(Exception):
    """Raised at a checkpoint when a stop has been requested for the mission.

    Lives in its own dependency-free module so the runner and the fake engine
    can import it without pulling in the Gemini/CrewAI stack.
    """
