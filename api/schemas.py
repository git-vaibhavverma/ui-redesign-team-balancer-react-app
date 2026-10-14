from __future__ import annotations

from typing import Any, Dict, List
from pydantic import BaseModel, Field


class GenerateMatchRequest(BaseModel):
    player_names: List[str] = Field(min_length=2, description="Selected player names")


class PlayerResponse(BaseModel):
    name: str
    batting: float
    bowling: float
    fielding: float
    is_batsman: bool = False
    is_bowler: bool = False
    strength_score: float
    rank: int


class SessionSnapshot(BaseModel):
    session_id: str
    match_number: int
    players: List[Dict[str, Any]]
    team_a: List[Dict[str, Any]]
    team_b: List[Dict[str, Any]]
    team_a_stats: Dict[str, Any]
    team_b_stats: Dict[str, Any]


class RestoreSessionRequest(BaseModel):
    restore_state: Dict[str, Any] = Field(..., description="Validated session snapshot produced by the API")
