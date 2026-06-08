from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple

import dataikuapi


@dataclass(frozen=True)
class ProjectUsageRow:
    project_key: str
    project_name: str
    python_code_env: str
    webapp_python_code_envs: Tuple[str, ...]
    agent_tool_code_envs: Tuple[str, ...]
    snowflake_connections: Tuple[str, ...]
    openai_connections: Tuple[str, ...]
    openai_llm_ids: Tuple[str, ...]
    errors: Tuple[str, ...]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "projectKey": self.project_key,
            "projectName": self.project_name,
            "pythonCodeEnv": self.python_code_env,
            "webappPythonCodeEnvs": ", ".join(self.webapp_python_code_envs),
            "agentToolCodeEnvs": ", ".join(self.agent_tool_code_envs),
            "snowflakeConnections": ", ".join(self.snowflake_connections),
            "openaiConnections": ", ".join(self.openai_connections),
            "openaiLLMIds": ", ".join(self.openai_llm_ids),
            "errors": "\n".join(self.errors),
        }


def _as_sorted_tuple(values: Iterable[str]) -> Tuple[str, ...]:
    return tuple(sorted({v for v in values if v}))


def _extract_project_python_code_env(project_settings_raw: Mapping[str, Any]) -> str:
    python_settings = (
        project_settings_raw.get("settings", {})
        .get("codeEnvs", {})
        .get("python", {})
    )
    if python_settings.get("mode") == "EXPLICIT_ENV" and python_settings.get("envName"):
        return str(python_settings["envName"])
    return "BUILTIN"


def _extract_webapp_python_code_env(webapp_settings_raw: Mapping[str, Any]) -> Optional[str]:
    env_selection = webapp_settings_raw.get("params", {}).get("envSelection", {})
    if env_selection.get("envMode") == "EXPLICIT_ENV" and env_selection.get("envName"):
        return str(env_selection["envName"])
    return None


def _parse_llm_id_for_openai(llm_id: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Returns (provider, connection_name) when it looks like an OpenAI-family LLM id.

    Examples (common in DSS):
    - openai:CONNECTION:MODEL
    - azureopenai:CONNECTION:DEPLOYMENT
    """
    if not llm_id or ":" not in llm_id:
        return (None, None)

    provider = llm_id.split(":", 1)[0].lower()
    if provider not in {"openai", "azureopenai"}:
        return (None, None)

    parts = llm_id.split(":")
    if len(parts) >= 2 and parts[1]:
        return (provider, parts[1])
    return (provider, None)

def _deep_collect_string_values_for_keys(
    obj: Any, keys_lower: Set[str]
) -> List[str]:
    found: List[str] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            try:
                k_lower = str(k).lower()
            except Exception:
                k_lower = ""
            if k_lower in keys_lower and isinstance(v, str) and v.strip():
                found.append(v.strip())
            found.extend(_deep_collect_string_values_for_keys(v, keys_lower))
    elif isinstance(obj, list):
        for v in obj:
            found.extend(_deep_collect_string_values_for_keys(v, keys_lower))
    return found


def collect_instance_project_usage(
    client: dataikuapi.DSSClient,
    *,
    project_keys: Optional[Sequence[str]] = None,
    include_llm_purposes: Sequence[str] = (
        "GENERIC_COMPLETION",
        "TEXT_EMBEDDING_EXTRACTION",
        "IMAGE_GENERATION",
        "RERANKING",
        "IMAGE_EMBEDDING_EXTRACTION",
    ),
) -> List[ProjectUsageRow]:
    """
    Collect per-project usage info from a DSS instance.

    Read-only: does not modify projects.
    """

    allowed: Optional[Set[str]] = set(project_keys) if project_keys else None

    projects = client.list_projects()
    rows: List[ProjectUsageRow] = []

    for p in projects:
        project_key = str(p.get("projectKey") or p.get("key") or "")
        if not project_key:
            continue
        if allowed is not None and project_key not in allowed:
            continue

        project_name = str(p.get("name") or "")
        errors: List[str] = []

        snowflake_connections: Set[str] = set()
        openai_connections: Set[str] = set()
        openai_llm_ids: Set[str] = set()
        webapp_envs: Set[str] = set()
        agent_tool_envs: Set[str] = set()
        python_env = "UNKNOWN"

        try:
            project = client.get_project(project_key)

            try:
                python_env = _extract_project_python_code_env(
                    project.get_settings().get_raw()
                )
            except Exception as e:
                errors.append(f"project settings: {e!r}")

            try:
                for ds_item in project.list_datasets(as_type="listitems"):
                    try:
                        if "snowflake" in str(ds_item.type).lower() and ds_item.connection:
                            snowflake_connections.add(str(ds_item.connection))
                    except Exception:
                        continue
            except Exception as e:
                errors.append(f"datasets: {e!r}")

            try:
                for webapp_item in project.list_webapps(as_type="objects"):
                    try:
                        ws = webapp_item.get_settings().get_raw()
                        env_name = _extract_webapp_python_code_env(ws)
                        if env_name:
                            webapp_envs.add(env_name)
                    except Exception:
                        continue
            except Exception as e:
                errors.append(f"webapps: {e!r}")

            try:
                # Agent tool code envs are not part of project settings; they live on the tools themselves.
                # We attempt a best-effort extraction by looking for common key names in the tool settings.
                env_keys = {
                    "codeenv",
                    "codeenvname",
                    "codeenvid",
                    "pythoncodeenv",
                    "pythoncodeenvname",
                    "pythonenv",
                    "pythonenvname",
                    "envname",
                }
                for tool in project.list_agent_tools(as_type="objects", include_shared=True):
                    try:
                        tool_settings = tool.get_settings().get_raw()
                        agent_tool_envs.update(
                            _deep_collect_string_values_for_keys(tool_settings, env_keys)
                        )
                        try:
                            tool_descriptor = tool.get_descriptor()
                            agent_tool_envs.update(
                                _deep_collect_string_values_for_keys(tool_descriptor, env_keys)
                            )
                        except Exception:
                            pass
                    except Exception:
                        continue
            except Exception as e:
                errors.append(f"agent tools: {e!r}")

            try:
                seen_llm_ids: Set[str] = set()
                for purpose in include_llm_purposes:
                    try:
                        for llm_item in project.list_llms(purpose=purpose, as_type="listitems"):
                            llm_id = str(llm_item.id)
                            if llm_id in seen_llm_ids:
                                continue
                            seen_llm_ids.add(llm_id)

                            provider, conn = _parse_llm_id_for_openai(llm_id)
                            if provider is None:
                                continue
                            openai_llm_ids.add(llm_id)
                            if conn:
                                openai_connections.add(conn)
                    except Exception:
                        # Purpose may not exist depending on DSS version/features; ignore.
                        continue
            except Exception as e:
                errors.append(f"llms: {e!r}")

        except Exception as e:
            errors.append(f"project handle: {e!r}")

        rows.append(
            ProjectUsageRow(
                project_key=project_key,
                project_name=project_name,
                python_code_env=python_env,
                webapp_python_code_envs=_as_sorted_tuple(webapp_envs),
                agent_tool_code_envs=_as_sorted_tuple(agent_tool_envs),
                snowflake_connections=_as_sorted_tuple(snowflake_connections),
                openai_connections=_as_sorted_tuple(openai_connections),
                openai_llm_ids=_as_sorted_tuple(openai_llm_ids),
                errors=tuple(errors),
            )
        )

    return rows
