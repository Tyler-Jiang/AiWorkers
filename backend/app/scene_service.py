"""Aggregate scene snapshot + phase / log helpers."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.config import get_settings, resolved_studio_output_dir
from app.models import (
    Agent,
    AgentInvocation,
    Artifact,
    ComputerState,
    EventLog,
    Message,
    Phase,
    StudioMeta,
    Task,
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def pick_current_phase(db: Session) -> Phase | None:
    """进行中的阶段：仅统计未结案状态；已 accepted 的阶段不会作为当前阶段。"""
    return db.execute(
        select(Phase)
        .where(
            Phase.status.in_(
                (
                    "not_started",
                    "needs_confirmation",
                    "active",
                    "waiting_acceptance",
                )
            )
        )
        .order_by(Phase.sort_order)
    ).scalars().first()


def cursor_integration_snapshot() -> dict[str, Any]:
    s = get_settings()
    live = bool(s.cursor_api_key and s.cursor_repository)
    return {
        "mode": "live" if live else "simulation",
        "api_configured": bool(s.cursor_api_key),
        "repository_configured": bool(s.cursor_repository),
        "branch": s.cursor_branch,
    }


def output_project_snapshot() -> dict[str, Any]:
    """小游戏产出目录与本地预览 URL（与控制台 frontend 分离）。"""
    s = get_settings()
    root = resolved_studio_output_dir(s)
    return {
        "preview_url": s.studio_output_preview_url,
        "folder_path": str(root),
        "folder_config": s.studio_output_dir,
        "hint": "在产出目录执行 npm install && npm run dev（默认 5180），办公室内嵌预览与本地 Web 开发一致。",
    }


def studio_meta_snapshot(db: Session) -> dict[str, Any]:
    """Stage D：用户需求与计划进度（供 GET /api/scene）。"""
    meta = db.get(StudioMeta, 1)
    req = meta.requirement_text if meta else None
    preview = None
    if req:
        preview = req if len(req) <= 160 else req[:157] + "..."
    return {
        "requirement_submitted": bool(req),
        "requirement_preview": preview,
        "clarification_answered": bool(meta and meta.clarification_answered),
        "plan_generated": bool(meta and meta.plan_generated),
    }


def add_event_log(db: Session, level: str, message: str) -> None:
    db.add(
        EventLog(level=level, message=message, created_at=_utc_now()),
    )


def build_scene(db: Session) -> dict[str, Any]:
    agents = db.execute(select(Agent).order_by(Agent.id)).scalars().all()
    comp = db.get(ComputerState, 1)
    if not comp:
        comp = ComputerState(id=1, holder_agent_id=None, queue_json="[]")
        db.add(comp)
        db.commit()
        db.refresh(comp)

    try:
        queue: list[str] = json.loads(comp.queue_json or "[]")
    except json.JSONDecodeError:
        queue = []

    phase = pick_current_phase(db)
    tasks_rows: list[Task] = []
    if phase:
        tasks_rows = db.execute(
            select(Task).where(Task.phase_id == phase.id).order_by(Task.sort_order)
        ).scalars().all()

    tasks_out = [
        {
            "id": t.id,
            "title": t.title,
            "owner_agent_id": t.owner_agent_id,
            "status": t.status,
        }
        for t in tasks_rows
    ]

    current_phase: dict[str, str] = {
        "id": phase.id if phase else "—",
        "title": phase.title if phase else "—",
        "status": phase.status if phase else "not_started",
    }

    messages = db.execute(
        select(Message).order_by(Message.id.desc()).limit(40)
    ).scalars().all()
    latest_messages = [
        {
            "id": m.id,
            "from_agent": m.from_agent,
            "to_agent": m.to_agent,
            "type": m.msg_type,
            "body": m.body,
            "created_at": m.created_at,
        }
        for m in reversed(messages)
    ]

    logs = db.execute(select(EventLog).order_by(EventLog.id.desc()).limit(60)).scalars().all()
    event_logs = [{"level": e.level, "message": e.message} for e in reversed(logs)]

    arts = db.execute(select(Artifact).order_by(Artifact.id.desc()).limit(20)).scalars().all()
    artifacts_summary = [{"label": a.label, "detail": a.detail} for a in arts]

    inv_rows = db.execute(
        select(AgentInvocation).order_by(desc(AgentInvocation.created_at)).limit(12)
    ).scalars().all()
    agent_invocations = [
        {
            "id": inv.id,
            "agent_id": inv.agent_id,
            "status": inv.status,
            "external_ref": inv.external_ref,
            "prompt_summary": inv.prompt_summary[:200]
            + ("…" if len(inv.prompt_summary) > 200 else ""),
            "created_at": inv.created_at,
        }
        for inv in inv_rows
    ]

    return {
        "agents": [
            {"id": a.id, "name": a.name, "role": a.role, "state": a.state}
            for a in agents
        ],
        "computer_lock": {
            "holder_agent_id": comp.holder_agent_id,
            "queue": queue,
        },
        "blackboard": {
            "phase": phase.id if phase else "not_started",
            "tasks": tasks_out,
        },
        "latest_messages": latest_messages,
        "event_logs": event_logs,
        "current_phase": current_phase,
        "artifacts_summary": artifacts_summary,
        "studio_meta": studio_meta_snapshot(db),
        "agent_invocations": agent_invocations,
        "cursor_integration": cursor_integration_snapshot(),
        "output_project": output_project_snapshot(),
    }


def approve_phase(db: Session, phase_id: str) -> Phase:
    p = db.get(Phase, phase_id)
    if not p:
        raise HTTPException(status_code=404, detail="phase not found")
    before = p.status
    if p.status == "needs_confirmation":
        p.status = "active"
    elif p.status == "waiting_acceptance":
        p.status = "accepted"
    if before != p.status:
        add_event_log(
            db,
            "info",
            f"阶段「{p.title}」批准：{before} → {p.status}",
        )
    db.commit()
    db.refresh(p)
    return p


def reject_phase(db: Session, phase_id: str, reason: str | None) -> Phase:
    p = db.get(Phase, phase_id)
    if not p:
        raise HTTPException(status_code=404, detail="phase not found")
    p.status = "rejected"
    add_event_log(
        db,
        "warning",
        f"阶段「{p.title}」已驳回：{reason or '无原因'}",
    )
    db.commit()
    db.refresh(p)
    return p


def set_computer_lock(
    db: Session,
    holder_agent_id: str | None,
    queue: list[str] | None = None,
) -> ComputerState:
    comp = db.get(ComputerState, 1)
    if not comp:
        comp = ComputerState(id=1)
        db.add(comp)
    if holder_agent_id is not None:
        comp.holder_agent_id = holder_agent_id
    if queue is not None:
        comp.queue_json = json.dumps(queue)
    db.commit()
    db.refresh(comp)
    return comp


def _computer_row(db: Session) -> ComputerState:
    comp = db.get(ComputerState, 1)
    if not comp:
        comp = ComputerState(id=1, holder_agent_id=None, queue_json="[]")
        db.add(comp)
        db.commit()
        db.refresh(comp)
    return comp


def _queue_list(comp: ComputerState) -> list[str]:
    try:
        return list(json.loads(comp.queue_json or "[]"))
    except json.JSONDecodeError:
        return []


def request_computer(db: Session, agent_id: str) -> dict[str, Any]:
    """Developer 申请共享工作站：空闲则占用，否则入队（Stage F）。"""
    if agent_id != "developer":
        raise HTTPException(status_code=400, detail="仅 developer 可申请共享工作站")
    comp = _computer_row(db)
    queue = _queue_list(comp)

    if comp.holder_agent_id == agent_id:
        add_event_log(db, "info", "Developer 已持有工作站")
        db.commit()
        return {"ok": True, "status": "holding"}

    if comp.holder_agent_id is None:
        comp.holder_agent_id = agent_id
        add_event_log(db, "info", "Developer 已占用共享工作站")
        db.commit()
        return {"ok": True, "status": "acquired"}

    if agent_id not in queue:
        queue.append(agent_id)
        comp.queue_json = json.dumps(queue)
        add_event_log(db, "info", f"Developer 已加入工作站队列（排队 {len(queue)}）")
    else:
        add_event_log(db, "info", "Developer 已在队列中")
    db.commit()
    pos = queue.index(agent_id) + 1 if agent_id in queue else 0
    return {"ok": True, "status": "queued", "queue_position": pos}


def release_computer(db: Session, agent_id: str) -> dict[str, Any]:
    """占用者释放工作站；若队列有人则顺位继承（Stage F）。"""
    comp = _computer_row(db)
    if comp.holder_agent_id != agent_id:
        raise HTTPException(status_code=409, detail="当前未持有工作站，无法释放")

    queue = _queue_list(comp)
    nxt: str | None = queue.pop(0) if queue else None
    comp.queue_json = json.dumps(queue)
    comp.holder_agent_id = nxt

    if nxt:
        add_event_log(db, "info", f"工作站已交给队列下一顺位：{nxt}")
    else:
        add_event_log(db, "info", "Developer 已释放共享工作站")
    db.commit()
    return {"ok": True, "status": "released", "new_holder": nxt}
