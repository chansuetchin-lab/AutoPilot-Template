import json
import os
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.audit import AuditLog
from app.services.exception_service import (
    get_exception,
    get_exceptions,
    update_exception,
)
from app.services.insight_service import generate_insights
from app.services.workbench_service import (
    execute_workbench_action,
    verify_workbench_action,
)

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None


router = APIRouter(
    prefix="/ai",
    tags=["AI"],
)


# ============================================================================
# Gemini configuration
# ============================================================================

GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.5-flash",
)

GEMINI_API_KEY = os.getenv(
    "GEMINI_API_KEY"
)


def get_gemini_client():
    """
    Create the Gemini API client.
    """

    if genai is None:
        raise RuntimeError(
            "google-genai is not installed."
        )

    if not GEMINI_API_KEY:
        raise RuntimeError(
            "GEMINI_API_KEY is not configured."
        )

    return genai.Client(
        api_key=GEMINI_API_KEY
    )


# ============================================================================
# Tool implementations
# ============================================================================


def tool_get_recent_activity(
    db: Session,
    limit: int = 8,
) -> dict[str, Any]:
    """
    Retrieve recent meaningful AutoPilot activity.

    AI Manager requests themselves and OPTIONS requests are excluded
    so that the result represents actual application activity.
    """

    limit = max(
        1,
        min(
            int(limit),
            20,
        ),
    )

    activities = (
        db.query(AuditLog)
        .filter(
            ~AuditLog.endpoint.in_(
                [
                    "/api/ai/chat",
                    "/api/insights",
                ]
            )
        )
        .filter(
            AuditLog.http_method != "OPTIONS"
        )
        .order_by(
            desc(AuditLog.timestamp)
        )
        .limit(limit)
        .all()
    )

    results = []

    for activity in activities:
        results.append(
            {
                "timestamp": (
                    activity.timestamp.isoformat()
                    if activity.timestamp
                    else None
                ),
                "action": activity.action,
                "endpoint": activity.endpoint,
                "method": activity.http_method,
                "description": activity.description,
                "success": activity.success,
                "severity": activity.severity,
            }
        )

    return {
        "count": len(results),
        "activities": results,
    }


def tool_get_exceptions() -> dict[str, Any]:
    """
    Retrieve all current AI Workbench exceptions.
    """

    exceptions = get_exceptions()

    return {
        "count": len(exceptions),
        "exceptions": exceptions,
    }


def tool_get_exception(
    exception_id: int,
) -> dict[str, Any]:
    """
    Retrieve a single exception.
    """

    exception = get_exception(
        exception_id
    )

    if not exception:
        return {
            "error": "Exception not found",
            "exception_id": exception_id,
        }

    return exception


def tool_approve_exception(
    exception_id: int,
) -> dict[str, Any]:
    """
    Approve an exception.
    """

    result = update_exception(
        exception_id,
        "approve",
    )

    if not result:
        return {
            "error": "Exception not found",
            "exception_id": exception_id,
        }

    return result


def tool_reject_exception(
    exception_id: int,
) -> dict[str, Any]:
    """
    Reject an exception and perform the existing
    rejection/escalation workflow.
    """

    result = update_exception(
        exception_id,
        "reject",
    )

    if not result:
        return {
            "error": "Exception not found",
            "exception_id": exception_id,
        }

    return execute_workbench_action(
        result
    )


def tool_remediate_exception(
    exception_id: int,
) -> dict[str, Any]:
    """
    Execute an approved remediation.
    """

    exception = get_exception(
        exception_id
    )

    if not exception:
        return {
            "error": "Exception not found",
            "exception_id": exception_id,
        }

    if exception.get("status") != "APPROVED":
        return {
            "error": (
                "Exception must be approved "
                "before remediation."
            ),
            "exception": exception,
        }

    exception["status"] = "REMEDIATING"

    exception["action_result"] = {
        "status": "EXECUTING",
        "message": (
            "Approved remediation is being executed."
        ),
    }

    result = execute_workbench_action(
        exception
    )

    result["status"] = "REMEDIATING"

    return result


def tool_verify_exception(
    exception_id: int,
) -> dict[str, Any]:
    """
    Verify an executed remediation.
    """

    exception = get_exception(
        exception_id
    )

    if not exception:
        return {
            "error": "Exception not found",
            "exception_id": exception_id,
        }

    verification = exception.get(
        "verification",
        {},
    )

    if verification.get("status") != "PENDING":
        return {
            "error": (
                "Exception is not waiting "
                "for verification."
            ),
            "exception": exception,
        }

    return verify_workbench_action(
        exception
    )


def tool_get_insights() -> dict[str, Any]:
    """
    Retrieve AI Insights from the existing
    AutoPilot insight service.
    """

    return generate_insights()


# ============================================================================
# Gemini tool declarations
#
# IMPORTANT:
# The google-genai SDK expects FunctionDeclaration objects inside
# a Tool(function_declarations=[...]).
# ============================================================================


def build_gemini_tools():
    """
    Build Gemini function declarations.
    """

    if types is None:
        raise RuntimeError(
            "Google Gemini SDK types are unavailable."
        )

    return [
        types.Tool(
            function_declarations=[
                types.FunctionDeclaration(
                    name="get_recent_activity",
                    description=(
                        "Retrieve recent AutoPilot audit activity. "
                        "Use this when the user asks about recent "
                        "activity, recent actions, system activity, "
                        "or audit activity."
                    ),
                    parameters={
                        "type": "object",
                        "properties": {
                            "limit": {
                                "type": "integer",
                                "description": (
                                    "Maximum number of activity "
                                    "records to retrieve."
                                ),
                            }
                        },
                    },
                ),
                types.FunctionDeclaration(
                    name="get_exceptions",
                    description=(
                        "Retrieve all current AI Workbench "
                        "exceptions. Use this when the user asks "
                        "about pending exceptions, workbench items, "
                        "human review, or exception status."
                    ),
                    parameters={
                        "type": "object",
                        "properties": {},
                    },
                ),
                types.FunctionDeclaration(
                    name="get_exception",
                    description=(
                        "Retrieve one AI Workbench exception "
                        "by ID."
                    ),
                    parameters={
                        "type": "object",
                        "properties": {
                            "exception_id": {
                                "type": "integer",
                                "description": (
                                    "Exception ID."
                                ),
                            }
                        },
                        "required": [
                            "exception_id"
                        ],
                    },
                ),
                types.FunctionDeclaration(
                    name="approve_exception",
                    description=(
                        "Approve a Workbench exception "
                        "for remediation."
                    ),
                    parameters={
                        "type": "object",
                        "properties": {
                            "exception_id": {
                                "type": "integer",
                                "description": (
                                    "Exception ID."
                                ),
                            }
                        },
                        "required": [
                            "exception_id"
                        ],
                    },
                ),
                types.FunctionDeclaration(
                    name="reject_exception",
                    description=(
                        "Reject a Workbench exception. "
                        "A rejected exception is passed to "
                        "the existing manual escalation "
                        "or workbench action."
                    ),
                    parameters={
                        "type": "object",
                        "properties": {
                            "exception_id": {
                                "type": "integer",
                                "description": (
                                    "Exception ID."
                                ),
                            }
                        },
                        "required": [
                            "exception_id"
                        ],
                    },
                ),
                types.FunctionDeclaration(
                    name="remediate_exception",
                    description=(
                        "Execute the approved remediation "
                        "for a Workbench exception. "
                        "The exception must already be APPROVED."
                    ),
                    parameters={
                        "type": "object",
                        "properties": {
                            "exception_id": {
                                "type": "integer",
                                "description": (
                                    "Exception ID."
                                ),
                            }
                        },
                        "required": [
                            "exception_id"
                        ],
                    },
                ),
                types.FunctionDeclaration(
                    name="verify_exception",
                    description=(
                        "Verify an executed remediation. "
                        "Use this after an exception has been "
                        "remediated and is waiting for verification."
                    ),
                    parameters={
                        "type": "object",
                        "properties": {
                            "exception_id": {
                                "type": "integer",
                                "description": (
                                    "Exception ID."
                                ),
                            }
                        },
                        "required": [
                            "exception_id"
                        ],
                    },
                ),
                types.FunctionDeclaration(
                    name="get_ai_insights",
                    description=(
                        "Retrieve AutoPilot AI Insights including "
                        "workflow metrics, risk level, SLA breaches, "
                        "human review, and recommendations."
                    ),
                    parameters={
                        "type": "object",
                        "properties": {},
                    },
                ),
            ]
        )
    ]


# ============================================================================
# Tool dispatcher
# ============================================================================


def execute_tool(
    name: str,
    args: dict[str, Any],
    db: Session,
) -> dict[str, Any]:

    if name == "get_recent_activity":
        return tool_get_recent_activity(
            db,
            int(
                args.get(
                    "limit",
                    8,
                )
            ),
        )

    if name == "get_exceptions":
        return tool_get_exceptions()

    if name == "get_exception":
        return tool_get_exception(
            int(
                args["exception_id"]
            )
        )

    if name == "approve_exception":
        return tool_approve_exception(
            int(
                args["exception_id"]
            )
        )

    if name == "reject_exception":
        return tool_reject_exception(
            int(
                args["exception_id"]
            )
        )

    if name == "remediate_exception":
        return tool_remediate_exception(
            int(
                args["exception_id"]
            )
        )

    if name == "verify_exception":
        return tool_verify_exception(
            int(
                args["exception_id"]
            )
        )

    if name == "get_ai_insights":
        return tool_get_insights()

    return {
        "error": (
            f"Unknown AI Manager tool: {name}"
        )
    }


# ============================================================================
# System instruction
# ============================================================================


SYSTEM_INSTRUCTION = """
You are AutoPilot AI, the intelligent assistant for the
AutoPilot Command Center.

You are connected to the real AutoPilot backend.

You can:

- explain the current page
- retrieve recent activity
- inspect AI Workbench exceptions
- inspect individual exceptions
- approve exceptions
- reject exceptions
- execute approved remediation
- verify remediation
- retrieve AI Insights

IMPORTANT:

Use tools when real application data or actions are required.

Do not invent system data.

When describing an action, clearly state what actually happened.

For operational actions:

- approve_exception changes an exception to approved
- reject_exception rejects the exception and performs the existing
  rejection workflow
- remediate_exception executes an already-approved remediation
- verify_exception verifies a remediation that is waiting for verification

Never claim that an operation succeeded unless the tool result
confirms it.

The current page is provided by the frontend. Use it when the
user asks to explain the current page.

For questions about actual AutoPilot data, prefer the available
backend tools over guessing.

Be concise, professional, and useful.
"""


# ============================================================================
# Helper: format recent activity
# ============================================================================


def format_recent_activity(
    result: dict[str, Any],
) -> str:

    activities = result.get(
        "activities",
        [],
    )

    if not activities:
        return (
            "There is currently no recent activity "
            "in AutoPilot."
        )

    lines = []

    for activity in activities:

        method = (
            activity.get("method")
            or ""
        )

        endpoint = (
            activity.get("endpoint")
            or ""
        )

        success = str(
            activity.get(
                "success",
                "",
            )
        ).lower()

        status = (
            "successful"
            if success == "true"
            else "unsuccessful"
        )

        description = (
            activity.get(
                "description"
            )
            or f"{method} {endpoint}"
        )

        lines.append(
            f"• {description} ({status})"
        )

    return (
        "Here is the most recent activity "
        "in AutoPilot:\n\n"
        + "\n".join(lines)
    )


# ============================================================================
# Helper: format exceptions
# ============================================================================


def format_exceptions(
    result: dict[str, Any],
) -> str:

    exceptions = result.get(
        "exceptions",
        [],
    )

    if not exceptions:
        return (
            "There are currently no pending "
            "exceptions in your queue."
        )

    lines = []

    for exception in exceptions:

        exception_id = exception.get(
            "id",
            "unknown",
        )

        exception_type = exception.get(
            "type",
            "UNKNOWN",
        )

        status = exception.get(
            "status",
            "UNKNOWN",
        )

        reason = exception.get(
            "reason",
            "",
        )

        line = (
            f"• Exception {exception_id}: "
            f"{exception_type} — {status}"
        )

        if reason:
            line += f" — {reason}"

        lines.append(line)

    return (
        "Here are the current AI Workbench "
        "exceptions:\n\n"
        + "\n".join(lines)
    )


# ============================================================================
# Chat endpoint
# ============================================================================


@router.post("/chat")
async def ai_chat(
    data: dict,
    db: Session = Depends(get_db),
):

    message = data.get(
        "message",
        "",
    ).strip()

    context = data.get(
        "context",
        {},
    )

    page = context.get(
        "page",
        "",
    )

    if not message:
        return {
            "response": (
                "How can I help you with AutoPilot?"
            )
        }

    # ------------------------------------------------------------------------
    # Gemini configuration check
    # ------------------------------------------------------------------------

    if not GEMINI_API_KEY:

        return {
            "response": (
                "Gemini AI is not configured. "
                "Please configure GEMINI_API_KEY."
            )
        }

    try:

        client = get_gemini_client()

        gemini_tools = build_gemini_tools()

        # --------------------------------------------------------------------
        # Include current page context
        # --------------------------------------------------------------------

        enriched_message = f"""
Current AutoPilot page:
{page or "Unknown"}

User request:
{message}
"""

        # --------------------------------------------------------------------
        # First Gemini request
        #
        # Gemini decides whether a backend tool is required.
        # --------------------------------------------------------------------

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=enriched_message,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                tools=gemini_tools,
            ),
        )

        tool_calls = []

        # --------------------------------------------------------------------
        # Gemini function calls
        # --------------------------------------------------------------------

        if response.function_calls:

            for function_call in response.function_calls:

                name = function_call.name

                args = (
                    dict(function_call.args)
                    if function_call.args
                    else {}
                )

                print(
                    "=== AI MANAGER TOOL CALL ==="
                )

                print(
                    "TOOL:",
                    name,
                )

                print(
                    "ARGS:",
                    json.dumps(
                        args,
                        default=str,
                    ),
                )

                result = execute_tool(
                    name,
                    args,
                    db,
                )

                tool_calls.append(
                    {
                        "name": name,
                        "args": args,
                        "result": result,
                    }
                )

            # ----------------------------------------------------------------
            # Single-tool responses
            #
            # Most AutoPilot requests should finish here.
            # This avoids an unnecessary second Gemini request.
            # ----------------------------------------------------------------

            if len(tool_calls) == 1:

                tool_call = tool_calls[0]

                name = tool_call["name"]

                result = tool_call["result"]

                # ------------------------------------------------------------
                # Recent activity
                # ------------------------------------------------------------

                if name == "get_recent_activity":

                    return {
                        "response": format_recent_activity(
                            result
                        ),
                        "tool_calls": tool_calls,
                    }

                # ------------------------------------------------------------
                # Workbench exceptions
                # ------------------------------------------------------------

                if name == "get_exceptions":

                    return {
                        "response": format_exceptions(
                            result
                        ),
                        "tool_calls": tool_calls,
                    }

                # ------------------------------------------------------------
                # Individual exception
                # ------------------------------------------------------------

                if name == "get_exception":

                    if result.get("error"):

                        return {
                            "response": (
                                f"I searched for exception "
                                f"{result.get('exception_id')} "
                                "but it was not found in the system."
                            ),
                            "tool_calls": tool_calls,
                        }

                    return {
                        "response": (
                            "Here is the requested exception:\n\n"
                            + json.dumps(
                                result,
                                indent=2,
                                default=str,
                            )
                        ),
                        "tool_calls": tool_calls,
                    }

                # ------------------------------------------------------------
                # AI Insights
                # ------------------------------------------------------------

                if name == "get_ai_insights":

                    if result.get(
                        "status"
                    ) == "no_data":

                        return {
                            "response": (
                                "There are currently no AI Insights "
                                "available. No workflow reports have "
                                "been generated yet."
                            ),
                            "tool_calls": tool_calls,
                        }

                    summary = result.get(
                        "summary",
                        {},
                    )

                    risk = result.get(
                        "risk",
                        {},
                    )

                    return {
                        "response": (
                            "AI Insights are available.\n\n"
                            f"Total tickets: "
                            f"{summary.get('total_tickets', 0)}\n"
                            f"Resolved: "
                            f"{summary.get('resolved_tickets', 0)}\n"
                            f"Open: "
                            f"{summary.get('open_tickets', 0)}\n"
                            f"Human review: "
                            f"{summary.get('human_review', 0)}\n"
                            f"SLA breaches: "
                            f"{summary.get('sla_breaches', 0)}\n"
                            f"Risk level: "
                            f"{risk.get('level', 'UNKNOWN')}"
                        ),
                        "tool_calls": tool_calls,
                    }

                # ------------------------------------------------------------
                # Operational actions
                # ------------------------------------------------------------

                if name in {
                    "approve_exception",
                    "reject_exception",
                    "remediate_exception",
                    "verify_exception",
                }:

                    if result.get("error"):

                        return {
                            "response": (
                                "The requested operation could "
                                "not be completed.\n\n"
                                f"{result.get('error')}"
                            ),
                            "tool_calls": tool_calls,
                        }

                    return {
                        "response": (
                            "The requested operation was completed "
                            "and the backend confirmed the result."
                            "\n\n"
                            + json.dumps(
                                result,
                                indent=2,
                                default=str,
                            )
                        ),
                        "tool_calls": tool_calls,
                    }

            # ----------------------------------------------------------------
            # Multi-tool fallback
            #
            # Only complex requests requiring multiple tools reach here.
            # ----------------------------------------------------------------

            tool_summary = json.dumps(
                tool_calls,
                indent=2,
                default=str,
            )

            try:

                final_response = client.models.generate_content(
                    model=GEMINI_MODEL,
                    contents=f"""
User request:
{message}

Current page:
{page}

The following tools were executed:

{tool_summary}

Respond naturally to the user.

Do not invent information that is not present
in the tool results.
""",
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_INSTRUCTION,
                    ),
                )

                return {
                    "response": (
                        final_response.text
                        if final_response.text
                        else (
                            "The requested operation completed."
                        )
                    ),
                    "tool_calls": tool_calls,
                }

            except Exception as summary_error:

                print(
                    "=== AI MANAGER SUMMARY ERROR ==="
                )

                print(
                    repr(summary_error)
                )

                return {
                    "response": (
                        "The requested operation completed, "
                        "but I could not generate the AI summary."
                    ),
                    "tool_calls": tool_calls,
                }

        # --------------------------------------------------------------------
        # Normal Gemini answer
        # --------------------------------------------------------------------

        return {
            "response": (
                response.text
                if response.text
                else "I couldn't generate a response."
            )
        }

    # ------------------------------------------------------------------------
    # Gemini quota / rate limit
    # ------------------------------------------------------------------------

    except Exception as error:

        print(
            "=== AI MANAGER ERROR ==="
        )

        print(
            repr(error)
        )

        error_text = str(error).lower()

        if (
            "429" in error_text
            or "resource_exhausted" in error_text
            or "quota" in error_text
        ):

            return {
                "response": (
                    "Gemini AI is temporarily rate-limited. "
                    "Please wait a few seconds and try again."
                ),
                "error": str(error),
            }

        # --------------------------------------------------------------------
        # Generic error
        # --------------------------------------------------------------------

        return {
            "response": (
                "I encountered an error while processing "
                "your request through AutoPilot AI."
            ),
            "error": str(error),
        }