import json

from fastapi import APIRouter

from app.services.supervity_client import run_supervity_workflow
from app.services.report_generator import generate_workflow_report
from app.services.exception_service import create_exception


orchestrator_router = APIRouter(
    prefix="/orchestrator",
    tags=["Orchestrator"]
)


@orchestrator_router.post("/run")
def run_orchestrator(data: dict):

    # ---------------------------------------------------------
    # 1. Execute Supervity Orchestrator
    # ---------------------------------------------------------

    result = run_supervity_workflow(data)

    print("=== SUPERVITY RESULT ===")
    print(json.dumps(result, indent=2, default=str))
    print("========================")

    if result.get("supervity_status") != 200:
        print("=== SUPERVITY FAILED ===")
        print("Status:", result.get("supervity_status"))
        print("Response:", result.get("supervity_response"))

        return {
            "status": "failed",
            "result": result
        }

    # ---------------------------------------------------------
    # 2. Parse Supervity response
    # ---------------------------------------------------------

    try:
        workflow_json = json.loads(
            result["supervity_response"]
        )

        workflow_result = workflow_json["workflowRun"]

    except (json.JSONDecodeError, KeyError, TypeError) as e:

        print("=== WORKFLOW PARSE ERROR ===")
        print("Error:", str(e))
        print("Supervity response:")
        print(result.get("supervity_response"))
        print("============================")

        return {
            "status": "failed",
            "result": result,
            "error": f"Could not parse Supervity workflow response: {str(e)}"
        }

    print("=== WORKFLOW RESULT ===")
    print(json.dumps(workflow_result, indent=2, default=str))
    print("=======================")



    # ---------------------------------------------------------
    # 3. Generate workflow report
    # ---------------------------------------------------------

    report_file = generate_workflow_report(
        workflow_result
    )

    # ---------------------------------------------------------
    # 4. Find Merge and Route Tickets result
    # ---------------------------------------------------------

    review_keys = []

    for activity in workflow_result.get("activityRuns", []):

        if activity.get("stepId") == "route_tickets":

            output = activity.get("outputs", {}).get("output", "")

            if output:

                try:
                    route_result = json.loads(output)

                    review_keys = route_result.get(
                        "review_keys",
                        []
                    )

                except json.JSONDecodeError:
                    review_keys = []

            break

    # ---------------------------------------------------------
    # 5. Create local Workbench exceptions
    # ---------------------------------------------------------

    created_exceptions = []

    tickets = data.get("tickets", [])

    diagnosis_by_key = {}

    # Find Cross-System Diagnosis output
    for activity in workflow_result.get("activityRuns", []):

        print("STEP ID:", activity.get("stepId"))

        if activity.get("stepId") != "cross_system_diagnosis":
            continue

        diagnosis_output = (
            activity
            .get("outputs", {})
            .get("output", "")
        )

        print("=== DIAGNOSIS OUTPUT ===")
        print(diagnosis_output)
        print("========================")

        try:
            diagnosis_data = json.loads(diagnosis_output)

            if isinstance(diagnosis_data, list):

                for item in diagnosis_data:

                    key = item.get("Issue key")

                    if key:
                        diagnosis_by_key[key] = item

            elif isinstance(diagnosis_data, dict):
                    key = diagnosis_data.get("Issue key")
                    if key:
                        diagnosis_by_key[key] = diagnosis_data


        except (json.JSONDecodeError, TypeError):
            print("Could not parse diagnosis output.")

        break


    # Create exceptions only for tickets requiring review
    for ticket in tickets:

        issue_key = ticket.get("Issue key")

        if issue_key not in review_keys:
            continue

        diagnosis = diagnosis_by_key.get(
            issue_key,
            {}
        )

        exception = create_exception({
            "type": "HUMAN_REVIEW",

            "reason": (
                "Ticket requires human approval before "
                "remediation."
            ),

            "incident": {

                "key": issue_key,

                "summary": ticket.get(
                    "Summary",
                    ""
                ),

                "priority": ticket.get(
                    "Priority",
                    ""
                ),
    
                "status": ticket.get(
                    "Status",
                    ""
                ),

                "diagnosis": diagnosis.get(
                    "root_cause",
                    diagnosis.get(
                        "mi_reasoning",
                        "Diagnosis not available."
                    )
                ),

                "diagnosis_confidence": diagnosis.get(
                    "confidence",
                    diagnosis.get(
                        "diagnosis_confidence"
                    )
                ),

                "action": diagnosis.get(
                    "recommended_action",
                    "Review and approve remediation"
                )
            }
        })

        created_exceptions.append(exception)

    # ---------------------------------------------------------
    # 6. Return result
    # ---------------------------------------------------------

    return {
        "status": "submitted",
        "result": result,
        "report_file": report_file,
        "workbench_exceptions": created_exceptions
    }