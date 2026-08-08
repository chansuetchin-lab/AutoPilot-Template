import json
from datetime import datetime
from pathlib import Path


REPORT_DIR = Path("reports")
REPORT_DIR.mkdir(exist_ok=True)


def _parse_output(value):
    """
    Supervity often returns operator output as a JSON string.
    Convert it into a Python object when possible.
    """
    if value is None:
        return None

    if isinstance(value, (dict, list)):
        return value

    if isinstance(value, str):
        value = value.strip()

        if not value:
            return None

        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value

    return value


def _find_activity(activities, step_id):
    """
    Find a specific Supervity activity by step ID.
    """
    for activity in activities:
        if activity.get("stepId") == step_id:
            return activity

    return None


def _get_activity_output(activities, step_id):
    """
    Return parsed output from a specific activity.
    """
    activity = _find_activity(activities, step_id)

    if not activity:
        return None

    outputs = activity.get("outputs") or {}

    return _parse_output(outputs.get("output"))


def generate_workflow_report(workflow_result: dict):
    """
    Convert the raw Supervity workflow result into a structured
    Command Center report.

    This report becomes the source for the AI Insights Engine.
    """

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    activities = workflow_result.get("activityRuns", [])

    # ---------------------------------------------------------
    # Extract operator outputs
    # ---------------------------------------------------------

    triage = _get_activity_output(
        activities,
        "sla_triage"
    )

    diagnosis = _get_activity_output(
        activities,
        "cross_system_diagnosis"
    )

    major_incidents = _get_activity_output(
        activities,
        "major_incident_detection"
    )

    routing = _get_activity_output(
        activities,
        "route_tickets"
    )

    remediation = _get_activity_output(
        activities,
        "safe_remediation"
    )

    workbench = _find_activity(
        activities,
        "auto_workbench"
    )

    workbench_processing = _get_activity_output(
        activities,
        "process_workbench_results"
    )

    verification = _get_activity_output(
        activities,
        "verify_resolution"
    )

    final_metrics = _get_activity_output(
        activities,
        "final_metrics"
    )

    # ---------------------------------------------------------
    # Build operator audit records
    # ---------------------------------------------------------

    agents = []

    for activity in activities:

        outputs = activity.get("outputs") or {}

        agents.append({
            "id": activity.get("id"),
            "name": activity.get("stepName"),
            "step_id": activity.get("stepId"),
            "description": activity.get("stepDescription"),
            "status": activity.get("status"),
            "started_at": activity.get("startedAt"),
            "completed_at": activity.get("completedAt"),
            "output": _parse_output(
                outputs.get("output")
            ),
            "display_data": outputs.get("displayData"),
            "error": outputs.get("error"),
            "error_details": activity.get("errorDetails"),
            "human_review": activity.get("userForm")
        })

    # ---------------------------------------------------------
    # Count workflow states
    # ---------------------------------------------------------

    completed_agents = [
        a for a in activities
        if a.get("status") == "completed"
    ]

    failed_agents = [
        a for a in activities
        if a.get("status") == "failed"
    ]

    # ---------------------------------------------------------
    # Extract final metrics
    # ---------------------------------------------------------

    metrics = []

    major_incidents_report = []

    if isinstance(final_metrics, dict):

        metrics = final_metrics.get(
            "metrics",
            []
        )

        major_incidents_report = final_metrics.get(
            "major_incidents_report",
            []
        )

    # ---------------------------------------------------------
    # Calculate Command Center metrics
    # ---------------------------------------------------------

    total_tickets = len(metrics)

    if total_tickets == 0:

        # Fallback to triage if Final Metrics doesn't contain
        # the ticket-level metrics.
        if isinstance(triage, dict):
            total_tickets = triage.get(
                "total_tickets",
                triage.get("unresolved_tickets", 0)
            )

    resolved_tickets = len([
        item
        for item in metrics
        if item.get("resolved") is True
    ])

    sla_met = len([
        item
        for item in metrics
        if item.get("sla_met") is True
    ])

    human_review = len([
        item
        for item in metrics
        if item.get("human_review") is True
    ])

    resolution_minutes = [
        item.get("resolution_minutes")
        for item in metrics
        if isinstance(
            item.get("resolution_minutes"),
            (int, float)
        )
    ]

    average_resolution_minutes = (
        sum(resolution_minutes) / len(resolution_minutes)
        if resolution_minutes
        else 0
    )

    auto_resolution_count = 0

    if isinstance(remediation, list):
        auto_resolution_count = len([
            item
            for item in remediation
            if str(
                item.get("status", "")
            ).lower()
            in {
                "success",
                "successful",
                "resolved",
                "completed"
            }
        ])

    verification_failures = 0

    if isinstance(verification, list):
        verification_failures = len([
            item
            for item in verification
            if str(
                item.get("verification_status", "")
            ).lower()
            in {
                "failed",
                "failure",
                "escalated"
            }
        ])

    major_incident_count = len(
        major_incidents_report
    )

    # Fallback to Major Incident Operator
    if major_incident_count == 0:

        if isinstance(major_incidents, list):

            major_incident_count = len([
                item
                for item in major_incidents
                if item.get("major_incident") is True
            ])

    resolution_rate = (
        (resolved_tickets / total_tickets) * 100
        if total_tickets
        else 0
    )

    sla_compliance_rate = (
        (sla_met / total_tickets) * 100
        if total_tickets
        else 0
    )

    human_review_rate = (
        (human_review / total_tickets) * 100
        if total_tickets
        else 0
    )

    auto_resolution_rate = (
        (auto_resolution_count / total_tickets) * 100
        if total_tickets
        else 0
    )

    verification_failure_rate = (
        (verification_failures / total_tickets) * 100
        if total_tickets
        else 0
    )

    # ---------------------------------------------------------
    # Risk assessment
    # ---------------------------------------------------------

    risk_level = "LOW"

    if major_incident_count > 0:
        risk_level = "HIGH"

    elif (
        verification_failures > 0
        or sla_compliance_rate < 80
    ):
        risk_level = "MEDIUM"

    if (
        major_incident_count > 0
        and verification_failures > 0
    ):
        risk_level = "CRITICAL"

    # ---------------------------------------------------------
    # Final report
    # ---------------------------------------------------------

    report = {
        "generated_at": timestamp,

        "workflow": {
            "workflow_id": workflow_result.get(
                "workflowId"
            ),
            "workflow_run_id": workflow_result.get(
                "id"
            ),
            "status": workflow_result.get(
                "status"
            )
        },

        "summary": {
            "total_agents": len(activities),
            "completed_agents": len(completed_agents),
            "failed_agents": len(failed_agents),

            "total_tickets": total_tickets,
            "resolved_tickets": resolved_tickets,

            "resolution_rate": round(
                resolution_rate,
                2
            ),

            "sla_met": sla_met,

            "sla_compliance_rate": round(
                sla_compliance_rate,
                2
            ),

            "human_review": human_review,

            "human_review_rate": round(
                human_review_rate,
                2
            ),

            "auto_resolution_count":
                auto_resolution_count,

            "auto_resolution_rate": round(
                auto_resolution_rate,
                2
            ),

            "verification_failures":
                verification_failures,

            "verification_failure_rate":
                round(
                    verification_failure_rate,
                    2
                ),

            "major_incidents":
                major_incident_count,

            "average_resolution_minutes":
                round(
                    average_resolution_minutes,
                    2
                ),

            "risk_level":
                risk_level
        },

        "operator_results": {
            "sla_triage": triage,
            "cross_system_diagnosis": diagnosis,
            "major_incident_detection":
                major_incidents,
            "route_tickets": routing,
            "safe_remediation": remediation,
            "workbench": (
                workbench.get("userForm")
                if workbench
                else None
            ),
            "workbench_processing":
                workbench_processing,
            "verification":
                verification,
            "final_metrics":
                final_metrics
        },

        "major_incidents_report":
            major_incidents_report,

        "agents":
            agents
    }

    filename = (
        REPORT_DIR
        / f"workflow_report_{timestamp}.json"
    )

    with open(
        filename,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            report,
            file,
            indent=2,
            ensure_ascii=False,
            default=str
        )

    return str(filename)