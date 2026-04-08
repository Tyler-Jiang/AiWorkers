"""Stage D：用户 ↔ Producer 需求、澄清与阶段计划（本地规则，不接云端 Agent）。"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Agent, Message, Phase, StudioMeta, Task
from app.scene_service import add_event_log


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def get_or_create_meta(db: Session) -> StudioMeta:
    m = db.get(StudioMeta, 1)
    if not m:
        m = StudioMeta(id=1)
        db.add(m)
        db.commit()
        db.refresh(m)
    return m


def _set_agent_state(db: Session, agent_id: str, state: str) -> None:
    a = db.get(Agent, agent_id)
    if a:
        a.state = state


def _add_message(
    db: Session,
    *,
    from_agent: str,
    to_agent: str | None,
    msg_type: str,
    body: str,
) -> None:
    db.add(
        Message(
            from_agent=from_agent,
            to_agent=to_agent,
            msg_type=msg_type,
            body=body,
            created_at=_utc_now(),
        )
    )


# 模板澄清（可多次由 /producer/clarify 触发）
_CLARIFY_TEMPLATES = [
    "关于目标平台与交付时间：是否有必须满足的截止日期，或仅支持桌面浏览器即可？",
    "玩法上除了点击攒资源与升级，是否需要本地存档、排行榜或音效？",
]


def submit_requirement(db: Session, text: str) -> dict[str, Any]:
    t = re.sub(r"\s+", " ", text.strip())
    if len(t) < 3:
        raise HTTPException(status_code=400, detail="需求至少 3 个字符")
    if len(t) > 8000:
        raise HTTPException(status_code=400, detail="需求过长")

    meta = get_or_create_meta(db)
    if meta.plan_generated:
        raise HTTPException(
            status_code=409,
            detail="阶段计划已生成，无法再次提交需求（演示版限制）。",
        )

    meta.requirement_text = t
    meta.clarification_answered = False

    _add_message(
        db,
        from_agent="user",
        to_agent="producer",
        msg_type="handoff",
        body=f"【用户需求】{t}",
    )
    q = _CLARIFY_TEMPLATES[0]
    _add_message(
        db,
        from_agent="producer",
        to_agent="user",
        msg_type="question",
        body=q,
    )

    _set_agent_state(db, "producer", "discussing")
    add_event_log(db, "info", "用户已提交需求，制作人已发起澄清（模板）。")
    db.commit()
    return {"ok": True}


def user_reply(db: Session, text: str) -> dict[str, Any]:
    t = text.strip()
    if len(t) < 1:
        raise HTTPException(status_code=400, detail="回复不能为空")
    if len(t) > 8000:
        raise HTTPException(status_code=400, detail="回复过长")

    meta = get_or_create_meta(db)
    if not meta.requirement_text:
        raise HTTPException(status_code=400, detail="请先提交需求")

    _add_message(
        db,
        from_agent="user",
        to_agent="producer",
        msg_type="status",
        body=t,
    )
    meta.clarification_answered = True
    add_event_log(db, "info", "用户已回复制作人澄清。")
    db.commit()
    return {"ok": True}


def producer_clarify(db: Session) -> dict[str, Any]:
    """制作人再发一条澄清（轮换模板）。"""
    meta = get_or_create_meta(db)
    if not meta.requirement_text:
        raise HTTPException(status_code=400, detail="请先提交需求")
    if meta.plan_generated:
        raise HTTPException(status_code=409, detail="阶段计划已生成，无需再澄清")

    n = (
        db.scalar(
            select(func.count()).select_from(Message).where(Message.from_agent == "producer")
        )
        or 0
    )
    idx = int(n) % len(_CLARIFY_TEMPLATES)
    body = _CLARIFY_TEMPLATES[idx]
    _add_message(
        db,
        from_agent="producer",
        to_agent="user",
        msg_type="question",
        body=body,
    )
    meta.clarification_answered = False
    _set_agent_state(db, "producer", "discussing")
    add_event_log(db, "info", "制作人追加澄清问题。")
    db.commit()
    return {"ok": True}


def producer_generate_plan(db: Session) -> dict[str, Any]:
    meta = get_or_create_meta(db)
    if not meta.requirement_text:
        raise HTTPException(status_code=400, detail="请先提交需求")
    if not meta.clarification_answered:
        raise HTTPException(status_code=400, detail="请先回复制作人的澄清问题")
    if meta.plan_generated:
        raise HTTPException(status_code=409, detail="阶段计划已生成，勿重复提交")

    if db.get(Phase, "clicker_mvp"):
        raise HTTPException(status_code=409, detail="阶段 clicker_mvp 已存在")

    boot = db.get(Phase, "bootstrap")
    if boot and boot.status in ("needs_confirmation", "not_started"):
        boot.status = "accepted"
        add_event_log(
            db,
            "info",
            "工程骨架阶段已随交付计划一并记为验收（避免与交付阶段并行待批）。",
        )

    _set_agent_state(db, "producer", "planning")

    db.add(
        Phase(
            id="clicker_mvp",
            title="点击成长小游戏 — 阶段计划",
            status="needs_confirmation",
            sort_order=10,
        )
    )
    tasks_spec = [
        ("t-mvp-design", "输出玩法与数值说明（策划）", "designer", 0),
        ("t-mvp-art", "输出 UI 与视觉规范（美术）", "artist", 1),
        ("t-mvp-dev", "实现点击成长 Web 原型（程序）", "developer", 2),
        ("t-mvp-qa", "阶段测试与报告（测试）", "qa", 3),
    ]
    for tid, title, owner, so in tasks_spec:
        db.add(
            Task(
                id=tid,
                phase_id="clicker_mvp",
                title=title,
                owner_agent_id=owner,
                status="todo",
                sort_order=so,
            )
        )

    meta.plan_generated = True
    _set_agent_state(db, "producer", "idle")

    add_event_log(
        db,
        "info",
        "制作人已生成阶段计划「点击成长小游戏」，等待用户批准。",
    )
    db.commit()
    return {"ok": True}
