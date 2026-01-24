"""Docker client wrapper for container monitoring"""

from typing import Any

import docker
from docker.errors import APIError, DockerException

_ZERO = 0.0


class DockerClient:
    def __init__(self) -> None:
        try:
            self.client = docker.from_env()
            self.client.ping()
        except DockerException as e:
            raise DockerException("Error initializing Docker client") from e

    def list_running_containers(self) -> list[dict[str, Any]]:
        try:
            containers = self.client.containers.list(all=False)

            running_containers = []

            for container in containers:
                running_containers.append(
                    {
                        "id": container.id[:12],
                        "name": container.name,
                        "image": container.image.tags[0] if container.image.tags else "unknown",
                        "status": container.status,
                    }
                )

        except (DockerException, APIError) as e:
            raise DockerException("Error listing running containers") from e
        else:
            return running_containers

    def get_container_stats(self, container_id: str) -> dict[str, Any]:
        try:
            container = self.client.containers.get(container_id)
            stats = container.stats(stream=False)

            cpu_stats = stats["cpu_stats"]
            pre_cpu_stats = stats["precpu_stats"]
            total_usage = cpu_stats["cpu_usage"]["total_usage"]
            prev_usage = pre_cpu_stats["cpu_usage"]["total_usage"]
            cpu_delta = total_usage - prev_usage
            system_delta = cpu_stats["system_cpu_usage"] - pre_cpu_stats["system_cpu_usage"]
            online_cpus = cpu_stats.get("online_cpus", 1)
            cpu_percent = 0.0

            if system_delta > _ZERO:
                cpu_percent = (cpu_delta / system_delta) * online_cpus * 100.0

            memory_stats = stats.get("memory_stats", {})
            memory_usage = memory_stats.get("usage", 0)
            memory_limit = memory_stats.get("limit", 0)
            memory_percent = 0.0
            if memory_limit > 0:
                memory_percent = (memory_usage / memory_limit) * 100.0

            network_stats = stats.get("networks", {})
            network_rx = 0
            network_tx = 0

            for network in network_stats.values():
                network_rx += network.get("rx_bytes", 0)
                network_tx += network.get("tx_bytes", 0)

            return {
                "container_id": container_id,
                "cpu_percent": round(cpu_percent, 2),
                "memory_usage_bytes": memory_usage,
                "memory_limit_bytes": memory_limit,
                "memory_percent": round(memory_percent, 2),
                "network_rx_bytes": network_rx,
                "network_tx_bytes": network_tx,
            }
        except docker.errors.NotFound as e:
            raise DockerException("Container not found") from e
        except (DockerException, APIError) as e:
            raise DockerException("Error getting container stats") from e

    def get_container_metadata(self, container_id: str) -> dict[str, Any]:
        try:
            container = self.client.containers.get(container_id)
            return {
                "name": container.name,
                "image": container.image.tags[0] if container.image.tags else "unknown",
                "status": container.status,
                "created": container.attrs["Created"],
                "ports": container.ports,
            }
        except docker.errors.NotFound as e:
            msg = f"Container {container_id} not found"
            raise DockerException(msg) from e
        except (DockerException, APIError) as e:
            msg = f"Error getting container metadata: {e}"
            raise DockerException(msg) from e
