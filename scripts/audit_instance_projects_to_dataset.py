from __future__ import annotations

"""
Collect a per-project inventory from a DSS instance and write it to a dataset in THIS project.

Intended usage: run from a DSS Jupyter notebook (in this project) or from a scenario Python step.
"""

from typing import Any, Dict, Optional


def _get_current_project_key() -> str:
    import dataiku

    return dataiku.default_project_key()


def _get_client(host: Optional[str] = None, api_key: Optional[str] = None):
    import dataiku
    import dataikuapi

    if host and api_key:
        return dataikuapi.DSSClient(host, api_key)
    return dataiku.api_client()


def _ensure_output_dataset(project_key: str, dataset_name: str) -> None:
    import dataiku

    client = dataiku.api_client()
    project = client.get_project(project_key)

    try:
        ds_handle = project.get_dataset(dataset_name)
        ds_raw = ds_handle.get_settings().get_raw()
    except Exception as e:
        raise Exception(
            f"Output dataset '{dataset_name}' not found (or not accessible). Create it first, or pull it from Git."
        ) from e

    if str(ds_raw.get("type")) != "Filesystem" or not bool(ds_raw.get("managed")):
        raise Exception(
            f"Output dataset '{dataset_name}' must be a managed Filesystem dataset. Current: type={ds_raw.get('type')}, managed={ds_raw.get('managed')}"
        )


def run(
    *,
    output_dataset: str = "INSTANCE_PROJECT_USAGE",
    host: Optional[str] = None,
    api_key: Optional[str] = None,
    project_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Writes a dataset with columns:
    - projectKey, projectName
    - pythonCodeEnv, webappPythonCodeEnvs
    - snowflakeConnections
    - openaiConnections, openaiLLMIds
    - errors
    """

    import pandas as pd
    import dataiku

    from dku_project_bulk_move.instance_audit import collect_instance_project_usage

    if project_key is None:
        project_key = _get_current_project_key()

    client = _get_client(host=host, api_key=api_key)
    rows = collect_instance_project_usage(client)
    records = [r.as_dict() for r in rows]

    _ensure_output_dataset(project_key, output_dataset)
    ds = dataiku.Dataset(output_dataset)
    df = pd.DataFrame.from_records(records)
    ds.write_with_schema(df)

    return {"rows": len(df), "dataset": output_dataset, "projectKey": project_key}


if __name__ == "__main__":
    # This is mostly useful when running as a python process; in DSS, prefer calling run() from a notebook.
    res = run()
    print(res)
