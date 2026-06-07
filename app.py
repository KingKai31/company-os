import os
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, Response, jsonify, render_template, request, send_from_directory

load_dotenv()

ROOT = Path(__file__).resolve().parent

app = Flask(__name__)

jobs_lock = threading.Lock()
jobs = {}

AGENT_KEYS = ["orchestrator", "ceo", "engineer", "legal", "sales", "finance", "risk"]

AGENT_PARSE_RULES = {
    "orchestrator": {
        "tag": "[ORCHESTRATOR]",
        "step": "Step 1/7: Orchestrator",
        "running_keywords": ["Planning"],
        "complete_line": "Orchestrator complete",
        "failed_line": "Orchestrator failed",
    },
    "ceo": {
        "tag": "[CEO]",
        "step": "Step 2/7: CEO",
        "running_keywords": ["Writing", "Reading", "Scoring"],
        "complete_line": "CEO Agent complete",
        "failed_line": "CEO Agent failed",
    },
    "legal": {
        "tag": "[LEGAL]",
        "step": "Step 3/7: Legal",
        "running_keywords": ["Reading", "Generating"],
        "complete_line": "Legal Agent complete",
        "failed_line": "Legal Agent failed",
    },
    "sales": {
        "tag": "[SALES]",
        "step": "Step 4/7: Sales",
        "running_keywords": ["Reading", "Generating", "Requesting"],
        "complete_line": "Sales Agent complete",
        "failed_line": "Sales Agent failed",
    },
    "finance": {
        "tag": "[FINANCE]",
        "step": "Step 5/7: Finance",
        "running_keywords": ["Reading", "Generating"],
        "complete_line": "Finance Agent complete",
        "failed_line": "Finance Agent failed",
    },
    "risk": {
        "tag": "[RISK]",
        "step": "Step 6/7: Risk",
        "running_keywords": ["Reading", "Analysing"],
        "complete_line": "Risk Agent complete",
        "failed_line": "Risk Agent failed",
    },
    "engineer": {
        "tag": "[ENGINEER]",
        "step": "Step 7/7: Engineer",
        "running_keywords": ["Reading", "Detecting", "Assembling", "Deploying", "Building", "Loaded"],
        "complete_line": "Engineer Agent complete",
        "failed_line": "Engineer Agent failed",
    },
}


def parse_agent_status(lines):
    status = {key: "IDLE" for key in AGENT_KEYS}
    negotiation_triggered = False

    for line in lines:
        if "[ALERT]" in line and "CRITICAL" in line.upper():
            negotiation_triggered = True

        for agent, rules in AGENT_PARSE_RULES.items():
            if rules["failed_line"] in line:
                status[agent] = "ERROR"
                continue

            if rules.get("step") and rules["step"] in line:
                if status[agent] not in ("COMPLETE", "ERROR"):
                    status[agent] = "RUNNING"

            if rules["complete_line"] in line:
                if "status: error" in line.lower():
                    status[agent] = "ERROR"
                elif "status: complete" in line.lower() or agent == "orchestrator":
                    status[agent] = "COMPLETE"
                else:
                    status[agent] = "COMPLETE"
                continue

            if rules["tag"] in line:
                if any(kw in line for kw in rules["running_keywords"]):
                    if status[agent] not in ("COMPLETE", "ERROR"):
                        status[agent] = "RUNNING"

    return {"agents": status, "negotiation_triggered": negotiation_triggered}


def run_pipeline_job(job_id, idea):
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    process = subprocess.Popen(
        [sys.executable, str(ROOT / "main.py"), idea],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(ROOT),
        env=env,
        bufsize=1,
    )

    assert process.stdout is not None
    for raw_line in process.stdout:
        line = raw_line.rstrip("\n")
        with jobs_lock:
            if job_id in jobs:
                jobs[job_id]["lines"].append(line)

    process.wait()

    with jobs_lock:
        if job_id in jobs:
            jobs[job_id]["done"] = True
            jobs[job_id]["returncode"] = process.returncode
            jobs[job_id]["finished_at"] = time.time()


def get_job(job_id):
    with jobs_lock:
        return jobs.get(job_id)


def get_latest_job_id():
    with jobs_lock:
        if not jobs:
            return None
        return max(jobs.keys(), key=lambda k: jobs[k].get("started_at", 0))


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory(ROOT / "static", filename)


@app.route("/api/run", methods=["POST"])
def api_run():
    data = request.get_json(silent=True) or {}
    idea = (data.get("idea") or "").strip()
    if not idea:
        return jsonify({"error": "idea is required"}), 400

    job_id = str(uuid.uuid4())
    with jobs_lock:
        jobs[job_id] = {
            "lines": [],
            "done": False,
            "idea": idea,
            "started_at": time.time(),
            "finished_at": None,
            "returncode": None,
        }

    thread = threading.Thread(target=run_pipeline_job, args=(job_id, idea), daemon=True)
    thread.start()

    return jsonify({"job_id": job_id})


@app.route("/api/stream/<job_id>")
def api_stream(job_id):
    def generate():
        cursor = 0
        while True:
            with jobs_lock:
                job = jobs.get(job_id)
                if not job:
                    yield "data: ERROR: job not found\n\n"
                    break
                lines = job["lines"]
                done = job["done"]

            while cursor < len(lines):
                yield f"data: {lines[cursor]}\n\n"
                cursor += 1

            if done and cursor >= len(lines):
                yield "data: PIPELINE_COMPLETE\n\n"
                break

            time.sleep(0.25)

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.route("/api/results")
def api_results():
    try:
        from utils.shared_brain import read_all_states

        states = read_all_states()
        if not states:
            return jsonify({"warning": "Cosmos DB empty or slow — try again", "states": {}})
        return jsonify(states)
    except Exception as e:
        return jsonify({"error": str(e), "states": {}}), 503


@app.route("/api/agents")
def api_agents():
    job_id = request.args.get("job_id") or get_latest_job_id()
    if not job_id:
        return jsonify({"agents": {k: "IDLE" for k in AGENT_KEYS}, "negotiation_triggered": False})

    job = get_job(job_id)
    if not job:
        return jsonify({"error": "job not found"}), 404

    parsed = parse_agent_status(job["lines"])
    parsed["job_id"] = job_id
    parsed["done"] = job["done"]
    if job.get("started_at") and job.get("finished_at"):
        parsed["runtime_seconds"] = round(job["finished_at"] - job["started_at"], 1)
    return jsonify(parsed)


@app.route("/api/reset", methods=["POST"])
def api_reset():
    try:
        from utils.shared_brain import clear_all

        cleared = clear_all()
        with jobs_lock:
            jobs.clear()

        if cleared:
            return jsonify({"status": "reset", "message": "Cosmos DB cleared and jobs reset"})
        return jsonify({"status": "partial", "message": "Jobs cleared; Cosmos may be slow or unavailable"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/health")
def api_health():
    cosmos_ok = False
    try:
        from utils.shared_brain import read_all_states
        read_all_states()
        cosmos_ok = True
    except Exception:
        pass
    return jsonify({"status": "ok", "cosmos": cosmos_ok})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
