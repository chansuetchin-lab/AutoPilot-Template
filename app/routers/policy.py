from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.policy import Policy
from app.schemas.policy import PolicyCreate, PolicyResponse
from app.services.policy_service import process_policy_check


router = APIRouter(
    prefix="/ai/policies",
    tags=["AI Policies"],
)


# ============================================================================
# GET POLICIES
# ============================================================================

@router.get("")
async def get_policies(
    db: Session = Depends(get_db),
):
    policies = (
        db.query(Policy)
        .order_by(Policy.created_at.desc())
        .all()
    )

    return [
        PolicyResponse.model_validate(policy).model_dump(mode="json")
        for policy in policies
    ]


# ============================================================================
# CREATE POLICY
# ============================================================================

@router.post(
    "",
    response_model=PolicyResponse,
)
async def create_policy(
    data: PolicyCreate,
    db: Session = Depends(get_db),
):
    """
    Create and persist an AI policy.
    """

    policy_id = f"pol-{uuid4().hex[:12]}"

    policy = Policy(
        id=policy_id,
        name=data.name,
        description=data.description,
        summary=data.summary,
        natural_language=data.natural_language,
        policy_type=data.policy_type,
        policy_scope=data.policy_scope,

        dsl=(
            data.dsl.model_dump()
            if data.dsl is not None
            else None
        ),

        refined_instruction=data.refined_instruction,
        ai_instruction=data.ai_instruction,
        entity_name=data.entity_name,

        is_active=data.is_active,
        priority=data.priority,
        tags=data.tags,
        source=data.source,

        execution_count=0,
        last_executed_at=None,
    )

    try:
        db.add(policy)
        db.commit()
        db.refresh(policy)

    except Exception as exc:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Failed to create policy: {str(exc)}",
        )

    return policy

# ============================================================================
# UPDATE POLICY
# ============================================================================

@router.patch("/{policy_id}", response_model=PolicyResponse)
async def update_policy(
    policy_id: str,
    data: dict,
    db: Session = Depends(get_db),
):
    """
    Update an existing AI policy.
    """

    policy = (
        db.query(Policy)
        .filter(Policy.id == policy_id)
        .first()
    )

    if not policy:
        raise HTTPException(
            status_code=404,
            detail="Policy not found.",
        )

    # Update only fields supplied by the frontend.
    if "name" in data:
        policy.name = data["name"]

    if "description" in data:
        policy.description = data["description"]

    if "natural_language" in data:
        policy.natural_language = data["natural_language"]

    if "policy_type" in data:
        policy.policy_type = data["policy_type"]

    if "refined_instruction" in data:
        policy.refined_instruction = data["refined_instruction"]

    if "entity_name" in data:
        policy.entity_name = data["entity_name"]

    if "priority" in data:
        policy.priority = data["priority"]

    if "tags" in data:
        policy.tags = data["tags"]

    if "is_active" in data:
        policy.is_active = data["is_active"]

    if "dsl" in data:
        policy.dsl = data["dsl"]

    try:
        db.commit()
        db.refresh(policy)

    except Exception as exc:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Failed to update policy: {str(exc)}",
        )

    return policy



# ============================================================================
# AI POLICY ANALYSIS
# ============================================================================

@router.post("/analyze-input")
async def analyze_policy_input(
    data: dict,
):
    """
    Analyze a natural-language policy and return a structured suggestion.

    This endpoint is used by the CreateWithAI frontend workflow.
    """

    user_input = str(data.get("input", "")).strip()

    if not user_input:
        raise HTTPException(
            status_code=400,
            detail="Policy input is required.",
        )

    text = user_input.lower()

    # ------------------------------------------------------------------------
    # Detect likely entity
    # ------------------------------------------------------------------------

    entity_name = None

    entity_keywords = {
        "invoice": "invoice",
        "invoices": "invoice",
        "ticket": "ticket",
        "tickets": "ticket",
        "item": "item",
        "items": "item",
        "vendor": "vendor",
        "employee": "employee",
        "employees": "employee",
        "request": "request",
        "requests": "request",
        "incident": "incident",
        "incidents": "incident",
    }

    for keyword, entity in entity_keywords.items():
        if keyword in text:
            entity_name = entity
            break

    # ------------------------------------------------------------------------
    # Detect common logical conditions
    # ------------------------------------------------------------------------

    import re

    conditions = []

    # amount < 500 / under 500 / below 500
    amount_match = re.search(
        r"(?:amount|invoice|item).*?"
        r"(?:under|below|less than|<)\s*\$?\s*([0-9]+(?:\.[0-9]+)?)",
        text,
    )

    if amount_match:
        amount = float(amount_match.group(1))

        if amount.is_integer():
            amount = int(amount)

        conditions.append(
            {
                "field": "amount",
                "operator": "lt",
                "value": amount,
            }
        )

    # greater than / above / over
    amount_gt_match = re.search(
        r"(?:amount|invoice|item).*?"
        r"(?:over|above|greater than|>)\s*\$?\s*([0-9]+(?:\.[0-9]+)?)",
        text,
    )

    if amount_gt_match:
        amount = float(amount_gt_match.group(1))

        if amount.is_integer():
            amount = int(amount)

        conditions.append(
            {
                "field": "amount",
                "operator": "gt",
                "value": amount,
            }
        )

    # ------------------------------------------------------------------------
    # Detect common status/vendor conditions
    # ------------------------------------------------------------------------

    if "approved vendor" in text or "approved vendors" in text:
        conditions.append(
            {
                "field": "vendor_status",
                "operator": "eq",
                "value": "approved",
            }
        )

    # ------------------------------------------------------------------------
    # Detect actions
    # ------------------------------------------------------------------------

    actions = []

    if "auto-approve" in text or "auto approve" in text or "approve automatically" in text:
        actions.append(
            {
                "type": "auto_approve",
            }
        )

    elif "approve directly" in text:
        actions.append(
            {
                "type": "auto_approve",
            }
        )

    elif "escalate" in text:
        actions.append(
            {
                "type": "escalate",
            }
        )

    elif "assign" in text:
        actions.append(
            {
                "type": "assign",
            }
        )

    elif "reject" in text or "deny" in text:
        actions.append(
            {
                "type": "reject",
            }
        )

    # ------------------------------------------------------------------------
    # Determine policy type
    # ------------------------------------------------------------------------

    is_logical = len(conditions) > 0 and len(actions) > 0

    suggested_type = (
        "logical"
        if is_logical
        else "natural_language"
    )

    # ------------------------------------------------------------------------
    # Generate DSL
    # ------------------------------------------------------------------------

    dsl = None

    if is_logical:
        dsl = {
            "conditions": conditions,
            "actions": actions,
            "match_mode": "all",
            "stop_on_match": False,
        }

    # ------------------------------------------------------------------------
    # Generate name
    # ------------------------------------------------------------------------

    if actions:
        action_name = actions[0]["type"].replace("_", " ").title()
    else:
        action_name = "Policy"

    if entity_name:
        suggested_name = f"{action_name} {entity_name.title()} Rule"
    else:
        suggested_name = "AI Policy Rule"

    # ------------------------------------------------------------------------
    # Generate summary
    # ------------------------------------------------------------------------

    if is_logical:
        summary = (
            f"Automatically {actions[0]['type'].replace('_', ' ')} "
            f"when the specified conditions are satisfied."
        )
    else:
        summary = (
            "Natural-language policy requiring AI interpretation."
        )

    # ------------------------------------------------------------------------
    # Refined instruction
    # ------------------------------------------------------------------------

    refined_instruction = user_input

    if is_logical:
        condition_text = []

        for condition in conditions:
            condition_text.append(
                f"{condition['field']} "
                f"{condition['operator']} "
                f"{condition['value']}"
            )

        action_text = ", ".join(
            action["type"].replace("_", " ")
            for action in actions
        )

        refined_instruction = (
            f"WHEN {' AND '.join(condition_text)} "
            f"THEN {action_text}."
        )

    # ------------------------------------------------------------------------
    # Tags
    # ------------------------------------------------------------------------

    suggested_tags = []

    if entity_name:
        suggested_tags.append(entity_name)

    if actions:
        suggested_tags.append(
            actions[0]["type"].replace("_", "-")
        )

    if "automatic" in text or "auto" in text:
        suggested_tags.append("automation")

    if "approve" in text:
        suggested_tags.append("approval")

    # Remove duplicates while preserving order
    suggested_tags = list(dict.fromkeys(suggested_tags))

    # ------------------------------------------------------------------------
    # Confidence
    # ------------------------------------------------------------------------

    if is_logical:
        confidence = 0.92
        reason = (
            "The policy contains identifiable conditions and an explicit action."
        )
    elif conditions:
        confidence = 0.75
        reason = (
            "The policy contains identifiable conditions but the action is unclear."
        )
    else:
        confidence = 0.60
        reason = (
            "The policy is best handled as a natural-language instruction."
        )

    return {
        "suggested_type": suggested_type,
        "confidence": confidence,
        "reason": reason,
        "suggested_name": suggested_name,
        "summary": summary,
        "dsl": dsl,
        "refined_instruction": refined_instruction,
        "entity_name": entity_name,
        "suggested_tags": suggested_tags,
    }


# ============================================================================
# POLICY CONFLICT CHECK
# ============================================================================

@router.post("/check-conflicts")
async def check_policy_conflicts(
    data: dict,
    db: Session = Depends(get_db),
):
    """
    Check a proposed policy against existing policies.

    The frontend uses this during the Create With AI workflow.
    """

    natural_language = str(
        data.get("natural_language", "")
    ).strip()

    policy_scope = data.get(
        "policy_scope",
        "base",
    )

    entity_name = data.get(
        "entity_name"
    )

    if not natural_language:
        raise HTTPException(
            status_code=400,
            detail="natural_language is required.",
        )

    existing_policies = (
        db.query(Policy)
        .filter(
            Policy.is_active.is_(True)
        )
        .order_by(
            Policy.priority.asc()
        )
        .all()
    )

    conflicts = []
    overrides = []
    clarifications = []
    suggested_instructions = []

    proposed_text = natural_language.lower()

    # ------------------------------------------------------------------------
    # Basic conflict detection
    # ------------------------------------------------------------------------

    for policy in existing_policies:
        existing_text = (
            f"{policy.name} "
            f"{policy.description or ''} "
            f"{policy.natural_language or ''}"
        ).lower()

        same_entity = (
            entity_name
            and policy.entity_name
            and entity_name.lower()
            == policy.entity_name.lower()
        )

        # Same entity + overlapping approval/rejection intent
        approval_conflict = (
            ("approve" in proposed_text)
            and (
                "reject" in existing_text
                or "deny" in existing_text
            )
        )

        rejection_conflict = (
            (
                "reject" in proposed_text
                or "deny" in proposed_text
            )
            and "approve" in existing_text
        )

        if same_entity and (
            approval_conflict
            or rejection_conflict
        ):
            conflicts.append(
                {
                    "conflicting_rule_id": policy.id,
                    "conflicting_rule_name": policy.name,
                    "explanation": (
                        "This policy appears to have an opposing "
                        "action for the same entity."
                    ),
                }
            )

        # --------------------------------------------------------------------
        # Instruction rules override base rules
        # --------------------------------------------------------------------

        if (
            policy_scope == "instruction"
            and policy.policy_scope == "base"
            and same_entity
        ):
            overrides.append(
                {
                    "overridden_rule_id": policy.id,
                    "overridden_rule_name": policy.name,
                    "explanation": (
                        "The instruction-scoped policy takes precedence "
                        "over the base policy for this entity."
                    ),
                }
            )

    # ------------------------------------------------------------------------
    # Clarification suggestions
    # ------------------------------------------------------------------------

    if "approve" in proposed_text and "manual" not in proposed_text:
        clarifications.append(
            "Consider specifying whether manual review should be skipped."
        )

    if not entity_name:
        clarifications.append(
            "Consider specifying which entity this policy applies to."
        )

    # ------------------------------------------------------------------------
    # Suggested instruction
    # ------------------------------------------------------------------------

    suggested_instructions.append(
        natural_language
    )

    return {
        "conflicts": conflicts,
        "overrides": overrides,
        "clarifications": clarifications,
        "suggested_instructions": suggested_instructions,
        "refined_instruction": natural_language,
        "is_valid": len(conflicts) == 0,
        "warnings": [],
    }


# ============================================================================
# POLICY CHECK
# ============================================================================

@router.post("/check")
async def policy_check(
    data: dict,
    db: Session = Depends(get_db),
):
    return process_policy_check(data, db)