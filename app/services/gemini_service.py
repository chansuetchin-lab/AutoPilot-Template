import os
from typing import Any

from google import genai


def get_gemini_client() -> genai.Client:
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not configured."
        )

    return genai.Client(api_key=api_key)


def ask_gemini(
    message: str,
    page: str = "",
    history: list[dict[str, str]] | None = None,
) -> str:
    client = get_gemini_client()

    model = os.getenv(
        "GEMINI_MODEL",
        "gemini-2.5-flash",
    )

    system_instruction = """
You are AutoPilot AI, the intelligent assistant
for the AutoPilot Command Center.

You help users understand and operate the system.

The AutoPilot system contains:

- Command Center dashboard
- AI Policies
- AI Workbench / exceptions
- Orchestrator
- AI Insights
- Audit activity

You should:
- Answer questions clearly.
- Use the current page context when relevant.
- Explain what users can do on the current page.
- Help users understand incidents, policies, exceptions,
  workflows, insights, and audit activity.
- When an operational action is requested, identify the
  intended action clearly so the backend can execute it.
- Never invent system data.
- Never claim that an action was executed unless the backend
  confirms it.
- Never expose API keys, credentials, or internal secrets.
"""

    context = f"""
Current page:
{page or "Unknown"}

User request:
{message}
"""

    contents: list[dict[str, Any]] = []

    if history:
        for item in history[-10:]:
            role = item.get("role", "user")
            content = item.get("content", "")

            if not content:
                continue

            contents.append(
                {
                    "role": (
                        "model"
                        if role == "assistant"
                        else "user"
                    ),
                    "parts": [
                        {
                            "text": content
                        }
                    ],
                }
            )

    contents.append(
        {
            "role": "user",
            "parts": [
                {
                    "text": context
                }
            ],
        }
    )

    response = client.models.generate_content(
        model=model,
        contents=contents,
        config={
            "system_instruction": system_instruction,
            "temperature": 0.2,
        },
    )

    return response.text or (
        "I wasn't able to generate a response."
    )
