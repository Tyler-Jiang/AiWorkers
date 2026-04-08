"""ORM models for studio state."""

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    role: Mapped[str] = mapped_column(String(64))
    state: Mapped[str] = mapped_column(String(32), default="idle")


class Phase(Base):
    __tablename__ = "phases"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(256))
    status: Mapped[str] = mapped_column(String(32))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    phase_id: Mapped[str] = mapped_column(String(64), ForeignKey("phases.id"))
    title: Mapped[str] = mapped_column(String(512))
    owner_agent_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    from_agent: Mapped[str] = mapped_column(String(64))
    to_agent: Mapped[str | None] = mapped_column(String(64), nullable=True)
    msg_type: Mapped[str] = mapped_column(String(32))
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String(32))


class EventLog(Base):
    __tablename__ = "event_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    level: Mapped[str] = mapped_column(String(16), default="info")
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String(32))


class ComputerState(Base):
    """Singleton row id=1: 电脑锁与队列（queue 为 JSON 字符串数组）。"""

    __tablename__ = "computer_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    holder_agent_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    queue_json: Mapped[str] = mapped_column(Text, default="[]")


class Artifact(Base):
    __tablename__ = "artifacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    label: Mapped[str] = mapped_column(String(256))
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)


class StudioMeta(Base):
    """单例 id=1：Stage D 用户需求与计划流程标记。"""

    __tablename__ = "studio_meta"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    requirement_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    clarification_answered: Mapped[bool] = mapped_column(Boolean, default=False)
    plan_generated: Mapped[bool] = mapped_column(Boolean, default=False)


class AgentInvocation(Base):
    """Cursor / 模拟 Agent 调用记录（Stage E）。"""

    __tablename__ = "agent_invocations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    agent_id: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32))
    external_ref: Mapped[str | None] = mapped_column(String(256), nullable=True)
    prompt_summary: Mapped[str] = mapped_column(Text)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(String(32))
    updated_at: Mapped[str] = mapped_column(String(32))
