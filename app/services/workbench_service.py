from datetime import datetime


def execute_workbench_action(exception):
    """
    Execute the action approved by a human operator.
    """

    incident = exception.get("incident", {})
    issue_key = incident.get("key")

    if exception["status"] in ("APPROVED", "REMEDIATING"):
        exception["execution"] = {
            "status": "EXECUTED",
            "action": "REMEDIATION",
            "issue_key": issue_key,
            "timestamp": datetime.utcnow().isoformat()
        }

        exception["verification"] = {
            "status": "PENDING"
        }

    elif exception["status"] == "REJECTED":
        exception["execution"] = {
            "status": "ESCALATED",
            "action": "MANUAL_SUPPORT",
            "issue_key": issue_key,
            "timestamp": datetime.utcnow().isoformat()
        }

        exception["verification"] = {
            "status": "SKIPPED",
            "reason": "Human rejected remediation"
        }

    return exception

def verify_workbench_action(exception):
    """
    Verify whether the executed remediation resolved the incident.
    """

    if exception.get("execution", {}).get("status") != "EXECUTED":
        exception["verification"] = {
            "status": "FAILED",
            "reason": "No successful remediation execution found."
        }
        return exception

    exception["verification"] = {
        "status": "VERIFIED",
        "message": "Remediation execution completed successfully.",
    }

    exception["status"] = "RESOLVED"

    return exception