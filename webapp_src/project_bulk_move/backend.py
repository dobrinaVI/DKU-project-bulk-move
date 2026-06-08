from __future__ import annotations

import json
import threading
import time
import uuid
from typing import Any, Dict

from flask import request

from dataiku.customwebapp import app

from dku_project_bulk_move.migrator import InstanceCredentials, migrate_projects


_JOBS: Dict[str, Dict[str, Any]] = {}
_JOBS_LOCK = threading.Lock()


def _now_ms() -> int:
    return int(time.time() * 1000)


def _sanitize_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    redacted = json.loads(json.dumps(payload))  # deep copy
    if isinstance(redacted.get("source"), dict) and "apiKey" in redacted["source"]:
        redacted["source"]["apiKey"] = "***"
    if isinstance(redacted.get("target"), dict) and "apiKey" in redacted["target"]:
        redacted["target"]["apiKey"] = "***"
    return redacted


def _set_job(job_id: str, patch: Dict[str, Any]) -> None:
    with _JOBS_LOCK:
        state = _JOBS.get(job_id) or {"jobId": job_id}
        state.update(patch)
        _JOBS[job_id] = state


def _get_job(job_id: str) -> Dict[str, Any]:
    with _JOBS_LOCK:
        return dict(_JOBS.get(job_id) or {"jobId": job_id, "status": "unknown"})


def _run_job(job_id: str, payload: Dict[str, Any]) -> None:
    _set_job(
        job_id,
        {
            "status": "running",
            "startedAtMs": _now_ms(),
            "payload": _sanitize_payload(payload),
            "result": None,
            "error": None,
        },
    )

    try:
        source = InstanceCredentials(
            host=payload["source"]["host"], api_key=payload["source"]["apiKey"]
        )
        target = InstanceCredentials(
            host=payload["target"]["host"], api_key=payload["target"]["apiKey"]
        )

        projects = payload.get("projects") or []
        connection_remap = payload.get("connectionRemap") or {}
        export_options = payload.get("options") or {}

        result = migrate_projects(
            source=source,
            target=target,
            project_keys=projects,
            connection_remap=connection_remap,
            export_options=export_options,
            target_key_prefix=payload.get("targetKeyPrefix") or "",
        )

        _set_job(job_id, {"status": "done", "finishedAtMs": _now_ms(), "result": result})
    except Exception as e:
        _set_job(job_id, {"status": "error", "finishedAtMs": _now_ms(), "error": repr(e)})


@app.route("/start", methods=["POST"])
def start() -> str:
    payload = request.get_json(force=True, silent=False)  # type: ignore[no-untyped-call]
    job_id = str(uuid.uuid4())
    _set_job(job_id, {"status": "queued", "createdAtMs": _now_ms()})
    t = threading.Thread(target=_run_job, args=(job_id, payload), daemon=True)
    t.start()
    return json.dumps({"jobId": job_id})


@app.route("/status", methods=["GET"])
def status() -> str:
    job_id = request.args.get("jobId", "")
    return json.dumps(_get_job(job_id))
