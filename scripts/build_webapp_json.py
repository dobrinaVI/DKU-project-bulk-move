from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
WEBAPP_SRC_DIR = REPO_ROOT / "webapp_src" / "project_bulk_move"
WEBAPP_DST_DIR = REPO_ROOT / "web_apps"

WEBAPP_ID = "pyCCIum"  # already exists in the DSS project; kept stable for Git-for-projects
PROJECT_KEY = "DKU_PROJECT_MOVE"


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def main() -> None:
    html = _read_text(WEBAPP_SRC_DIR / "body.html")
    css = _read_text(WEBAPP_SRC_DIR / "style.css")
    js = _read_text(WEBAPP_SRC_DIR / "app.js")
    python_code = _read_text(WEBAPP_SRC_DIR / "backend.py")

    definition = {
        "type": "STANDARD",
        "hasLegacyBackendURL": False,
        "projectKey": PROJECT_KEY,
        "id": WEBAPP_ID,
        "storageFile": f"projects/{PROJECT_KEY}/web_apps/{WEBAPP_ID}.json",
        "params": {
            "html": html,
            "css": css,
            "js": js,
            "python": python_code,
            "backendEnabled": True,
            "enableJavascriptModules": False,
            "autoStartBackend": True,
            "hideJSSecurityPanel": False,
            "hideWebAppConfig": False,
            "envSelection": {"envMode": "INHERIT"},
            "nbProcesses": 0,
            "backendAPIAccessEnabled": True,
            "backendFramework": "FLASK",
            "libraries": ["jquery", "dataiku"],
            "infra": {
                "containerSelection": {"containerMode": "INHERIT"},
                "overrideGlobalK8sExposition": False,
                "exposition": {"type": "local_process", "params": {}},
                "scaling": {
                    "initialReplicas": 1,
                    "progressDeadlineSeconds": 600,
                    "hpa": False,
                    "hpaTargetCPUPercent": 0,
                    "hpaTargetMemoryPercent": 0,
                    "hpaMetrics": [],
                    "hpaMinPods": 0,
                    "hpaMaxPods": 0,
                    "hpaAnnotations": [],
                },
                "podDisruptionBudget": {
                    "enable": False,
                    "isMaxUnavailable": False,
                    "minAvailable": "50%",
                },
                "deploymentModifier": {"config": {}},
            },
            "forceAuthentication": False,
        },
        "config": {},
        "name": "project_bulk_move",
        # Do NOT commit the per-webapp project API key field (it is instance-specific).
        "tags": [],
        "checklists": {"checklists": []},
        "customFields": {},
        "isVirtual": False,
    }

    WEBAPP_DST_DIR.mkdir(parents=True, exist_ok=True)
    out_path = WEBAPP_DST_DIR / f"{WEBAPP_ID}.json"
    out_path.write_text(json.dumps(definition, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()

