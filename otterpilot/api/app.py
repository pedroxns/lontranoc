from __future__ import annotations

import socket
import subprocess
import time
from datetime import datetime, timezone
from importlib import resources
from typing import Any

import yaml
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from otterpilot.api import auth
from otterpilot.api.catalog import (
    SettingsValidationError,
    all_groups,
    describe_group,
    find_group,
    update_group,
)
from otterpilot.copilot.service import answer_question
from otterpilot.core.config import (
    CONFIG_DIR,
    NotConfiguredError,
    PROJECT_ROOT,
    config_path,
    connector_enabled,
    update_env_file,
    write_config_file,
)
from otterpilot.core.registry.bootstrap import build_default_registry
from otterpilot.core.registry.executor_bootstrap import build_default_executor
from otterpilot.integrations.mqtt.client import check_connection as check_mqtt
from otterpilot.core.scheduler.bootstrap import DEFAULT_JOBS
from otterpilot.core.scheduler.scheduler import effective_interval, interval_override_key
from otterpilot.knowledge.providers.openobserve import search as history
from otterpilot.overview.system import _age_seconds, _is_stale, build_overview
from otterpilot.state import DEFAULT_STATE_DB, build_default_state_store
from otterpilot.version import __version__

SERVICE_UNITS = (
    "otterpilot-scheduler",
    "otterpilot-zigbee2mqtt",
    "otterpilot-frigate",
    "otterpilot-copilot",
    "otterpilot-api",
)

EDITABLE_CONFIG_FILES = ("proxmox.yaml", "vehicle.yaml")

ACTIVITY_CACHE_SECONDS = 30
_activity_cache: dict[int, tuple[float, dict[str, Any]]] = {}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------- modelos


class LoginRequest(BaseModel):
    password: str


class PasswordChange(BaseModel):
    current: str
    new: str = Field(min_length=auth.MIN_PASSWORD_LENGTH)


class SettingsUpdate(BaseModel):
    values: dict[str, Any] = Field(default_factory=dict)
    enabled: bool | None = None


class IntervalUpdate(BaseModel):
    interval_seconds: int | None = Field(default=None, ge=10, le=86400)


class CopilotQuery(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


class ConfigFileUpdate(BaseModel):
    content: str = Field(max_length=200_000)


class WorkloadPolicy(BaseModel):
    name: str | None = None
    expected_state: str | None = Field(default=None, pattern="^(running|stopped)$")
    importance: str | None = Field(default=None, pattern="^(critical|warning)$")


class PoliciesUpdate(BaseModel):
    workloads: dict[str, WorkloadPolicy]


# ---------------------------------------------------------------- helpers


def require_session(request: Request) -> None:
    if not auth.validate_session(request.cookies.get(auth.SESSION_COOKIE)):
        raise HTTPException(status_code=401, detail="Sessão expirada ou inválida")


def _client(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _resource_view(state: dict[str, Any]) -> dict[str, Any]:
    try:
        age = round(_age_seconds(state["timestamp"]))
    except (TypeError, ValueError):
        age = None

    payload = state.get("payload") or {}

    return {
        **state,
        "name": payload.get("name") or payload.get("camera") or payload.get("instance"),
        "age_seconds": age,
        "stale": _is_stale(state),
    }


def _job_rows() -> list[dict[str, Any]]:
    recorded = {row["job_id"]: row for row in build_default_state_store().list_job_status()}
    rows = []

    for job in DEFAULT_JOBS:
        row = recorded.get(job.job_id, {})
        rows.append(
            {
                "job_id": job.job_id,
                "connector_id": job.connector_id,
                "capability_id": job.capability_id,
                "default_interval_seconds": job.interval_seconds,
                "interval_seconds": effective_interval(job),
                "interval_overridden": effective_interval(job) != job.interval_seconds,
                "enabled": connector_enabled(job.connector_id),
                "outcome": row.get("outcome", "pending"),
                "last_run_at": row.get("last_run_at"),
                "last_success_at": row.get("last_success_at"),
                "last_error_at": row.get("last_error_at"),
                "last_error": row.get("last_error"),
                "consecutive_failures": row.get("consecutive_failures", 0),
                "duration_ms": row.get("duration_ms"),
                "resource_count": row.get("resource_count"),
            }
        )

    return rows


def _unit_status(unit: str) -> dict[str, Any]:
    properties = ("ActiveState", "SubState", "ActiveEnterTimestamp", "NRestarts", "UnitFileState")

    try:
        output = subprocess.run(
            ["systemctl", "show", f"{unit}.service", *(f"--property={p}" for p in properties)],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        ).stdout
    except (OSError, subprocess.TimeoutExpired):
        return {"unit": unit, "active_state": "unknown"}

    values = dict(line.split("=", 1) for line in output.splitlines() if "=" in line)

    return {
        "unit": unit,
        "active_state": values.get("ActiveState", "unknown"),
        "sub_state": values.get("SubState"),
        "since": values.get("ActiveEnterTimestamp") or None,
        "restarts": int(values["NRestarts"]) if values.get("NRestarts", "").isdigit() else None,
        "unit_file_state": values.get("UnitFileState"),
    }


def _test_step(label: str, action) -> dict[str, Any]:
    started = time.monotonic()

    try:
        detail = action()
        ok, not_configured = True, False
    except NotConfiguredError as error:
        detail, ok, not_configured = str(error), False, True
    except Exception as error:
        detail, ok, not_configured = str(error), False, False

    return {
        "label": label,
        "ok": ok,
        "not_configured": not_configured,
        "detail": detail,
        "duration_ms": round((time.monotonic() - started) * 1000),
    }


def _describe_collection(payload: Any) -> str:
    count = len(payload) if isinstance(payload, list) else 1
    return f"{count} recurso(s) coletado(s)"


def run_connection_test(group_id: str) -> list[dict[str, Any]]:
    if group_id == "mqtt":
        return [_test_step("Broker MQTT", check_mqtt)]

    if group_id == "openobserve":
        return [
            _test_step(
                "Consulta ao OpenObserve",
                lambda: f"{len(history.list_streams())} stream(s) encontrado(s)",
            )
        ]

    executor = build_default_executor()
    jobs = [job for job in DEFAULT_JOBS if job.connector_id == group_id]

    results = [
        _test_step(
            f"Coleta {job.capability_id}",
            lambda job=job: _describe_collection(
                executor.collect(job.connector_id, job.capability_id)
            ),
        )
        for job in jobs
    ]

    if not jobs:
        # Integrações por eventos (ex.: Zigbee2MQTT) dependem só do broker.
        results.append(_test_step("Broker MQTT", check_mqtt))

    return results


def _load_proxmox_document() -> dict[str, Any]:
    path = config_path("proxmox.yaml", must_exist=False)

    if not path.is_file():
        return {}

    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _validate_config_file(name: str, content: str) -> None:
    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError as error:
        raise HTTPException(status_code=422, detail=f"YAML inválido: {error}") from error

    if name == "proxmox.yaml":
        if not isinstance(data, dict) or not isinstance(data.get("proxmox"), dict):
            raise HTTPException(status_code=422, detail="O arquivo precisa da seção 'proxmox'")

    if name == "vehicle.yaml":
        if not isinstance(data, dict) or not isinstance(data.get("vehicle"), dict):
            raise HTTPException(status_code=422, detail="O arquivo precisa da seção 'vehicle'")


# ---------------------------------------------------------------- app


def create_app() -> FastAPI:
    app = FastAPI(title="OtterPilot", version=__version__, docs_url=None, redoc_url=None)
    api = Depends(require_session)

    static_dir = resources.files("otterpilot.web").joinpath("static")

    # ---- público

    @app.get("/api/health")
    def health() -> dict[str, Any]:
        return {"status": "ok", "version": __version__}

    @app.get("/api/auth/session")
    def session(request: Request) -> dict[str, Any]:
        return {
            "authenticated": auth.validate_session(request.cookies.get(auth.SESSION_COOKIE)),
            "password_configured": auth.password_configured(),
            "version": __version__,
        }

    @app.post("/api/auth/login")
    def login(body: LoginRequest, request: Request, response: Response) -> dict[str, Any]:
        client = _client(request)

        if not auth.password_configured():
            raise HTTPException(
                status_code=503,
                detail="Senha de administrador não definida. Execute: sudo otterpilot set-password",
            )

        if not auth.login_allowed(client):
            raise HTTPException(status_code=429, detail="Muitas tentativas. Aguarde alguns minutos.")

        if not auth.verify_password(body.password, auth.load_auth()["password_hash"]):
            auth.register_failure(client)
            time.sleep(1)
            raise HTTPException(status_code=401, detail="Senha incorreta")

        auth.reset_failures(client)
        response.set_cookie(
            auth.SESSION_COOKIE,
            auth.create_session(),
            max_age=auth.SESSION_TTL_SECONDS,
            httponly=True,
            samesite="strict",
            secure=request.url.scheme == "https",
        )

        return {"authenticated": True}

    @app.post("/api/auth/logout")
    def logout(response: Response) -> dict[str, Any]:
        response.delete_cookie(auth.SESSION_COOKIE)
        return {"authenticated": False}

    # ---- autenticado

    @app.post("/api/auth/password", dependencies=[api])
    def change_password(body: PasswordChange, response: Response, request: Request):
        if not auth.verify_password(body.current, auth.load_auth()["password_hash"]):
            raise HTTPException(status_code=401, detail="Senha atual incorreta")

        auth.set_password(body.new)
        response.set_cookie(
            auth.SESSION_COOKIE,
            auth.create_session(),
            max_age=auth.SESSION_TTL_SECONDS,
            httponly=True,
            samesite="strict",
            secure=request.url.scheme == "https",
        )

        return {"changed": True}

    @app.get("/api/system", dependencies=[api])
    def system() -> dict[str, Any]:
        return {**build_overview(), "generated_at": now_iso(), "version": __version__}

    @app.get("/api/resources", dependencies=[api])
    def resources_list(
        capability: str | None = None,
        connector: str | None = None,
        status: str | None = None,
        q: str | None = None,
    ) -> list[dict[str, Any]]:
        items = [
            _resource_view(state)
            for state in build_default_state_store().list_all()
            if state["capability"] != "system_health"
        ]

        if capability:
            items = [item for item in items if item["capability"] == capability]

        if connector:
            items = [item for item in items if item["connector"] == connector]

        if status:
            items = [item for item in items if item["status"] == status]

        if q:
            needle = q.lower()
            items = [
                item
                for item in items
                if needle in item["resource_id"].lower()
                or needle in str(item.get("name") or "").lower()
            ]

        return items

    @app.get("/api/resources/{connector}/{capability}/{resource_id:path}", dependencies=[api])
    def resource_detail(connector: str, capability: str, resource_id: str) -> dict[str, Any]:
        state = build_default_state_store().get(
            connector=connector, capability=capability, resource_id=resource_id
        )

        if state is None:
            raise HTTPException(status_code=404, detail="Recurso não encontrado")

        return _resource_view(state)

    @app.delete("/api/resources/{connector}/{capability}/{resource_id:path}", dependencies=[api])
    def resource_forget(connector: str, capability: str, resource_id: str) -> dict[str, Any]:
        removed = build_default_state_store().delete(
            connector=connector, capability=capability, resource_id=resource_id
        )

        if not removed:
            raise HTTPException(status_code=404, detail="Recurso não encontrado")

        return {"removed": True}

    @app.get("/api/capabilities", dependencies=[api])
    def capabilities() -> list[dict[str, Any]]:
        registry = build_default_registry()
        stats = build_overview()["by_capability"]

        return [
            {
                "id": capability.capability_id,
                "name": capability.display_name,
                "domain": capability.domain,
                "description": capability.description,
                "connectors": [c.connector_id for c in registry.connectors_for_capability(capability.capability_id)],
                "stats": stats.get(capability.capability_id, {"total": 0, "healthy": 0, "problem": 0, "stale": 0}),
            }
            for capability in registry.list_capabilities()
        ]

    @app.get("/api/connectors", dependencies=[api])
    def connectors() -> list[dict[str, Any]]:
        registry = build_default_registry()
        store = build_default_state_store()
        jobs = _job_rows()
        components = {row["component"]: row for row in store.list_component_status()}
        states = store.list_all()
        groups = {group.group_id: group for group in all_groups()}

        result = []

        for connector in registry.list_connectors():
            group = groups.get(connector.connector_id)
            described = describe_group(group) if group else {"configured": True, "missing": [], "settings": []}

            result.append(
                {
                    "id": connector.connector_id,
                    "name": connector.display_name,
                    "description": connector.description,
                    "capabilities": list(connector.capabilities),
                    "internal": not connector.settings,
                    "enabled": connector_enabled(connector.connector_id),
                    "configured": described["configured"],
                    "missing": described["missing"],
                    "jobs": [job for job in jobs if job["connector_id"] == connector.connector_id],
                    "components": [
                        components.get(name, {"component": name, "status": "unknown"})
                        for name in connector.push_components
                    ],
                    "resource_count": sum(1 for state in states if state["connector"] == connector.connector_id),
                }
            )

        return result

    @app.get("/api/jobs", dependencies=[api])
    def jobs() -> list[dict[str, Any]]:
        return _job_rows()

    @app.put("/api/jobs/{job_id}", dependencies=[api])
    def update_job(job_id: str, body: IntervalUpdate) -> list[dict[str, Any]]:
        job = next((job for job in DEFAULT_JOBS if job.job_id == job_id), None)

        if job is None:
            raise HTTPException(status_code=404, detail="Job não encontrado")

        value = body.interval_seconds
        update_env_file(
            {
                interval_override_key(job): (
                    None if value in (None, job.interval_seconds) else str(value)
                )
            }
        )

        return _job_rows()

    @app.get("/api/settings", dependencies=[api])
    def settings() -> list[dict[str, Any]]:
        return [describe_group(group) for group in all_groups()]

    @app.put("/api/settings/{group_id}", dependencies=[api])
    def settings_update(group_id: str, body: SettingsUpdate) -> dict[str, Any]:
        try:
            group = find_group(group_id)
        except KeyError as error:
            raise HTTPException(status_code=404, detail="Grupo de configuração desconhecido") from error

        try:
            return update_group(group, body.values, body.enabled)
        except SettingsValidationError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @app.post("/api/settings/{group_id}/test", dependencies=[api])
    def settings_test(group_id: str) -> dict[str, Any]:
        try:
            find_group(group_id)
        except KeyError as error:
            raise HTTPException(status_code=404, detail="Grupo de configuração desconhecido") from error

        return {"results": run_connection_test(group_id)}

    @app.get("/api/policies/virtualization", dependencies=[api])
    def policies() -> dict[str, Any]:
        document = _load_proxmox_document()
        workloads = (document.get("proxmox") or {}).get("workloads") or {}
        store = build_default_state_store()

        guests = [
            {
                "resource_id": state["resource_id"],
                "name": state["payload"].get("name"),
                "node": state["payload"].get("node"),
                "proxmox_status": state["payload"].get("proxmox_status"),
                "status": state["status"],
            }
            for state in store.list_all()
            if state["capability"] == "virtualization"
        ]

        return {"workloads": workloads, "guests": guests}

    @app.put("/api/policies/virtualization", dependencies=[api])
    def policies_update(body: PoliciesUpdate) -> dict[str, Any]:
        document = _load_proxmox_document()
        section = document.setdefault("proxmox", {})

        section["workloads"] = {
            resource_id: {
                key: value
                for key, value in policy.model_dump().items()
                if value is not None
            }
            for resource_id, policy in sorted(body.workloads.items())
            if policy.expected_state or policy.importance
        }

        write_config_file(
            "proxmox.yaml",
            yaml.safe_dump(document, allow_unicode=True, sort_keys=False),
        )

        return policies()

    @app.get("/api/config-files", dependencies=[api])
    def config_files() -> list[dict[str, Any]]:
        files = []

        for name in EDITABLE_CONFIG_FILES:
            path = CONFIG_DIR / name
            files.append(
                {
                    "name": name,
                    "exists": path.is_file(),
                    "content": path.read_text(encoding="utf-8") if path.is_file() else "",
                }
            )

        return files

    @app.put("/api/config-files/{name}", dependencies=[api])
    def config_file_update(name: str, body: ConfigFileUpdate) -> dict[str, Any]:
        if name not in EDITABLE_CONFIG_FILES:
            raise HTTPException(status_code=404, detail="Arquivo não editável")

        _validate_config_file(name, body.content)
        write_config_file(name, body.content)

        return {"name": name, "saved": True}

    @app.post("/api/copilot/query", dependencies=[api])
    def copilot(body: CopilotQuery) -> dict[str, Any]:
        return answer_question(body.question.strip(), source="web")

    @app.get("/api/activity", dependencies=[api])
    def activity(hours: int = 24) -> dict[str, Any]:
        hours = max(1, min(hours, 168))
        cached = _activity_cache.get(hours)

        if cached and time.monotonic() - cached[0] < ACTIVITY_CACHE_SECONDS:
            return cached[1]

        if not history.is_configured():
            return {"available": False, "reason": "OpenObserve não configurado", "events": []}

        streams = [c.capability_id for c in build_default_registry().list_capabilities()]
        streams.append("otterpilot")

        events: list[dict[str, Any]] = []
        errors: list[str] = []

        for stream in streams:
            sql = (
                f'SELECT * FROM "{stream}" '
                "WHERE severity IN ('warning', 'error', 'critical') "
                "ORDER BY _timestamp DESC"
            )

            try:
                events.extend(history.search_logs(sql, hours=hours, size=50))
            except Exception as error:
                if "not found" not in str(error).lower():
                    errors.append(f"{stream}: {error}")

        events.sort(key=lambda event: event.get("_timestamp", 0), reverse=True)

        result = {
            "available": True,
            "hours": hours,
            "events": [
                {
                    "timestamp": event.get("timestamp"),
                    "capability": event.get("capability") or event.get("component"),
                    "connector": event.get("connector") or event.get("service"),
                    "resource_id": event.get("resource_id"),
                    "event_type": event.get("event_type"),
                    "severity": event.get("severity"),
                    "status": event.get("status"),
                    "message": event.get("message"),
                }
                for event in events[:200]
            ],
            "errors": errors[:5],
        }

        _activity_cache[hours] = (time.monotonic(), result)
        return result

    @app.get("/api/about", dependencies=[api])
    def about() -> dict[str, Any]:
        return {
            "version": __version__,
            "hostname": socket.gethostname(),
            "config_root": str(PROJECT_ROOT),
            "state_db": str(DEFAULT_STATE_DB),
            "services": [_unit_status(unit) for unit in SERVICE_UNITS],
        }

    # ---- interface web

    @app.exception_handler(404)
    async def not_found(request: Request, exc: HTTPException):
        if request.url.path.startswith("/api/"):
            return JSONResponse({"detail": getattr(exc, "detail", "Não encontrado")}, status_code=404)

        return FileResponse(str(static_dir.joinpath("index.html")))

    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(str(static_dir.joinpath("index.html")))

    return app


app = create_app()
