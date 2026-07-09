import os
import time
import requests
from dotenv import load_dotenv

load_dotenv("/opt/lontranoc/.env")

OO_URL = os.getenv("OPENOBSERVE_URL")
OO_ORG = os.getenv("OPENOBSERVE_ORG", "default")
OO_USER = os.getenv("OPENOBSERVE_READ_USER")
OO_TOKEN = os.getenv("OPENOBSERVE_READ_TOKEN")


def search_logs(sql: str, hours: int = 24, size: int = 100, start_time=None, end_time=None):
    if end_time is None:
        end_time = int(time.time() * 1_000_000)

    if start_time is None:
        start_time = end_time - (hours * 60 * 60 * 1_000_000)

    payload = {
        "query": {
            "sql": sql,
            "from": 0,
            "size": size,
            "start_time": start_time,
            "end_time": end_time,
        }
    }

    response = requests.post(
        f"{OO_URL}/api/{OO_ORG}/_search",
        json=payload,
        auth=(OO_USER, OO_TOKEN),
        headers={"Content-Type": "application/json"},
        timeout=20,
    )

    if not response.ok:
        print("STATUS:", response.status_code)
        print("RESPOSTA:", response.text)
        response.raise_for_status()

    return response.json().get("hits", [])