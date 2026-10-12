"""HTTP API for the Prism React frontend.

This layer adapts the existing Python backend; balancing rules stay in backend/.
Run from the repository root with:
    uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
"""
from __future__ import annotations

import os
import sys
import threading
import uuid
from pathlib import Path
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# Ensure imports work when the service is launched from the repository root.
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.player_service import PlayerService  # noqa: E402
from backend.session_manager import CricketSession  # noqa: E402
from backend.team_balancer import player_strength, team_stats  # noqa: E402
from api.schemas import GenerateMatchRequest  # noqa: E402

app = FastAPI(
    title="Prism Cricket Team Balancer API",
    version="0.1.0",
    description="API adapter for the existing Prism team-balancing engine.",
)


def _allowed_origins() -> List[str]:
    configured = os.getenv("FRONTEND_ORIGINS", "")
    origins = [item.strip().rstrip("/") for item in configured.split(",") if item.strip()]
    defaults = ["http://localhost:5173", "http://127.0.0.1:5173"]
    return list(dict.fromkeys(defaults + origins))


app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins(),
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)

# The CSV is located under backend/ in the folder structure the user described.
PLAYERS_CSV = ROOT_DIR / "backend" / "players.csv"
_player_service = PlayerService(str(PLAYERS_CSV))
_master_players: List[Dict[str, Any]] = _player_service.load_master_players()
_sessions: Dict[str, CricketSession] = {}
_session_lock = threading.RLock()


def _score(player: Dict[str, Any]) -> float:
    return float(player_strength(player))


def _player_key(player: Dict[str, Any]) -> tuple:
    return (-_score(player), str(player.get("name", "")).casefold())


def _public_players() -> List[Dict[str, Any]]:
    ranked = sorted(_master_players, key=_player_key)
    results: List[Dict[str, Any]] = []
    for rank, player in enumerate(ranked, start=1):
        item = dict(player)
        item["name"] = str(item["name"])
        item["batting"] = float(item.get("batting", 0) or 0)
        item["bowling"] = float(item.get("bowling", 0) or 0)
        item["fielding"] = float(item.get("fielding", 0) or 0)
        item["is_batsman"] = bool(item.get("is_batsman", False))
        item["is_bowler"] = bool(item.get("is_bowler", False))
        item["strength_score"] = _score(player)
        item["rank"] = rank
        results.append(item)
    return results


def _clean_number(value: Any) -> Any:
    """Convert common scalar numeric types into JSON-friendly Python values."""
    if isinstance(value, (int, float, str, bool)) or value is None:
        return value
    try:
        return float(value)
    except (TypeError, ValueError):
        return str(value)


def _team_stats(team: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not team:
        return {
            "batting": 0.0, "bowling": 0.0, "fielding": 0.0, "strength": 0.0,
            "batsmen": 0, "bowlers": 0, "fielders": 0,
            "elite_batters": 0, "elite_bowlers": 0,
            "strong_batters": 0, "strong_bowlers": 0,
        }
    # Keep these as backend-calculated figures: no frontend threshold calculations.
    raw = team_stats(team)
    return {str(key): _clean_number(value) for key, value in raw.items()}


def _get_session(session_id: str) -> CricketSession:
    session = _sessions.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found. Create a new session and try again.")
    return session


def _snapshot(session_id: str, session: CricketSession) -> Dict[str, Any]:
    current_teams = session.current_teams or {}
    team_a = list(current_teams.get("team_a", []) or [])
    team_b = list(current_teams.get("team_b", []) or [])

    # Add the same presentation fields to master players, selected players, and team
    # members, so PlayerCard receives rank and strength_score in every view.
    ranked_by_name = {player["name"]: player for player in _public_players()}

    def enrich(player: Dict[str, Any]) -> Dict[str, Any]:
        name = str(player.get("name", ""))
        result = dict(ranked_by_name.get(name, {}))
        result.update(dict(player))
        ranked = ranked_by_name.get(name, {})
        result["name"] = name
        result["strength_score"] = float(ranked.get("strength_score", _score(player)))
        result["rank"] = int(ranked.get("rank", 0))
        result["batting"] = float(result.get("batting", 0) or 0)
        result["bowling"] = float(result.get("bowling", 0) or 0)
        result["fielding"] = float(result.get("fielding", 0) or 0)
        result["is_batsman"] = bool(result.get("is_batsman", False))
        result["is_bowler"] = bool(result.get("is_bowler", False))
        return result

    return {
        "session_id": session_id,
        "match_number": int(getattr(session, "match_number", 0) or 0),
        "players": [enrich(player) for player in (getattr(session, "players", []) or [])],
        "team_a": [enrich(player) for player in team_a],
        "team_b": [enrich(player) for player in team_b],
        "team_a_stats": _team_stats(team_a),
        "team_b_stats": _team_stats(team_b),
    }


@app.get("/api/health")
def health() -> Dict[str, str]:
    return {"status": "ok", "service": "prism-api"}


@app.get("/api/players")
def list_players() -> List[Dict[str, Any]]:
    """Return master players ranked by existing player_strength()."""
    return _public_players()


@app.post("/api/sessions")
def create_session() -> Dict[str, Any]:
    session_id = str(uuid.uuid4())
    with _session_lock:
        session = CricketSession()
        _sessions[session_id] = session
        return _snapshot(session_id, session)


@app.get("/api/sessions/{session_id}")
def get_session_snapshot(session_id: str) -> Dict[str, Any]:
    with _session_lock:
        return _snapshot(session_id, _get_session(session_id))


@app.post("/api/sessions/{session_id}/generate-match")
def generate_match(session_id: str, request: GenerateMatchRequest) -> Dict[str, Any]:
    selected_names = list(dict.fromkeys(name.strip() for name in request.player_names if name.strip()))
    if len(selected_names) < 2:
        raise HTTPException(status_code=422, detail="Select at least two players.")

    master_by_name = {str(player["name"]): player for player in _master_players}
    unknown = [name for name in selected_names if name not in master_by_name]
    if unknown:
        raise HTTPException(status_code=422, detail=f"Unknown player name(s): {', '.join(unknown)}")
    selected_players = [master_by_name[name] for name in selected_names]

    with _session_lock:
        session = _get_session(session_id)
        try:
            if int(getattr(session, "match_number", 0) or 0) == 0:
                session.set_initial_players(selected_players)
            else:
                selected_by_name = {str(player["name"]): player for player in selected_players}
                current_by_name = {
                    str(player["name"]): player
                    for player in (getattr(session, "players", []) or [])
                }
                for current_name in list(current_by_name):
                    if current_name not in selected_by_name:
                        session.remove_player(current_name)
                for selected_name, player in selected_by_name.items():
                    if selected_name not in current_by_name:
                        session.add_player(player)
            session.generate_match()
        except Exception as exc:  # Surface a useful API error without leaking a traceback.
            raise HTTPException(status_code=500, detail=f"Could not generate match: {exc}") from exc
        return _snapshot(session_id, session)


@app.post("/api/sessions/{session_id}/reset")
def reset_session(session_id: str) -> Dict[str, Any]:
    with _session_lock:
        if session_id not in _sessions:
            raise HTTPException(status_code=404, detail="Session not found.")
        # Preserve the browser's session ID, but start a fresh CricketSession object.
        _sessions[session_id] = CricketSession()
        return _snapshot(session_id, _sessions[session_id])
