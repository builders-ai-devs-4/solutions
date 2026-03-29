import json, os, requests
from libs.loggers import agent_logger


def _post_to_central(answer) -> tuple[str, dict]:
    """Private helper — common logic for POSTing to the central server."""
    payload = {
        "apikey": os.environ["AI_DEVS_SECRET"],
        "task":   os.environ["TASK_NAME"],
        "answer": answer,
    }
    agent_logger.info(f"[central] POST answer={str(answer)[:200]}")

    response = requests.post(os.environ["SOLUTION_URL"], json=payload, timeout=30)
    result   = response.json()

    if not response.ok:
        agent_logger.warning(f"[central] FAIL status={response.status_code} msg={result}")
        return (
            f"Central rejected the answer. "
            f"Status: {response.status_code}. "
            f"Message: {json.dumps(result, ensure_ascii=False)}. "
            f"Review the answer and retry.",
            payload,
        )

    agent_logger.info(f"[central] OK response={result}")
    return json.dumps(result, ensure_ascii=False, indent=2), payload