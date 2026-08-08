import json
from pathlib import Path
from typing import Any
import re

REPORT_DIR = Path("reports")


def _load_latest_report() -> dict[str, Any] | None:
    """Load the most recently generated workflow report."""

    if not REPORT_DIR.exists():
        return None

    reports = list(
        REPORT_DIR.glob("workflow_report_*.json")
    )

    if not reports:
        return None

    latest_report = max(
        reports,
        key=lambda file: file.stat().st_mtime
    )

    try:
        with open(
            latest_report,
            "r",
            encoding="utf-8"
        ) as f:
            return json.load(f)

    except (
        json.JSONDecodeError,
        OSError
    ):
        return None


def _parse_output(output: Any) -> Any:
    """Parse Supervity step output when it is JSON text."""

    if output is None:
        return None

    if isinstance(output, (dict, list)):
        return output

    if isinstance(output, str):
        try:
            return json.loads(output)
        except (
            json.JSONDecodeError,
            TypeError
        ):
            return output

    return output


def calculate_metrics() -> dict[str, Any]:
    """
    Calculate operational metrics from the latest
    Supervity workflow report.

    This is the canonical source of operational
    metrics used by the Command Center.
    """

    report = _load_latest_report()

    if not report:
        return {
            "status": "no_data",
            "total_tickets": 0,
            "resolved_tickets": 0,
            "open_tickets": 0,
            "major_incidents": 0,
            "human_review": 0,
            "sla_breaches": 0,
            "resolution_rate": 0,
            "sla_compliance_rate": 0,
            "human_review_rate": 0,
            "auto_resolution_rate": 0,
            "verification_failures": 0,
            "verification_failure_rate": 0,
            "average_resolution_minutes": 0,
            "major_incidents_report": [],
            "ticket_metrics": [],
        }

    agents = report.get("agents", [])

    metrics = []
    major_incidents = []
    human_review = 0
    verification_failures = 0

    # ---------------------------------------------------------
    # Find Final Metrics output
    # ---------------------------------------------------------

    for agent in agents:

        name = agent.get("name", "")

        output = _parse_output(
            agent.get("output")
        )

        if name == "Final Metrics Operator Agent":

            if isinstance(output, dict):

                metrics = output.get(
                    "metrics",
                    []
                )

                major_incidents = output.get(
                    "major_incidents_report",
                    []
                )

        # -----------------------------------------------------
        # Count human review
        # -----------------------------------------------------

        if name == "Execute Human Workbench Actions":

            text = agent.get(
                "output",
                ""
            )

            if isinstance(text, str):

                match = re.search(
                    r"Processed\s+(\d+)\s+tickets",
                    text
                )

                if match:
                    human_review = int(
                        match.group(1)
                    )

        # -----------------------------------------------------
        # Detect verification failures
        # -----------------------------------------------------

        if name == "Verify Resolution":

            output_text = str(
                agent.get("output", "")
            ).lower()

            if (
                "failed" in output_text
                or "failure" in output_text
                or "not verified" in output_text
            ):
                verification_failures += 1

    # ---------------------------------------------------------
    # Calculate ticket metrics
    # ---------------------------------------------------------

    total_tickets = len(metrics)

    resolved_tickets = len([
        item
        for item in metrics
        if item.get("resolved") is True
    ])

    open_tickets = (
        total_tickets -
        resolved_tickets
    )

    sla_breaches = len([
        item
        for item in metrics
        if item.get("sla_met") is False
    ])

    sla_met = len([
        item
        for item in metrics
        if item.get("sla_met") is True
    ])

    auto_resolved = len([
        item
        for item in metrics
        if (
            item.get("resolved") is True
            and item.get("human_review") is False
        )
    ])

    # ---------------------------------------------------------
    # Resolution time
    # ---------------------------------------------------------

    resolution_minutes = [
        item.get(
            "resolution_minutes",
            0
        )
        for item in metrics
        if isinstance(
            item.get("resolution_minutes"),
            (int, float)
        )
        and item.get(
            "resolution_minutes",
            0
        ) > 0
    ]

    average_resolution = (
        sum(resolution_minutes)
        / len(resolution_minutes)
        if resolution_minutes
        else 0
    )

    # ---------------------------------------------------------
    # Rates
    # ---------------------------------------------------------

    resolution_rate = (
        resolved_tickets
        / total_tickets
        * 100
        if total_tickets
        else 0
    )

    sla_compliance_rate = (
        sla_met
        / total_tickets
        * 100
        if total_tickets
        else 0
    )

    human_review_rate = (
        human_review
        / total_tickets
        * 100
        if total_tickets
        else 0
    )

    auto_resolution_rate = (
        auto_resolved
        / total_tickets
        * 100
        if total_tickets
        else 0
    )

    verification_failure_rate = (
        verification_failures
        / total_tickets
        * 100
        if total_tickets
        else 0
    )

    # ---------------------------------------------------------
    # Risk level
    # ---------------------------------------------------------

    if len(major_incidents) > 0:
        risk_level = "CRITICAL"

    elif (
        sla_compliance_rate < 80
        or verification_failure_rate >= 50
    ):
        risk_level = "HIGH"

    elif (
        human_review_rate >= 50
        or auto_resolution_rate == 0
    ):
        risk_level = "MEDIUM"

    else:
        risk_level = "LOW"

    # ---------------------------------------------------------
    # Return canonical operational metrics
    # ---------------------------------------------------------

    return {
        "status": "ok",

        "total_tickets": total_tickets,

        "resolved_tickets":
            resolved_tickets,

        "open_tickets":
            open_tickets,

        "major_incidents":
            len(major_incidents),

        "human_review":
            human_review,

        "sla_breaches":
            sla_breaches,

        "resolution_rate":
            round(
                resolution_rate,
                2
            ),

        "sla_compliance_rate":
            round(
                sla_compliance_rate,
                2
            ),

        "human_review_rate":
            round(
                human_review_rate,
                2
            ),

        "auto_resolution_rate":
            round(
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

        "average_resolution_minutes":
            round(
                average_resolution,
                2
            ),

        "risk_level":
            risk_level,

        "major_incidents_report":
            major_incidents,

        "ticket_metrics":
            metrics,
    }
