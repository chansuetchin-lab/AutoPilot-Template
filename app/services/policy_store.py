from datetime import datetime
from typing import Any


policies: list[dict[str, Any]] = [
    {
        "id": "demo-001",
        "name": "Auto-Approve Low Value Invoices",
        "description": "Automatically approve invoices under $500 from approved vendors.",
        "natural_language": (
            "If an invoice total is less than $500 and the vendor is in our "
            "approved vendor list, automatically approve for payment without "
            "requiring manual review."
        ),
        "summary": "Auto-approves low-value invoices from trusted vendors to reduce manual workload.",
        "policy_type": "logical",
        "dsl": {
            "conditions": [
                {
                    "field": "amount",
                    "operator": "less_than",
                    "value": "500",
                },
                {
                    "field": "vendor_status",
                    "operator": "equals",
                    "value": "approved",
                },
            ],
            "actions": [
                {
                    "type": "auto_approve",
                }
            ],
            "match_mode": "all",
        },
        "refined_instruction": None,
        "ai_instruction": (
            "WHEN amount < 500 AND vendor_status = approved "
            "THEN auto_approve"
        ),
        "entity_name": "invoice",
        "is_active": True,
        "priority": 10,
        "tags": ["finance", "auto-approve", "demo"],
        "execution_count": 120,
        "last_executed_at": None,
        "created_at": "2026-08-01T00:00:00",
        "updated_at": "2026-08-08T00:00:00",
    },
    {
        "id": "demo-002",
        "name": "CFO Approval for Large Transactions",
        "description": "Require CFO approval for any transaction exceeding $50,000.",
        "natural_language": (
            "Any transaction or purchase order exceeding $50,000 must be "
            "reviewed and approved by the CFO before processing."
        ),
        "summary": "Enforces executive approval on high-value transactions.",
        "policy_type": "logical",
        "dsl": {
            "conditions": [
                {
                    "field": "amount",
                    "operator": "greater_than",
                    "value": "50000",
                }
            ],
            "actions": [
                {
                    "type": "require_approval",
                    "value": "CFO",
                }
            ],
            "match_mode": "all",
        },
        "refined_instruction": None,
        "ai_instruction": (
            "WHEN amount > 50000 THEN require_approval(CFO)"
        ),
        "entity_name": "transaction",
        "is_active": True,
        "priority": 5,
        "tags": ["finance", "escalation", "demo"],
        "execution_count": 45,
        "last_executed_at": None,
        "created_at": "2026-08-01T00:00:00",
        "updated_at": "2026-08-08T00:00:00",
    },
]


def get_policies() -> list[dict[str, Any]]:
    return policies


def get_policy(policy_id: str) -> dict[str, Any] | None:
    return next(
        (policy for policy in policies if policy["id"] == policy_id),
        None,
    )


def create_policy(data: dict[str, Any]) -> dict[str, Any]:
    now = datetime.utcnow().isoformat()

    policy = {
        "id": f"policy-{len(policies) + 1}",
        "name": data.get("name", "Untitled Policy"),
        "description": data.get("description", ""),
        "natural_language": data.get("natural_language", ""),
        "summary": data.get("summary", data.get("description", "")),
        "policy_type": data.get("policy_type", "natural_language"),
        "dsl": data.get("dsl"),
        "refined_instruction": data.get("refined_instruction"),
        "ai_instruction": data.get(
            "ai_instruction",
            data.get("natural_language", ""),
        ),
        "entity_name": data.get("entity_name"),
        "is_active": data.get("is_active", True),
        "priority": data.get("priority", 50),
        "tags": data.get("tags", []),
        "execution_count": 0,
        "last_executed_at": None,
        "created_at": now,
        "updated_at": now,
    }

    policies.insert(0, policy)

    return policy


def update_policy(
    policy_id: str,
    data: dict[str, Any],
) -> dict[str, Any] | None:

    policy = get_policy(policy_id)

    if policy is None:
        return None

    for key, value in data.items():
        if key in policy and key not in {
            "id",
            "created_at",
            "execution_count",
            "last_executed_at",
        }:
            policy[key] = value

    policy["updated_at"] = datetime.utcnow().isoformat()

    return policy


def delete_policy(policy_id: str) -> bool:
    policy = get_policy(policy_id)

    if policy is None:
        return False

    policies.remove(policy)

    return True
