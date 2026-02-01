from typing import Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from app.docker_client import DockerClient

router = APIRouter(prefix="/api/v1", tags=["metrics"])
docker_client = DockerClient()


class ContainerResponse(BaseModel):
    id: str = Field(..., description="Container ID (first 12 characters)")
    name: str = Field(..., description="Container name")
    image: str = Field(..., description="Container image name")
    status: str = Field(..., description="Container status")


class ContainerStatsResponse(BaseModel):
    container_id: str = Field(..., description="Container ID")
    cpu_percent: float = Field(..., description="CPU usage percentage")
    memory_usage_bytes: int = Field(..., description="Memory usage in bytes")
    memory_limit_bytes: int = Field(..., description="Memory limit in bytes")
    memory_percent: float = Field(..., description="Memory usage percentage")
    network_rx_bytes: int = Field(..., description="Network received bytes")
    network_tx_bytes: int = Field(..., description="Network transmitted bytes")


class ContainerMetadataResponse(BaseModel):
    name: str = Field(..., description="Container name")
    image: str = Field(..., description="Container image")
    status: str = Field(..., description="Container status")
    created: str = Field(..., description="Container creation timestamp")
    ports: dict[str, Any] = Field(..., description="Container port mappings")


@router.get("/containers", response_model=list[ContainerResponse])
async def list_containers() -> list[ContainerResponse]:
    try:
        containers = docker_client.list_running_containers()
        return [ContainerResponse(**container) for container in containers]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/containers/{container_id}/stats", response_model=ContainerStatsResponse)
async def get_container_stats(container_id: str) -> ContainerStatsResponse:
    try:
        stats = docker_client.get_container_stats(container_id)
        return ContainerStatsResponse(**stats)
    except Exception as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=404, detail=f"Container {container_id} not found") from e
        raise HTTPException(status_code=500, detail=error_msg) from e


@router.get("/containers/{container_id}/logs")
async def get_container_logs(
    container_id: str,
    tail: int = Query(default=100, ge=1, le=10000, description="Number of lines to return"),
    follow: bool = Query(  # noqa: ARG001
        default=False, description="Follow log output (ignored for HTTP; use WebSocket for streaming)"
    ),
) -> dict[str, Any]:
    try:
        container = docker_client.client.containers.get(container_id)
        logs = container.logs(tail=tail, follow=False).decode("utf-8")
        return {"container_id": container_id, "logs": logs, "lines": len(logs.splitlines())}
    except Exception as e:
        error_msg = str(e)
        if "not found" in error_msg.lower() or "No such container" in error_msg:
            raise HTTPException(status_code=404, detail=f"Container {container_id} not found") from e
        raise HTTPException(status_code=500, detail=f"Failed to get container logs: {e}") from e


@router.get("/metrics")
async def get_prometheus_metrics() -> str:
    try:
        containers = docker_client.list_running_containers()
        container_count = len(containers)

        metrics_lines = [
            "# HELP sentinel_container_count Total number of running containers",
            "# TYPE sentinel_container_count gauge",
            f"sentinel_container_count {container_count}",
        ]
        for container in containers:
            try:
                c_id, c_name = container["id"], container["name"].replace("-", "_")
                stats = docker_client.get_container_stats(c_id)
                base = f'id="{c_id}",name="{c_name}"'

                metrics_lines.extend(
                    [
                        f"sentinel_container_cpu_percent{{{base}}} {stats['cpu_percent']}",
                        f'sentinel_container_memory_bytes{{{base},type="usage"}} {stats["memory_usage_bytes"]}',
                        f'sentinel_container_memory_bytes{{{base},type="limit"}} {stats["memory_limit_bytes"]}',
                        f'sentinel_container_network_bytes{{{base},direction="rx"}} {stats["network_rx_bytes"]}',
                        f'sentinel_container_network_bytes{{{base},direction="tx"}} {stats["network_tx_bytes"]}',
                    ]
                )
            except Exception:
                continue

        return "\n".join(metrics_lines)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate metrics: {e}") from e
