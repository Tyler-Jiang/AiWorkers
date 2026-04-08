"""Cursor Cloud Agents 调用与模拟模式（Stage E）。"""

from __future__ import annotations

import base64
import json
import uuid
from typing import Any

import httpx
from fastapi import HTTPException
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.agent_prompts import ALLOWED_AGENT_IDS, OUTPUT_FORMAT_HINT, ROLE_PROMPTS
from app.config import get_settings
from app.models import AgentInvocation, Message
from app.scene_service import add_event_log, build_scene, release_computer, studio_meta_snapshot


def _utc_now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _add_agent_message(
    db: Session,
    *,
    from_agent: str,
    body: str,
    msg_type: str = "result",
) -> None:
    db.add(
        Message(
            from_agent=from_agent,
            to_agent="user",
            msg_type=msg_type,
            body=body,
            created_at=_utc_now(),
        )
    )


def build_full_prompt(
    agent_id: str,
    prompt_extra: str,
    *,
    computer_granted: bool,
    scene: dict[str, Any] | None,
) -> str:
    base = ROLE_PROMPTS.get(agent_id, "")
    ctx = ""
    if scene:
        ctx = json.dumps(
            {
                "studio_meta": scene.get("studio_meta"),
                "current_phase": scene.get("current_phase"),
                "computer_lock": scene.get("computer_lock"),
                "output_project": scene.get("output_project"),
            },
            ensure_ascii=False,
        )[:8000]
    lock_line = (
        "电脑锁状态：已授予 Developer，可执行仓库写入。"
        if computer_granted and agent_id == "developer"
        else "电脑锁状态：未授予代码写入；非 Developer 或非授权时不要改代码。"
    )
    parts = [
        base,
        OUTPUT_FORMAT_HINT,
        lock_line,
        f"附加说明：{prompt_extra}" if prompt_extra.strip() else "",
        f"当前场景摘要（JSON 片段）：{ctx}" if ctx else "",
    ]
    return "\n\n".join(p for p in parts if p)


def _extract_external_id(data: dict[str, Any]) -> str | None:
    if not data:
        return None
    for key in ("id", "agentId", "runId"):
        v = data.get(key)
        if isinstance(v, str):
            return v
    run = data.get("run")
    if isinstance(run, dict) and isinstance(run.get("id"), str):
        return run["id"]
    return None


def invoke_agent(
    db: Session,
    agent_id: str,
    prompt_extra: str,
    *,
    computer_granted: bool,
) -> dict[str, Any]:
    if agent_id not in ALLOWED_AGENT_IDS:
        raise HTTPException(status_code=400, detail="unknown agent_id")

    scene = build_scene(db)
    if agent_id == "developer" and computer_granted:
        holder = (scene.get("computer_lock") or {}).get("holder_agent_id")
        if holder != "developer":
            raise HTTPException(
                status_code=409,
                detail="需要写入代码时请先在控制台申请并占用共享工作站（Developer）",
            )

    full_prompt = build_full_prompt(
        agent_id,
        prompt_extra,
        computer_granted=computer_granted,
        scene=scene,
    )
    inv_id = uuid.uuid4().hex[:24]
    now = _utc_now()
    row = AgentInvocation(
        id=inv_id,
        agent_id=agent_id,
        status="pending",
        external_ref=None,
        prompt_summary=full_prompt[:2000],
        last_error=None,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    settings = get_settings()
    use_live = bool(
        settings.cursor_api_key and settings.cursor_repository and settings.cursor_api_base
    )

    if not use_live:
        row.status = "simulated"
        row.updated_at = _utc_now()
        _add_agent_message(
            db,
            from_agent=agent_id,
            msg_type="result",
            body=(
                "[模拟模式] 已记录调用。请在 backend/.env 配置 CURSOR_API_KEY 与 "
                "CURSOR_REPOSITORY（GitHub owner/repo）后重试，以连接真实 Cloud Agent。"
            ),
        )
        add_event_log(
            db,
            "info",
            f"Agent「{agent_id}」模拟调用完成（invocation={inv_id}）。",
        )
        if agent_id == "developer" and computer_granted:
            try:
                release_computer(db, "developer")
            except HTTPException:
                pass
        db.commit()
        db.refresh(row)
        return {
            "invocation_id": inv_id,
            "status": row.status,
            "external_ref": None,
            "mode": "simulation",
        }

    url = f"{settings.cursor_api_base.rstrip('/')}/v0/agents"
    basic = base64.b64encode(f"{settings.cursor_api_key}:".encode()).decode()
    headers = {
        "Authorization": f"Basic {basic}",
        "Content-Type": "application/json",
    }
    payload: dict[str, Any] = {
        "source": {
            "repository": settings.cursor_repository,
            "ref": settings.cursor_branch,
        },
        "prompt": {"text": full_prompt},
    }

    try:
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(url, headers=headers, json=payload)
        try:
            data = resp.json() if resp.content else {}
        except Exception:  # noqa: BLE001
            data = {"_parse_error": True, "_text": resp.text[:800]}
    except Exception as e:  # noqa: BLE001
        row.status = "failed"
        row.last_error = str(e)[:2000]
        row.updated_at = _utc_now()
        add_event_log(db, "error", f"Cursor API 请求异常：{e!s}")
        db.commit()
        return {
            "invocation_id": inv_id,
            "status": "failed",
            "external_ref": None,
            "mode": "live",
            "error": row.last_error,
        }

    if resp.status_code >= 400:
        row.status = "failed"
        row.last_error = (data.get("message") if isinstance(data, dict) else None) or resp.text[
            :2000
        ]
        row.updated_at = _utc_now()
        add_event_log(
            db,
            "error",
            f"Cursor API HTTP {resp.status_code}：{row.last_error}",
        )
        db.commit()
        return {
            "invocation_id": inv_id,
            "status": "failed",
            "external_ref": None,
            "mode": "live",
            "error": row.last_error,
        }

    ext = _extract_external_id(data) if isinstance(data, dict) else None
    row.status = "dispatched"
    row.external_ref = ext
    row.updated_at = _utc_now()
    add_event_log(
        db,
        "info",
        f"Cursor Agent 已派发：agent={agent_id} invocation={inv_id} external={ext}",
    )
    db.commit()
    db.refresh(row)
    preview: dict[str, Any] | None = None
    if isinstance(data, dict):
        preview = dict(list(data.items())[:12])
    return {
        "invocation_id": inv_id,
        "status": row.status,
        "external_ref": ext,
        "mode": "live",
        "response_preview": preview,
    }


def list_invocations(db: Session, limit: int = 20) -> list[dict[str, Any]]:
    rows = db.execute(
        select(AgentInvocation).order_by(desc(AgentInvocation.created_at)).limit(limit)
    ).scalars().all()
    return [
        {
            "id": r.id,
            "agent_id": r.agent_id,
            "status": r.status,
            "external_ref": r.external_ref,
            "prompt_summary": r.prompt_summary[:240] + ("…" if len(r.prompt_summary) > 240 else ""),
            "last_error": r.last_error,
            "created_at": r.created_at,
            "updated_at": r.updated_at,
        }
        for r in rows
    ]


def apply_webhook_payload(db: Session, payload: dict[str, Any]) -> None:
    """根据 webhook 体尽量更新 invocation 状态（兼容多种字段名）。"""
    add_event_log(
        db,
        "info",
        f"[webhook/cursor] 收到 payload 键：{list(payload.keys())[:20]}",
    )
    ext = (
        payload.get("external_ref")
        or payload.get("agent_id")
        or payload.get("id")
        or payload.get("runId")
    )
    if isinstance(payload.get("data"), dict):
        d = payload["data"]
        ext = ext or d.get("id") or d.get("agentId")

    if not ext or not isinstance(ext, str):
        db.commit()
        return

    row = db.execute(
        select(AgentInvocation).where(AgentInvocation.external_ref == ext)
    ).scalars().first()
    if not row:
        db.commit()
        return

    st = payload.get("status") or payload.get("state")
    if isinstance(st, str):
        if st.lower() in ("completed", "success", "done"):
            row.status = "completed"
        elif st.lower() in ("failed", "error"):
            row.status = "failed"
    row.updated_at = _utc_now()
    add_event_log(
        db,
        "info",
        f"Webhook 更新 invocation {row.id} → {row.status}",
    )
    db.commit()
