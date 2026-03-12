from typing import Any, Dict, List

from pydantic import BaseModel


class MissionBlackboard(BaseModel):
    target: str
    plan: str = ""
    scan_results: List[str] = []
    exploit_suggestions: List[str] = []
    final_json: Dict[str, Any] = {}
