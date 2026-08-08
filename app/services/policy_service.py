from app.services.policy_engine import evaluate_policy
from app.services.exception_service import create_exception


def process_policy_check(data, db):

    decision = evaluate_policy(data, db)

    if decision["decision"] == "REQUIRE_APPROVAL":
        create_exception({
            "type": "POLICY_VIOLATION",
            "reason": decision["reason"],
            "incident": data,
        })

    return decision