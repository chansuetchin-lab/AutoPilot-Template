from fastapi import APIRouter, HTTPException

from app.services.exception_service import (
    create_exception,
    get_exceptions,
    get_exception,
    update_exception,
    sync_supervity_decisions,
)

from app.services.workbench_service import (
    execute_workbench_action,
    verify_workbench_action,
)


router = APIRouter(
    prefix="/exceptions",
    tags=["Workbench Exceptions"]
)


@router.post("")
async def add_exception(data: dict):
    return create_exception(data)


@router.get("")
async def list_exceptions():
    return get_exceptions()


@router.post("/{exception_id}/approve")
async def approve_exception(exception_id: int):

    result = update_exception(
        exception_id,
        "approve"
    )

    if not result:
        raise HTTPException(
            status_code=404,
            detail="Exception not found"
        )

    # Approval only.
    # Remediation must be explicitly triggered
    # through the /remediate endpoint.

    return result


@router.post("/{exception_id}/reject")
async def reject_exception(exception_id: int):

    result = update_exception(
        exception_id,
        "reject"
    )

    if not result:
        raise HTTPException(
            status_code=404,
            detail="Exception not found"
        )

    # Rejection can immediately be treated as
    # manual escalation.

    result = execute_workbench_action(result)

    return result


@router.post("/{exception_id}/remediate")
async def remediate_exception(exception_id: int):

    exception = get_exception(exception_id)

    if not exception:
        raise HTTPException(
            status_code=404,
            detail="Exception not found"
        )

    if exception["status"] != "APPROVED":
        raise HTTPException(
            status_code=400,
            detail="Exception must be approved before remediation."
        )

    # Change status before executing the action.
    exception["status"] = "REMEDIATING"

    exception["action_result"] = {
        "status": "EXECUTING",
        "message": "Approved remediation is being executed."
    }

    # Execute the actual Workbench action.
    result = execute_workbench_action(exception)

    # Workbench action has completed.
    result["status"] = "REMEDIATING"

    return result

@router.post("/{exception_id}/verify")
async def verify_exception(exception_id: int):

    exception = get_exception(exception_id)

    if not exception:
        raise HTTPException(
            status_code=404,
            detail="Exception not found"
        )

    if exception.get("verification", {}).get("status") != "PENDING":
        raise HTTPException(
            status_code=400,
            detail="Exception is not waiting for verification."
        )

    result = verify_workbench_action(exception)

    return result

@router.post("/sync-supervity")
async def sync_supervity(data: dict):
    decisions = data.get("decisions", {})

    if not decisions:
        return {
            "status": "skipped",
            "message": "No Supervity decisions were provided.",
            "results": []
        }

    results = sync_supervity_decisions(decisions)

    return {
        "status": "success",
        "results": results
    }

