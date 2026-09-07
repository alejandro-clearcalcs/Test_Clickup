import os
import json
import time
from datetime import datetime, timezone

import requests

CLICKUP_API_TOKEN = os.environ["CLICKUP_API_TOKEN"]
LIST_ID = os.environ.get("CLICKUP_LIST_ID", "901614719925")

BASE_URL = "https://api.clickup.com/api/v2"
HEADERS = {"Authorization": CLICKUP_API_TOKEN}


def fetch_tasks(list_id):
    tasks = []
    page = 0
    while True:
        params = {
            "page": page,
            "include_closed": "true",
            "subtasks": "true",
        }
        resp = requests.get(
            f"{BASE_URL}/list/{list_id}/task",
            headers=HEADERS,
            params=params,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        batch = data.get("tasks", [])
        tasks.extend(batch)
        if data.get("last_page", True) or not batch:
            break
        page += 1
        time.sleep(0.5)  # be gentle with rate limits
    return tasks


def ts_to_iso(ts):
    if not ts:
        return None
    return datetime.fromtimestamp(int(ts) / 1000, tz=timezone.utc).isoformat()


def simplify_task(task):
    custom_fields = {}
    for cf in task.get("custom_fields", []):
        custom_fields[cf.get("name")] = cf.get("value")

    assignees = [a.get("username") for a in task.get("assignees", [])]

    return {
        "id": task.get("id"),
        "name": task.get("name"),
        "status": (task.get("status") or {}).get("status"),
        "assignees": assignees,
        "start_date": ts_to_iso(task.get("start_date")),
        "due_date": ts_to_iso(task.get("due_date")),
        "custom_fields": custom_fields,
        "url": task.get("url"),
    }


def main():
    tasks = fetch_tasks(LIST_ID)
    snapshot = {
        "extracted_at": datetime.now(timezone.utc).isoformat(),
        "list_id": LIST_ID,
        "task_count": len(tasks),
        "tasks": [simplify_task(t) for t in tasks],
    }

    os.makedirs("data", exist_ok=True)
    out_path = "data/snapshot.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2, ensure_ascii=False)

    print(f"Wrote {len(tasks)} tasks to {out_path}")


if __name__ == "__main__":
    main()
