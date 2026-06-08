from __future__ import annotations

import os
import tempfile
import time
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional

import dataikuapi


@dataclass(frozen=True)
class InstanceCredentials:
    host: str
    api_key: str


def _now_ms() -> int:
    return int(time.time() * 1000)


def build_import_settings(
    *,
    target_project_key: Optional[str],
    connection_remap: Mapping[str, str],
    codeenv_remap: Optional[Mapping[str, str]] = None,
) -> Dict[str, Any]:
    """
    Builds the settings dict for `TemporaryImportHandle.execute(settings=...)`.

    Reference: `DSSClient.prepare_project_import()` -> `TemporaryImportHandle.execute()`.
    """

    settings: Dict[str, Any] = {}
    if target_project_key:
        settings["targetProjectKey"] = target_project_key

    remapping: Dict[str, Any] = {}
    if connection_remap:
        remapping["connections"] = [
            {"source": src, "target": tgt} for src, tgt in connection_remap.items()
        ]
    if codeenv_remap:
        remapping["codeEnvs"] = [
            {"source": src, "target": tgt} for src, tgt in codeenv_remap.items()
        ]
    if remapping:
        settings["remapping"] = remapping

    return settings


def export_project_to_zip(
    src_client: dataikuapi.DSSClient,
    project_key: str,
    export_options: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Exports a project to a local zip file and returns the file path.
    """

    project = src_client.get_project(project_key)
    fd, zip_path = tempfile.mkstemp(prefix=f"dku_export_{project_key}_", suffix=".zip")
    os.close(fd)
    try:
        project.export_to_file(zip_path, options=export_options or {})
        return zip_path
    except Exception:
        try:
            os.remove(zip_path)
        except Exception:
            pass
        raise


def import_project_from_zip(
    tgt_client: dataikuapi.DSSClient,
    zip_path: str,
    import_settings: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Imports a project from a local zip file.

    Warning: you must check the `success` flag in the result.
    """

    with open(zip_path, "rb") as f:
        handle = tgt_client.prepare_project_import(f)
        result = handle.execute(settings=import_settings or {})
    if not isinstance(result, dict):
        raise TypeError(f"Unexpected import result type: {type(result)}")
    return result


def migrate_projects(
    *,
    source: InstanceCredentials,
    target: InstanceCredentials,
    project_keys: Iterable[str],
    connection_remap: Mapping[str, str],
    export_options: Optional[Dict[str, Any]] = None,
    target_key_prefix: str = "",
) -> Dict[str, Any]:
    """
    Migrate projects from one DSS instance to another.

    - Exports each project to a zip (locally) from the source instance
    - Imports it to the target instance with connection remapping
    This function never deletes or modifies the source project. It only exports it.
    """

    src_client = dataikuapi.DSSClient(source.host, source.api_key)
    tgt_client = dataikuapi.DSSClient(target.host, target.api_key)

    report: Dict[str, Any] = {
        "startedAtMs": _now_ms(),
        "finishedAtMs": None,
        "success": True,
        "projects": [],
    }

    for project_key in list(project_keys):
        item: Dict[str, Any] = {
            "sourceProjectKey": project_key,
            "targetProjectKey": f"{target_key_prefix}{project_key}"
            if target_key_prefix
            else project_key,
            "success": False,
        }
        report["projects"].append(item)

        zip_path: Optional[str] = None
        try:
            zip_path = export_project_to_zip(
                src_client, project_key, export_options=export_options
            )

            import_settings = build_import_settings(
                target_project_key=item["targetProjectKey"],
                connection_remap=connection_remap,
            )
            import_result = import_project_from_zip(
                tgt_client, zip_path, import_settings=import_settings
            )
            item["importResult"] = import_result
            item["success"] = bool(import_result.get("success", False))

            if not item["success"]:
                report["success"] = False
        except Exception as e:
            item["error"] = repr(e)
            report["success"] = False
        finally:
            if zip_path and os.path.exists(zip_path):
                try:
                    os.remove(zip_path)
                except Exception:
                    pass

    report["finishedAtMs"] = _now_ms()
    return report
