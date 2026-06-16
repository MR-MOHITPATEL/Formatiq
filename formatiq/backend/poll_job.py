import requests
import time
import sys

job_id = sys.argv[1] if len(sys.argv) > 1 else "scrape_526071"
url = "http://localhost:8000/api/jobs/" + job_id

for i in range(120):
    try:
        r = requests.get(url, timeout=5)
        d = r.json()
        status = d.get("status", "unknown")
        prog = d.get("progress", 0)
        total = d.get("total", 0)
        msg = d.get("message", "")
        print(f"{i*15}s | {status} | {prog}/{total} | {msg}", flush=True)
        if status in ("done", "error"):
            break
    except Exception as e:
        print(f"{i*15}s | error polling: {e}", flush=True)
    time.sleep(15)
