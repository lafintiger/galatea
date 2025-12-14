# Galatea MCP Integration Design

## Executive Summary

This document outlines the design for integrating Model Context Protocol (MCP) into Galatea, transforming her from a conversational assistant into an **agentic assistant** capable of taking real actions on the user's system and external services.

---

## What is MCP?

MCP (Model Context Protocol) is Anthropic's open standard for connecting AI assistants to external tools and data sources. It provides:

- **Standardized tool interface** - Any MCP server works with any MCP client
- **Security** - Sandboxed execution, credential management
- **Discoverability** - Tools self-describe their capabilities
- **Transport flexibility** - stdio, HTTP, SSE, WebSocket

---

## Architecture Options

### Option A: Direct MCP Client (Simple)

```
┌─────────────────────────────────────────────────────────────┐
│ Galatea Backend (FastAPI)                                   │
│                                                             │
│  ┌─────────────┐    ┌──────────────────────────────────┐   │
│  │ Command     │───▶│ MCP Client (Python SDK)          │   │
│  │ Router      │    │                                  │   │
│  └─────────────┘    │  ┌──────────┐ ┌──────────┐      │   │
│                     │  │ Docker   │ │ Home     │ ...  │   │
│                     │  │ MCP      │ │ Assistant│      │   │
│                     │  └──────────┘ └──────────┘      │   │
│                     └──────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

**Pros:** Simple, direct control, low latency
**Cons:** Must manage each MCP connection, harder to scale

### Option B: Docker MCP Gateway (Recommended)

```
┌─────────────────────────────────────────────────────────────┐
│ Galatea Backend                                             │
│  ┌─────────────┐    ┌──────────────────────────────────┐   │
│  │ Command     │───▶│ MCP Gateway Client               │   │
│  │ Router      │    └──────────────────────────────────┘   │
└──┼──────────────────────────────┼───────────────────────────┘
   │                              │
   ▼                              ▼
┌─────────────────────────────────────────────────────────────┐
│ Docker MCP Gateway (Container)                     :8811    │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Tool Discovery │ Routing │ Auth │ Secrets           │   │
│  └─────────────────────────────────────────────────────┘   │
│           │              │              │                   │
│           ▼              ▼              ▼                   │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐              │
│  │ Docker MCP │ │ Filesystem │ │ Home Asst  │              │
│  │ Container  │ │ Container  │ │ Container  │  ...         │
│  └────────────┘ └────────────┘ └────────────┘              │
└─────────────────────────────────────────────────────────────┘
```

**Pros:** 
- Centralized management
- All MCP servers as Docker containers (easy deployment)
- Built-in secrets/OAuth handling
- Tool discovery/cataloging
- Better isolation

**Cons:** 
- Additional container to manage
- Slightly more complex setup

### Recommendation: **Option B** 

The Docker MCP Gateway aligns perfectly with your goals:
- ✅ Easy to deploy (Docker containers)
- ✅ Hooks already exist in the gateway
- ✅ Scales to many MCP servers
- ✅ Docker Desktop integration available

---

## Proposed MCP Servers (Priority Order)

### Tier 1: High Value, Easy Setup

| Server | Capability | Voice Examples |
|--------|-----------|----------------|
| **Docker MCP** | Container management | "Restart the whisper container", "Is Ollama running?" |
| **Filesystem MCP** | Read/write files | "Save this to my notes", "Read my shopping list" |
| **Home Assistant MCP** | Smart home control | "Turn off lights", "Set temp to 72" |

### Tier 2: Productivity

| Server | Capability | Voice Examples |
|--------|-----------|----------------|
| **Google Workspace MCP** | Gmail, Calendar | "What's on my schedule?", "Send email to..." |
| **Outlook MCP** | Email, Calendar | Same as above for Microsoft users |
| **Browser (Puppeteer/Playwright)** | Web automation | "Open YouTube", "Search for..." |

### Tier 3: Developer Tools

| Server | Capability | Voice Examples |
|--------|-----------|----------------|
| **Git MCP** | Repository management | "Commit my changes", "Git status" |
| **Shell MCP** | Command execution | "Run npm install", "Check disk space" |
| **Database MCP** | SQL queries | "How many users signed up today?" |

### Tier 4: Future / Specialized

| Server | Capability | Voice Examples |
|--------|-----------|----------------|
| **Spotify MCP** | Music control | "Play my focus playlist" |
| **Todoist/Notion MCP** | Task management | "Add task to project" |
| **Weather MCP** | Weather data | Already have via web search |

---

## Implementation Plan

### Phase 1: Foundation (Week 1)

**Goal:** Get one MCP server working end-to-end

1. **Add MCP Python SDK to backend**
   ```bash
   pip install mcp
   ```

2. **Create MCP service module**
   ```
   backend/app/services/mcp_client.py
   ```

3. **Integrate with Command Router**
   - Detect when user request needs MCP tool
   - Route to appropriate MCP server
   - Return result to conversation

4. **Docker Compose addition**
   ```yaml
   services:
     mcp-filesystem:
       image: modelcontextprotocol/server-filesystem
       volumes:
         - ./data/user-files:/workspace
   ```

5. **Test with Filesystem MCP**
   - "Save note: remember to buy milk"
   - "Read my notes"

### Phase 2: Docker Gateway (Week 2)

**Goal:** Centralized MCP management

1. **Add Docker MCP Gateway**
   ```yaml
   services:
     mcp-gateway:
       image: docker/mcp-gateway
       ports:
         - "8811:8811"
       volumes:
         - /var/run/docker.sock:/var/run/docker.sock
   ```

2. **Configure gateway to manage MCP servers**

3. **Update Galatea to use gateway as single endpoint**

4. **Add Docker MCP server**
   - "Restart the piper container"
   - "What containers are running?"

### Phase 3: Home Automation (Week 3)

**Goal:** Smart home control

1. **Add Home Assistant MCP**
   - Configure with HA token
   - Expose to gateway

2. **Voice commands**
   - "Turn off the living room lights"
   - "Set thermostat to 68"
   - "Lock the front door"

### Phase 4: Productivity (Week 4+)

**Goal:** Email/Calendar integration

1. **Add Google Workspace or Outlook MCP**
2. **OAuth flow setup**
3. **Voice commands**
   - "What's on my calendar today?"
   - "Send email to John: meeting confirmed"

---

## Technical Details

### MCP Client Implementation

```python
# backend/app/services/mcp_client.py

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import httpx

class MCPService:
    """MCP client for Galatea to call external tools."""
    
    def __init__(self):
        self.gateway_url = "http://mcp-gateway:8811"
        self.sessions: dict[str, ClientSession] = {}
    
    async def list_tools(self) -> list[dict]:
        """Get all available tools from MCP gateway."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.gateway_url}/tools")
            return response.json()
    
    async def call_tool(self, tool_name: str, arguments: dict) -> dict:
        """Call an MCP tool and return result."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.gateway_url}/tools/{tool_name}",
                json={"arguments": arguments}
            )
            return response.json()
    
    def get_tool_definitions(self) -> list[dict]:
        """Get tool definitions for LLM function calling."""
        # Returns tools in Ollama/OpenAI function calling format
        pass

mcp_service = MCPService()
```

### Command Router Integration

```python
# Update to backend/app/services/command_router.py

# Add MCP tools to the TOOLS list dynamically
async def get_all_tools():
    """Combine built-in tools with MCP tools."""
    builtin_tools = TOOLS  # existing tools
    mcp_tools = await mcp_service.get_tool_definitions()
    return builtin_tools + mcp_tools

# In route() method:
if tool_name in mcp_tool_names:
    result = await mcp_service.call_tool(tool_name, tool_args)
    return {"action": "mcp_result", "result": result}
```

### Docker Compose Addition

```yaml
# Add to docker-compose.yml

services:
  # ... existing services ...

  mcp-gateway:
    image: docker/mcp-gateway:latest
    container_name: mcp-gateway
    ports:
      - "8811:8811"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - ./mcp-config:/config
    environment:
      - MCP_LOG_LEVEL=info
    restart: unless-stopped

  mcp-filesystem:
    image: modelcontextprotocol/server-filesystem:latest
    container_name: mcp-filesystem
    volumes:
      - ./data/user-files:/workspace:rw
    environment:
      - ALLOWED_DIRECTORIES=/workspace
    restart: unless-stopped

  mcp-docker:
    image: ghcr.io/modelcontextprotocol/server-docker:latest
    container_name: mcp-docker
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
    restart: unless-stopped
```

---

## Voice Command Examples (Full Integration)

| Category | Voice Command | MCP Server | Tool Called |
|----------|--------------|------------|-------------|
| **Files** | "Save this conversation" | Filesystem | write_file |
| **Files** | "Read my shopping list" | Filesystem | read_file |
| **Docker** | "Restart whisper" | Docker | container_restart |
| **Docker** | "What's using my GPU?" | Docker | container_list |
| **Smart Home** | "Turn off all lights" | Home Assistant | call_service |
| **Smart Home** | "Is the garage door closed?" | Home Assistant | get_state |
| **Calendar** | "What meetings today?" | Google/Outlook | list_events |
| **Email** | "Any urgent emails?" | Google/Outlook | search_emails |
| **Browser** | "Open my bank website" | Puppeteer | navigate |
| **System** | "How much disk space left?" | Shell | execute |

---

## Security Considerations

1. **Sandboxing**: All MCP servers run in isolated containers
2. **Secrets**: API keys stored in Docker secrets, not in code
3. **OAuth**: Gateway handles OAuth flows for Google/Microsoft
4. **Access Control**: Can restrict which tools Gala can call
5. **Audit Logging**: Gateway logs all tool calls for review
6. **Volume Mounts**: Filesystem access limited to specific directories

---

## Deployment Considerations

### Single docker-compose.yml

All MCP servers defined in one file for easy deployment:

```bash
# Start everything
docker compose --profile mcp up -d

# Or selective
docker compose up mcp-gateway mcp-filesystem mcp-docker -d
```

### Environment Variables

```env
# .env additions
MCP_GATEWAY_PORT=8811
HOME_ASSISTANT_URL=http://homeassistant.local:8123
HOME_ASSISTANT_TOKEN=your_long_lived_token
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
```

---

## Questions for Discussion

1. **Which MCP servers are highest priority for you?**
   - Docker management?
   - Home Assistant?
   - Files?
   - Calendar/Email?

2. **Do you have Home Assistant set up?**
   - If yes, this would be a quick win

3. **Google or Microsoft for productivity?**
   - Gmail/Calendar or Outlook?

4. **Any security concerns?**
   - Should Gala be able to delete files?
   - Should she control all smart home devices or just some?

5. **Custom MCP servers?**
   - Any specific tools you want Gala to have that don't exist yet?

---

## Next Steps

After discussion, I'll:

1. Add the MCP Python SDK to requirements.txt
2. Create the MCP client service
3. Update docker-compose.yml with MCP servers
4. Integrate with the command router
5. Test end-to-end with filesystem operations
6. Expand to other MCP servers based on your priorities

---

## Implementation Status

### ✅ Completed (December 14, 2024)

| Component | Status | Notes |
|-----------|--------|-------|
| Docker Service | ✅ Done | `backend/app/services/docker_service.py` |
| Home Assistant Service | ✅ Done | `backend/app/services/homeassistant_service.py` |
| Command Router Tools | ✅ Done | Added docker_* and ha_* tools |
| WebSocket Handler | ✅ Done | `handle_mcp_command()` function |
| Config Settings | ✅ Done | `ha_url`, `ha_token`, `docker_enabled` |
| Documentation | ✅ Done | AGENTS.md, CHEATSHEET.md updated |

### 🔜 Future Phases

| Feature | Status |
|---------|--------|
| Docker MCP Gateway | Planned |
| Filesystem MCP | Not started |
| Browser MCP | Not started |
| Calendar/Email MCP | Not started |

---

*Document created: December 14, 2024*
*Status: PHASE 1 COMPLETE - Docker and Home Assistant working*
