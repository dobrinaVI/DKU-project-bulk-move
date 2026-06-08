# DKU project bulk move

This repository is a **Dataiku project** that provides a **Standard Webapp** to migrate (copy) projects from a **source DSS instance** to a **target DSS instance** using the Dataiku Python API (`dataikuapi`).

## What it does

- Exports each source project to a ZIP archive
- Imports the ZIP into the target instance
- Applies **connection remapping** during import (for example Snowflake + OpenAI/LLM Mesh connection names)
- Applies **code env remapping** during import (for example Agent/tool Python code envs that don’t exist on the target)
- Runs the migration in a **background thread** from the webapp backend
- Does **not** delete or modify the source project (export-only)

## Where the code lives

- Migration library: `lib/python/dku_project_bulk_move/migrator.py`
- Instance inventory helper: `lib/python/dku_project_bulk_move/instance_audit.py`
- Standard webapp (id `pyCCIum`): `web_apps/pyCCIum/`

## Optional: instance inventory table

If you want a quick table of what projects use **Snowflake datasets**, **OpenAI-family LLMs**, and which **Python code envs** are configured, run:

- Script: `scripts/audit_instance_projects_to_dataset.py`
- Output dataset (default): `INSTANCE_PROJECT_USAGE`

## Usage (in DSS)

1. In the project, open **Code → Webapps → project_bulk_move**.
2. Fill in:
   - Source host + API key
   - Target host + API key
   - Project keys (one per line)
   - Connection remapping rows (source → target)
   - Code env remapping rows (source → target)
3. Click **Start** and monitor the status panel.

Notes:
- API keys are only used in-memory by the backend job runner and are **redacted** in stored job state.
- The import API requires you to map connections to existing target connections of a compatible type.
- If the import fails with `ERR_BUNDLE_ACTIVATE_MISSING_CODE_ENV`, add a code env mapping (or create that code env on the target).
