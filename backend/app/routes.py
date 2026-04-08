"""HTTP API：场景聚合、黑板、日志、电脑锁、阶段与占位命令。"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.agent_manager import apply_webhook_payload, invoke_agent, list_invocations
from app.config import get_settings
from app.db import get_db
from app.producer_flow import (
    producer_clarify,
    producer_generate_plan,
    submit_requirement,
    user_reply,
)
from app.scene_service import (
    add_event_log,
    approve_phase,
    build_scene,
    reject_phase,
    release_computer,
    request_computer,
)

router = APIRouter()


@router.get("/ping")
def ping() -> dict[str, Any]:
    """健康探测（与 /health 区分：走 /api 前缀，便于验证 Vite 代理是否生效）。"""
    return {"ok": True, "service": "ai-game-studio"}


@router.get("/scene")
def get_scene(db: Session = Depends(get_db)) -> dict[str, Any]:
    return build_scene(db)


@router.get("/blackboard")
def get_blackboard(db: Session = Depends(get_db)) -> dict[str, Any]:
    s = build_scene(db)
    return {
        "phase_key": s["blackboard"]["phase"],
        "tasks": s["blackboard"]["tasks"],
        "current_phase": s["current_phase"],
    }


@router.get("/message-board")
def get_message_board(db: Session = Depends(get_db)) -> dict[str, Any]:
    return {"messages": build_scene(db)["latest_messages"]}


@router.get("/logs")
def get_logs(db: Session = Depends(get_db)) -> dict[str, Any]:
    return {"logs": build_scene(db)["event_logs"]}


@router.get("/computer-lock")
def get_computer_lock(db: Session = Depends(get_db)) -> dict[str, Any]:
    return build_scene(db)["computer_lock"]


class ComputerAgentBody(BaseModel):
    agent_id: str = Field(..., min_length=2, max_length=64, description="通常为 developer")


@router.post("/computer/request")
def post_computer_request(
    body: ComputerAgentBody,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    extra = request_computer(db, body.agent_id)
    return {**extra, "scene": build_scene(db)}


@router.post("/computer/release")
def post_computer_release(
    body: ComputerAgentBody,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    extra = release_computer(db, body.agent_id)
    return {**extra, "scene": build_scene(db)}


class RejectBody(BaseModel):
    reason: str | None = Field(default=None, description="驳回原因")


@router.post("/phases/{phase_id}/approve")
def post_phase_approve(phase_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    approve_phase(db, phase_id)
    return {"ok": True, "scene": build_scene(db)}


@router.post("/phases/{phase_id}/reject")
def post_phase_reject(
    phase_id: str,
    body: RejectBody | None = None,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    reject_phase(db, phase_id, body.reason if body else None)
    return {"ok": True, "scene": build_scene(db)}


class CommandBody(BaseModel):
    command: str
    payload: dict[str, Any] | None = None


@router.post("/command/global")
def post_command_global(
    body: CommandBody,
    db: Session = Depends(get_db),
) -> dict[str, bool]:
    add_event_log(
        db,
        "info",
        f"[global] {body.command} payload={body.payload!r}",
    )
    db.commit()
    return {"ok": True}


@router.post("/command/agent/{agent_id}")
def post_command_agent(
    agent_id: str,
    body: CommandBody,
    db: Session = Depends(get_db),
) -> dict[str, bool]:
    add_event_log(
        db,
        "info",
        f"[agent:{agent_id}] {body.command} payload={body.payload!r}",
    )
    db.commit()
    return {"ok": True}


@router.post("/webhooks/cursor")
async def post_webhook_cursor(
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, bool]:
    s = get_settings()
    if s.cursor_webhook_secret:
        if request.headers.get("X-Studio-Webhook-Secret") != s.cursor_webhook_secret:
            raise HTTPException(status_code=401, detail="invalid webhook secret")
    try:
        payload = await request.json()
    except Exception:  # noqa: BLE001
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    apply_webhook_payload(db, payload)
    return {"received": True}


class RequirementBody(BaseModel):
    text: str = Field(..., min_length=3, max_length=8000)


class UserReplyBody(BaseModel):
    text: str = Field(..., min_length=1, max_length=8000)


@router.post("/requirements")
def post_requirement(
    body: RequirementBody,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    submit_requirement(db, body.text)
    return {"ok": True, "scene": build_scene(db)}


@router.post("/conversation/user-reply")
def post_user_reply(
    body: UserReplyBody,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    user_reply(db, body.text)
    return {"ok": True, "scene": build_scene(db)}


@router.post("/producer/clarify")
def post_producer_clarify(db: Session = Depends(get_db)) -> dict[str, Any]:
    producer_clarify(db)
    return {"ok": True, "scene": build_scene(db)}


@router.post("/producer/generate-plan")
def post_producer_generate_plan(db: Session = Depends(get_db)) -> dict[str, Any]:
    producer_generate_plan(db)
    return {"ok": True, "scene": build_scene(db)}


class InvokeBody(BaseModel):
    prompt_extra: str = ""
    computer_granted: bool = False


@router.post("/agents/{agent_id}/invoke")
def post_agent_invoke(
    agent_id: str,
    body: InvokeBody,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    out = invoke_agent(
        db,
        agent_id,
        body.prompt_extra,
        computer_granted=body.computer_granted,
    )
    return {"ok": True, "scene": build_scene(db), **out}


@router.get("/agents/invocations")
def get_agent_invocations(db: Session = Depends(get_db)) -> dict[str, Any]:
    return {"items": list_invocations(db)}


@router.get("/integrations/cursor")
def get_cursor_integration() -> dict[str, Any]:
    s = get_settings()
    live = bool(s.cursor_api_key and s.cursor_repository)
    return {
        "api_configured": bool(s.cursor_api_key),
        "repository_configured": bool(s.cursor_repository),
        "branch": s.cursor_branch,
        "mode": "live" if live else "simulation",
    }
