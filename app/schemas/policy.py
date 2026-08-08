from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class PolicyCondition(BaseModel):
    field: str
    operator: str
    value: Any


class PolicyAction(BaseModel):
    type: str
    value: Any | None = None
    params: dict[str, Any] | None = None


class PolicyDSL(BaseModel):
    conditions: list[PolicyCondition] = Field(default_factory=list)
    actions: list[PolicyAction] = Field(default_factory=list)
    match_mode: Literal["all", "any"] = "all"
    stop_on_match: bool | None = None


class PolicyCreate(BaseModel):
    name: str
    description: str = ""
    natural_language: str = ""

    summary: str | None = None

    policy_type: Literal[
        "logical",
        "natural_language",
    ] = "natural_language"

    policy_scope: Literal[
        "base",
        "instruction",
        "custom",
    ] = "base"

    dsl: PolicyDSL | None = None

    refined_instruction: str | None = None
    ai_instruction: str | None = None
    entity_name: str | None = None

    is_active: bool = True
    priority: int = 50

    tags: list[str] = Field(default_factory=list)

    source: str = "user"


class PolicyResponse(PolicyCreate):
    id: str

    execution_count: int
    last_executed_at: datetime | None

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)