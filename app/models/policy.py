from sqlalchemy import Boolean, Column, DateTime, Integer, JSON, String
from sqlalchemy.sql import func

from ..core.database import Base


class Policy(Base):
    __tablename__ = "policies"

    id = Column(String(100), primary_key=True, index=True)

    name = Column(String(255), nullable=False, index=True)
    description = Column(String, nullable=False, default="")
    summary = Column(String, nullable=True)

    natural_language = Column(String, nullable=False, default="")

    policy_type = Column(
        String(50),
        nullable=False,
        default="natural_language",
        index=True,
    )

    policy_scope = Column(
        String(50),
        nullable=True,
        default="base",
    )

    dsl = Column(JSON, nullable=True)

    refined_instruction = Column(String, nullable=True)
    ai_instruction = Column(String, nullable=True)
    entity_name = Column(String(255), nullable=True)

    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
    )

    priority = Column(
        Integer,
        nullable=False,
        default=50,
        index=True,
    )

    tags = Column(
        JSON,
        nullable=False,
        default=list,
    )

    source = Column(
        String(100),
        nullable=True,
        default="user",
    )

    execution_count = Column(
        Integer,
        nullable=False,
        default=0,
    )

    last_executed_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )