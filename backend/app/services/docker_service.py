"""
Docker Service - Container management for Galatea

Allows Gala to manage Docker containers via voice commands:
- List containers
- Start/stop/restart containers
- Check container health
- View container logs

This is a simplified MCP-style service using Docker SDK directly.
"""

import asyncio
from typing import Optional
from dataclasses import dataclass

try:
    import docker
    from docker.errors import NotFound, APIError
    DOCKER_AVAILABLE = True
except ImportError:
    DOCKER_AVAILABLE = False
    docker = None


@dataclass
class ContainerInfo:
    """Container information."""
    id: str
    name: str
    status: str
    image: str
    ports: dict
    created: str


class DockerService:
    """Service for managing Docker containers."""
    
    def __init__(self):
        self._client = None
        self._connected = False
    
    def _get_client(self):
        """Get or create Docker client."""
        if not DOCKER_AVAILABLE:
            raise RuntimeError("Docker SDK not installed. Run: pip install docker")
        
        if self._client is None:
            try:
                self._client = docker.from_env()
                self._client.ping()
                self._connected = True
            except Exception as e:
                self._connected = False
                raise RuntimeError(f"Cannot connect to Docker: {e}")
        
        return self._client
    
    @property
    def is_available(self) -> bool:
        """Check if Docker is available."""
        if not DOCKER_AVAILABLE:
            return False
        try:
            self._get_client()
            return True
        except:
            return False
    
    async def list_containers(self, all_containers: bool = True) -> list[ContainerInfo]:
        """List all containers."""
        def _list():
            client = self._get_client()
            containers = client.containers.list(all=all_containers)
            return [
                ContainerInfo(
                    id=c.short_id,
                    name=c.name,
                    status=c.status,
                    image=c.image.tags[0] if c.image.tags else c.image.short_id,
                    ports=c.ports,
                    created=str(c.attrs.get('Created', ''))[:19]
                )
                for c in containers
            ]
        
        return await asyncio.to_thread(_list)
    
    async def get_container(self, name_or_id: str) -> Optional[ContainerInfo]:
        """Get a specific container by name or ID."""
        def _get():
            client = self._get_client()
            try:
                c = client.containers.get(name_or_id)
                return ContainerInfo(
                    id=c.short_id,
                    name=c.name,
                    status=c.status,
                    image=c.image.tags[0] if c.image.tags else c.image.short_id,
                    ports=c.ports,
                    created=str(c.attrs.get('Created', ''))[:19]
                )
            except NotFound:
                return None
        
        return await asyncio.to_thread(_get)
    
    async def start_container(self, name_or_id: str) -> tuple[bool, str]:
        """Start a container."""
        def _start():
            client = self._get_client()
            try:
                container = client.containers.get(name_or_id)
                if container.status == 'running':
                    return True, f"Container {container.name} is already running"
                container.start()
                return True, f"Started container {container.name}"
            except NotFound:
                return False, f"Container '{name_or_id}' not found"
            except APIError as e:
                return False, f"Failed to start: {str(e)}"
        
        return await asyncio.to_thread(_start)
    
    async def stop_container(self, name_or_id: str) -> tuple[bool, str]:
        """Stop a container."""
        def _stop():
            client = self._get_client()
            try:
                container = client.containers.get(name_or_id)
                if container.status != 'running':
                    return True, f"Container {container.name} is already stopped"
                container.stop(timeout=10)
                return True, f"Stopped container {container.name}"
            except NotFound:
                return False, f"Container '{name_or_id}' not found"
            except APIError as e:
                return False, f"Failed to stop: {str(e)}"
        
        return await asyncio.to_thread(_stop)
    
    async def restart_container(self, name_or_id: str) -> tuple[bool, str]:
        """Restart a container."""
        def _restart():
            client = self._get_client()
            try:
                container = client.containers.get(name_or_id)
                container.restart(timeout=10)
                return True, f"Restarted container {container.name}"
            except NotFound:
                return False, f"Container '{name_or_id}' not found"
            except APIError as e:
                return False, f"Failed to restart: {str(e)}"
        
        return await asyncio.to_thread(_restart)
    
    async def get_logs(self, name_or_id: str, tail: int = 20) -> tuple[bool, str]:
        """Get container logs."""
        def _logs():
            client = self._get_client()
            try:
                container = client.containers.get(name_or_id)
                logs = container.logs(tail=tail, timestamps=False).decode('utf-8')
                return True, logs if logs else "No logs available"
            except NotFound:
                return False, f"Container '{name_or_id}' not found"
            except APIError as e:
                return False, f"Failed to get logs: {str(e)}"
        
        return await asyncio.to_thread(_logs)
    
    async def get_container_health(self, name_or_id: str) -> dict:
        """Get detailed container health info."""
        def _health():
            client = self._get_client()
            try:
                container = client.containers.get(name_or_id)
                stats = container.stats(stream=False)
                
                # Calculate CPU usage
                cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - \
                           stats['precpu_stats']['cpu_usage']['total_usage']
                system_delta = stats['cpu_stats']['system_cpu_usage'] - \
                              stats['precpu_stats']['system_cpu_usage']
                cpu_percent = (cpu_delta / system_delta) * 100 if system_delta > 0 else 0
                
                # Calculate memory usage
                mem_usage = stats['memory_stats'].get('usage', 0)
                mem_limit = stats['memory_stats'].get('limit', 1)
                mem_percent = (mem_usage / mem_limit) * 100
                
                return {
                    'name': container.name,
                    'status': container.status,
                    'cpu_percent': round(cpu_percent, 2),
                    'memory_mb': round(mem_usage / (1024 * 1024), 2),
                    'memory_percent': round(mem_percent, 2),
                    'healthy': container.status == 'running'
                }
            except NotFound:
                return {'error': f"Container '{name_or_id}' not found"}
            except Exception as e:
                return {'error': str(e)}
        
        return await asyncio.to_thread(_health)
    
    def find_container_by_partial_name(self, partial_name: str) -> Optional[str]:
        """Find container by partial name match."""
        if not self.is_available:
            return None
        
        try:
            client = self._get_client()
            containers = client.containers.list(all=True)
            
            # Normalize search term
            search = partial_name.lower().replace('-', '').replace('_', '')
            
            for c in containers:
                name = c.name.lower().replace('-', '').replace('_', '')
                # Check for common aliases
                if search in name:
                    return c.name
                # Handle common voice transcription variations
                if search == 'whisper' and 'whisper' in name:
                    return c.name
                if search == 'piper' and 'piper' in name:
                    return c.name
                if search == 'kokoro' and 'kokoro' in name:
                    return c.name
                if search == 'ollama' and 'ollama' in name:
                    return c.name
                if search == 'vision' and 'vision' in name:
                    return c.name
                if search == 'backend' and 'backend' in name:
                    return c.name
                if search == 'frontend' and 'frontend' in name:
                    return c.name
            
            return None
        except:
            return None


# Global service instance
docker_service = DockerService()
