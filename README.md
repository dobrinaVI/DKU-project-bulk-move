# DKU project bulk move

This repository is a **Dataiku project** that provides a **Standard Webapp** to migrate (copy) projects from a **source DSS instance** to a **target DSS instance** using the Dataiku Python API (`dataikuapi`).

## What it does

- Exports each source project to a ZIP archive
- Imports the ZIP into the target instance
- Applies **connection remapping** during import (for example Snowflake + OpenAI/LLM Mesh connection names)
- Runs the migration in a **background thread** from the webapp backend
- Does **not** delete or modify the source project (export-only)

## Where the code lives

- Migration library: `lib/python/dku_project_bulk_move/migrator.py`
- Webapp sources (editable): `webapp_src/project_bulk_move/`
- Webapp definition tracked by Git-for-projects: `web_apps/pyCCIum.json`

To regenerate the tracked `web_apps/pyCCIum.json` from `webapp_src/`:

```bash
python3 scripts/build_webapp_json.py
```

## Usage (in DSS)

1. In the project, open **Code → Webapps → project_bulk_move**.
2. Fill in:
   - Source host + API key
   - Target host + API key
   - Project keys (one per line)
   - Connection remapping rows (source → target)
3. Click **Start** and monitor the status panel.

Notes:
- API keys are only used in-memory by the backend job runner and are **redacted** in stored job state.
- The import API requires you to map connections to existing target connections of a compatible type.
