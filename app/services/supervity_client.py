import os
import json
import time
import requests


def run_supervity_workflow(payload: dict):

    # Basic website/demo mode
    if os.getenv("BASIC_MODE", "false").lower() == "true":
        incidents = payload.get("tickets") or payload.get("ticket_dataset") or []

        print("=== BASIC MODE ===")
        print("Tickets:", json.dumps(incidents, indent=2))

        results = []

        for ticket in incidents:
            issue_key = (
                ticket.get("Issue key")
                or ticket.get("IssueKey")
                or ticket.get("key")
                or "UNKNOWN"
            )

            summary = ticket.get(
                "Summary",
                ticket.get("summary", "")
            )

            priority = ticket.get(
                "Priority",
                ticket.get("priority", "Medium")
            )

            status = ticket.get(
                "Status",
                ticket.get("status", "Open")
            )

            sla = ticket.get(
                "SLA",
                ticket.get("sla", "Within SLA")
            )

            if str(sla).lower() == "breached":
                decision = "HUMAN_REVIEW"
                confidence = 0.65
                action = "Review breached SLA ticket"
            elif str(priority).lower() in ["highest", "high"]:
                decision = "HUMAN_REVIEW"
                confidence = 0.70
                action = "Review high-priority ticket"
            else:
                decision = "SAFE_REMEDIATION"
                confidence = 0.90
                action = "Apply standard remediation"

            results.append({
                "issue_key": issue_key,
                "summary": summary,
                "priority": priority,
                "status": status,
                "sla": sla,
                "decision": decision,
                "confidence": confidence,
                "recommended_action": action,
                "root_cause": "Basic analysis placeholder"
            })

        workflow_result = {
            "status": "completed",
            "mode": "basic",
            "total_tickets": len(results),
            "results": results
        }

        return {
            "supervity_status": 200,
            "supervity_response": json.dumps({
                "workflowRun": workflow_result
            }),
            "workflow_run": workflow_result
        }

    # ---------------------------------------------------------
    # REAL SUPERVITY MODE
    # ---------------------------------------------------------

    api_url = os.getenv(
        "SUPERVITY_API_URL",
        "https://auto-workflow-api.supervity.ai"
    )

    workflow_id = os.getenv("SUPERVITY_WORKFLOW_ID")
    api_key = os.getenv("SUPERVITY_API_KEY")

    execute_url = f"{api_url}/api/v1/workflow-runs/execute"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "x-source": "external",
        "x-active-org": "ResolveOps",
        "x-user-timezone": "Asia/Kuala_Lumpur",
    }

    incidents = payload.get("tickets")

    print("=== SUPERVITY DEBUG ===")
    print("PAYLOAD:", json.dumps(payload, indent=2))
    print("INCIDENTS:", json.dumps(incidents, indent=2))

    if not incidents:
        raise ValueError(
            "No tickets were provided in the request payload."
        )

    ticket_dataset = json.dumps(incidents)

    print("TICKET DATASET:", ticket_dataset)
    print("======================")

    files = {
        "workflowId": (None, workflow_id),

        "inputs[ticket_dataset]": (
            "ticket_dataset.json",
            ticket_dataset,
            "application/json"
        ),

        "inputs[severity]": (
            None,
            payload.get("severity", "")
        ),

        "inputs[rules_config_threshold]": (
            None,
            ""
        ),

        "inputs[notification_target]": (
            None,
            ""
        ),
    }

    print("=== CALLING SUPERVITY ===")
    print("URL:", execute_url)

    response = requests.post(
        execute_url,
        headers=headers,
        files=files,
        timeout=300
    )

    print("SUPERVITY POST STATUS:", response.status_code)
    print("SUPERVITY POST RESPONSE:", response.text[:5000])

    if response.status_code != 200:
        return {
            "supervity_status": response.status_code,
            "supervity_response": response.text
        }

    try:
        execute_data = response.json()
    except ValueError:
        return {
            "supervity_status": response.status_code,
            "supervity_response": response.text,
            "error": "Supervity returned non-JSON response."
        }

    # ---------------------------------------------------------
    # Get workflow run ID
    # ---------------------------------------------------------

    workflow_runs = execute_data.get("workflowRuns", [])

    if not workflow_runs:
        return {
            "supervity_status": response.status_code,
            "supervity_response": response.text,
            "error": "Supervity response contained no workflowRuns."
        }

    run_id = workflow_runs[0].get("id")

    if not run_id:
        return {
            "supervity_status": response.status_code,
            "supervity_response": response.text,
            "error": "Supervity workflow run has no ID."
        }

    print("=== SUPERVITY RUN ===")
    print("RUN ID:", run_id)

    # ---------------------------------------------------------
    # Poll individual workflow run
    # ---------------------------------------------------------

    run_url = f"{api_url}/api/v1/workflow-runs/{run_id}"

    max_attempts = 60
    poll_interval = 2

    for attempt in range(max_attempts):

        print(
            f"Checking workflow status "
            f"({attempt + 1}/{max_attempts})..."
        )

        run_response = requests.get(
            run_url,
            headers=headers,
            timeout=30
        )

        print(
            "RUN STATUS HTTP:",
            run_response.status_code
        )

        if run_response.status_code != 200:
            print(
                "RUN RESPONSE:",
                run_response.text[:2000]
            )

            time.sleep(poll_interval)
            continue

        try:
            run_data = run_response.json()
        except ValueError:
            print("Run endpoint returned invalid JSON.")
            time.sleep(poll_interval)
            continue

        workflow_run = run_data.get("workflowRun", {})

        status = workflow_run.get("status")

        print("WORKFLOW STATUS:", status)

        if status in ["completed", "failed", "cancelled"]:
            print("=== SUPERVITY WORKFLOW FINISHED ===")
            print(
                json.dumps(
                    workflow_run,
                    indent=2,
                    default=str
                )[:20000]
            )

            return {
                "supervity_status": 200,
                "supervity_response": json.dumps(
                    run_data,
                    default=str
                ),
                "run_id": run_id,
                "workflow_run": workflow_run
            }

        time.sleep(poll_interval)

    return {
        "supervity_status": 408,
        "supervity_response": json.dumps(
            {
                "run_id": run_id,
                "error": "Workflow did not finish within polling timeout."
            }
        ),
        "run_id": run_id
    }