from typing import Any

from sqlalchemy.orm import Session

from app.models.policy import Policy


def evaluate_policy(
    data: dict[str, Any],
    db: Session,
) -> dict[str, Any]:

    # Get active policies, highest priority first
    policies = (
        db.query(Policy)
        .filter(Policy.is_active == True)
        .order_by(Policy.priority.asc())
        .all()
    )

    for policy in policies:

        dsl = policy.dsl

        if not dsl:
            continue

        conditions = dsl.get("conditions", [])
        match_mode = dsl.get("match_mode", "all")

        results = []

        for condition in conditions:

            field = condition.get("field")
            operator = condition.get("operator")
            expected = condition.get("value")

            actual = data.get(field)

            if actual is None:
                results.append(False)
                continue

            try:
                if operator in ("less_than", "lt"):
                    result = float(actual) < float(expected)

                elif operator in ("greater_than", "gt"):
                    result = float(actual) > float(expected)

                elif operator in ("equals", "equal", "eq"):
                    result = str(actual) == str(expected)

                elif operator in ("not_equals", "neq"):
                    result = str(actual) != str(expected)

                else:
                    result = False

                results.append(result)

            except (ValueError, TypeError):
                results.append(False)

        # Determine whether policy matches
        if match_mode == "any":
            matched = any(results)
        else:
            matched = all(results)

        if not matched:
            continue

        # Policy matched
        actions = dsl.get("actions", [])

        if not actions:
            return {
                "decision": "ALLOW",
                "reason": f"Policy matched: {policy.name}",
                "policy_id": policy.id,
                "policy_name": policy.name,
            }

        action = actions[0]
        action_type = action.get("type", "")

        if action_type in (
            "require_approval",
            "require_human_review",
            "human_review",
        ):
            decision = "REQUIRE_APPROVAL"

        elif action_type in (
            "block",
            "deny",
            "reject",
        ):
            decision = "BLOCK"

        elif action_type in (
            "escalate",
        ):
            decision = "ESCALATE"

        elif action_type in (
            "auto_approve",
            "approve",
        ):
            decision = "ALLOW"

        else:
            decision = "ALLOW"

        return {
            "decision": decision,
            "reason": f"Policy matched: {policy.name}",
            "policy_id": policy.id,
            "policy_name": policy.name,
            "action": action_type,
        }

    return {
        "decision": "ALLOW",
        "reason": "No active policy matched",
    }