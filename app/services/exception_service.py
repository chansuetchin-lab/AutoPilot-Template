exceptions = []
counter = 1


def create_exception(data):
    global counter

    incident = data.get("incident", {})
    issue_key = incident.get("key")

    # Prevent duplicate pending exceptions for the same ticket
    for existing in exceptions:
        existing_key = existing.get("incident", {}).get("key")

        if (
            existing_key == issue_key
            and existing.get("status") == "PENDING"
        ):
            return existing

    exception = {
        "id": counter,
        "type": data.get("type", "POLICY_VIOLATION"),
        "reason": data.get("reason", ""),
        "status": "PENDING",
        "incident": incident,
        "action_result": None,
    }

    exceptions.append(exception)
    counter += 1

    return exception


def get_exceptions():
    return exceptions


def get_exception(exception_id):
    for exception in exceptions:
        if exception["id"] == exception_id:
            return exception

    return None


def update_exception(exception_id, action):
    for exception in exceptions:

        if exception["id"] != exception_id:
            continue

        if action == "approve":
            exception["status"] = "APPROVED"

            exception["action_result"] = {
                "status": "PENDING_REMEDIATION",
                "message": (
                    "Human approval received. "
                    "Remediation is ready to execute."
                )
            }

        elif action == "reject":
            exception["status"] = "REJECTED"

            exception["action_result"] = {
                "status": "ESCALATED",
                "message": (
                    "Human rejected remediation. "
                    "Ticket requires manual handling."
                )
            }

        return exception

    return None

def sync_supervity_decisions(decisions):
    """
    Synchronize human decisions received from the
    Supervity Auto Workbench into backend exceptions.
    """

    results = []

    for issue_key, decision in decisions.items():
        action = decision.get("action", "").strip().lower()

        # Find the backend exception belonging to this ticket
        exception = None

        for existing in exceptions:
            existing_key = existing.get("incident", {}).get("key")

            if existing_key == issue_key:
                exception = existing
                break

        # Create an exception if one does not already exist
        if exception is None:
            exception = create_exception({
                "type": "HUMAN_REVIEW",
                "reason": "Ticket requires human approval before remediation.",
                "incident": {
                    "key": issue_key
                }
            })

        if action == "approve":
            exception["status"] = "APPROVED"

            exception["action_result"] = {
                "status": "PENDING_REMEDIATION",
                "message": (
                    "Human approval received from Supervity Workbench. "
                    "Remediation is ready to execute."
                )
            }

        elif action == "reject":
            exception["status"] = "REJECTED"

            exception["action_result"] = {
                "status": "ESCALATED",
                "message": (
                    "Human rejected remediation in Supervity Workbench. "
                    "Ticket requires manual handling."
                )
            }

        results.append(exception)

    return results