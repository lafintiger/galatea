"""
Home Assistant Service - Smart Home control for Galatea

Allows Gala to control smart home devices via voice commands:
- Turn lights on/off
- Set thermostat temperature
- Check device states
- Call any Home Assistant service

Requires:
- Home Assistant URL (e.g., http://homeassistant.local:8123)
- Long-lived access token from HA
"""

import httpx
from typing import Optional, Any
from dataclasses import dataclass
from ..config import settings


@dataclass 
class DeviceState:
    """Device state information."""
    entity_id: str
    state: str
    friendly_name: str
    attributes: dict


class HomeAssistantService:
    """Service for controlling Home Assistant devices."""
    
    def __init__(self):
        self._url: Optional[str] = None
        self._token: Optional[str] = None
        self._client: Optional[httpx.AsyncClient] = None
    
    def configure(self, url: str, token: str):
        """Configure Home Assistant connection."""
        self._url = url.rstrip('/')
        self._token = token
        self._client = httpx.AsyncClient(
            base_url=self._url,
            headers={"Authorization": f"Bearer {self._token}"},
            timeout=30.0
        )
    
    @property
    def is_configured(self) -> bool:
        """Check if HA is configured."""
        return self._url is not None and self._token is not None
    
    async def check_connection(self) -> tuple[bool, str]:
        """Check if we can connect to Home Assistant."""
        if not self.is_configured:
            return False, "Home Assistant not configured. Set HA_URL and HA_TOKEN."
        
        try:
            response = await self._client.get("/api/")
            if response.status_code == 200:
                return True, "Connected to Home Assistant"
            elif response.status_code == 401:
                return False, "Invalid Home Assistant token"
            else:
                return False, f"Home Assistant returned status {response.status_code}"
        except Exception as e:
            return False, f"Cannot connect to Home Assistant: {e}"
    
    async def get_states(self) -> list[DeviceState]:
        """Get all device states."""
        if not self.is_configured:
            return []
        
        try:
            response = await self._client.get("/api/states")
            if response.status_code == 200:
                states = response.json()
                return [
                    DeviceState(
                        entity_id=s['entity_id'],
                        state=s['state'],
                        friendly_name=s['attributes'].get('friendly_name', s['entity_id']),
                        attributes=s['attributes']
                    )
                    for s in states
                ]
            return []
        except Exception:
            return []
    
    async def get_state(self, entity_id: str) -> Optional[DeviceState]:
        """Get state of a specific entity."""
        if not self.is_configured:
            return None
        
        try:
            response = await self._client.get(f"/api/states/{entity_id}")
            if response.status_code == 200:
                s = response.json()
                return DeviceState(
                    entity_id=s['entity_id'],
                    state=s['state'],
                    friendly_name=s['attributes'].get('friendly_name', s['entity_id']),
                    attributes=s['attributes']
                )
            return None
        except Exception:
            return None
    
    async def call_service(
        self, 
        domain: str, 
        service: str, 
        entity_id: Optional[str] = None,
        data: Optional[dict] = None
    ) -> tuple[bool, str]:
        """
        Call a Home Assistant service.
        
        Examples:
        - domain="light", service="turn_on", entity_id="light.living_room"
        - domain="climate", service="set_temperature", data={"temperature": 72}
        """
        if not self.is_configured:
            return False, "Home Assistant not configured"
        
        try:
            payload = data or {}
            if entity_id:
                payload['entity_id'] = entity_id
            
            response = await self._client.post(
                f"/api/services/{domain}/{service}",
                json=payload
            )
            
            if response.status_code == 200:
                return True, f"Successfully called {domain}.{service}"
            else:
                return False, f"Service call failed: {response.text}"
        except Exception as e:
            return False, f"Error calling service: {e}"
    
    # =========================================
    # Convenience methods for common operations
    # =========================================
    
    async def turn_on(self, entity_id: str, **kwargs) -> tuple[bool, str]:
        """Turn on a device (light, switch, etc.)."""
        domain = entity_id.split('.')[0]
        return await self.call_service(domain, "turn_on", entity_id, kwargs)
    
    async def turn_off(self, entity_id: str) -> tuple[bool, str]:
        """Turn off a device."""
        domain = entity_id.split('.')[0]
        return await self.call_service(domain, "turn_off", entity_id)
    
    async def toggle(self, entity_id: str) -> tuple[bool, str]:
        """Toggle a device."""
        domain = entity_id.split('.')[0]
        return await self.call_service(domain, "toggle", entity_id)
    
    async def set_temperature(self, entity_id: str, temperature: float) -> tuple[bool, str]:
        """Set thermostat temperature."""
        return await self.call_service(
            "climate", 
            "set_temperature", 
            entity_id,
            {"temperature": temperature}
        )
    
    async def set_brightness(self, entity_id: str, brightness_pct: int) -> tuple[bool, str]:
        """Set light brightness (0-100%)."""
        return await self.call_service(
            "light",
            "turn_on",
            entity_id,
            {"brightness_pct": brightness_pct}
        )
    
    async def lock(self, entity_id: str) -> tuple[bool, str]:
        """Lock a lock."""
        return await self.call_service("lock", "lock", entity_id)
    
    async def unlock(self, entity_id: str) -> tuple[bool, str]:
        """Unlock a lock."""
        return await self.call_service("lock", "unlock", entity_id)
    
    # =========================================
    # Entity discovery helpers
    # =========================================
    
    async def find_entities(self, domain: Optional[str] = None, name_contains: Optional[str] = None) -> list[DeviceState]:
        """Find entities by domain and/or name."""
        states = await self.get_states()
        results = []
        
        for state in states:
            # Filter by domain
            if domain and not state.entity_id.startswith(f"{domain}."):
                continue
            
            # Filter by name
            if name_contains:
                search = name_contains.lower()
                if search not in state.entity_id.lower() and search not in state.friendly_name.lower():
                    continue
            
            results.append(state)
        
        return results
    
    async def get_lights(self) -> list[DeviceState]:
        """Get all lights."""
        return await self.find_entities(domain="light")
    
    async def get_switches(self) -> list[DeviceState]:
        """Get all switches."""
        return await self.find_entities(domain="switch")
    
    async def get_climate(self) -> list[DeviceState]:
        """Get all thermostats/climate devices."""
        return await self.find_entities(domain="climate")
    
    async def get_locks(self) -> list[DeviceState]:
        """Get all locks."""
        return await self.find_entities(domain="lock")
    
    async def get_sensors(self, name_contains: Optional[str] = None) -> list[DeviceState]:
        """Get sensors, optionally filtered by name."""
        return await self.find_entities(domain="sensor", name_contains=name_contains)
    
    def find_entity_by_name(self, states: list[DeviceState], name: str) -> Optional[DeviceState]:
        """Find an entity by friendly name or partial match."""
        name_lower = name.lower()
        
        # Exact match first
        for state in states:
            if state.friendly_name.lower() == name_lower:
                return state
        
        # Partial match
        for state in states:
            if name_lower in state.friendly_name.lower():
                return state
            if name_lower in state.entity_id.lower():
                return state
        
        return None


# Global service instance
ha_service = HomeAssistantService()


# Initialize from environment if available
def init_from_env():
    """Initialize HA service from environment variables."""
    ha_url = getattr(settings, 'ha_url', None)
    ha_token = getattr(settings, 'ha_token', None)
    
    if ha_url and ha_token:
        ha_service.configure(ha_url, ha_token)
        print(f"[HA] Configured for {ha_url}")
    else:
        print("[HA] Not configured (set HA_URL and HA_TOKEN in .env)")
