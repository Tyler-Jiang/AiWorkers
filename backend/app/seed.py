"""Initial data when database is empty."""

import json
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Agent, Artifact, ComputerState, EventLog, Phase, StudioMeta, Task


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def seed_if_empty(db: Session) -> None:
    n = db.scalar(select(func.count()).select_from(Agent))
    if n and n > 0:
        return

    agents = [
        ("producer", "Producer", "制作人"),
        ("designer", "Designer", "策划"),
        ("developer", "Developer", "程序"),
        ("artist", "Artist", "美术"),
        ("qa", "QA", "测试"),
    ]
    for aid, name, role in agents:
        db.add(Agent(id=aid, name=name, role=role, state="idle"))

    db.add(
        Phase(
            id="bootstrap",
            title="工程骨架与状态系统",
            status="accepted",
            sort_order=0,
        )
    )
    db.add(
        Task(
            id="t-setup",
            phase_id="bootstrap",
            title="跑通本地前后端与 SQLite 持久化",
            owner_agent_id="developer",
            status="todo",
            sort_order=0,
        )
    )
    db.add(ComputerState(id=1, holder_agent_id=None, queue_json=json.dumps([])))
    db.add(
        EventLog(
            level="info",
            message="SQLite 已初始化；工程骨架阶段在种子数据中记为已验收。请提交用户需求开始 Stage D。",
            created_at=_utc_now(),
        )
    )
    db.add(Artifact(label="仓库", detail="ai_game_studio_docs / backend / frontend"))
    db.commit()


def ensure_studio_meta(db: Session) -> None:
    """已有库升级时补全 studio_meta 单例行。"""
    if db.get(StudioMeta, 1):
        return
    db.add(StudioMeta(id=1))
    db.commit()
