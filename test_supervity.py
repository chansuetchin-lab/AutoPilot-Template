import os
import json
import requests

api_url = os.getenv(
    "SUPERVITY_API_URL",
    "https://auto-workflow-api.supervity.ai"
)

workflow_id = os.getenv("SUPERVITY_WORKFLOW_ID")
api_key = os.getenv("SUPERVITY_API_KEY")

url = f"{api_url}/api/v1/workflow-runs/execute"

headers = {
    "Authorization": f"Bearer {api_key}",
    "x-source": "external",
    "x-active-org": "ResolveOps",
    "x-user-timezone": "Asia/Kuala_Lumpur",
}

tickets = [
    {
        "Summary": "Production API is unavailable",
        "Issue key": "INC-TEST-002",
        "Priority": "Highest",
        "Status": "Open",
    }
]

ticket_dataset = json.dumps(tickets)

files = {
    "workflowId": (None, workflow_id),
    "inputs[ticket_dataset]": (
        "ticket_dataset.json",
        ticket_dataset,
        "application/json",
    ),
    "inputs[severity]": (None, ""),
    "inputs[rules_config_threshold]": (None, ""),
    "inputs[notification_target]": (None, ""),
}

print("Calling:", url)
print("Workflow:", workflow_id)
print("Starting request...")

try:
    response = requests.post(
        url,
        headers=headers,
        files=files,
        timeout=30,
    )

    print("STATUS:", response.status_code)
    print("RESPONSE:")
    print(response.text[:5000])

except Exception as e:
    print("ERROR:", repr(e))