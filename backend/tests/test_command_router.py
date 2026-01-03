"""Tests for the Command Router service."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.command_router import CommandRouter, command_router


class TestCommandRouter:
    """Tests for CommandRouter class."""
    
    def test_init(self):
        """Test router initialization."""
        router = CommandRouter()
        assert router.model == "ministral-3:latest"
        assert len(router.tools) > 0
    
    def test_tools_have_required_fields(self):
        """Test that all tools have required OpenAI function fields."""
        router = CommandRouter()
        for tool in router.tools:
            assert tool["type"] == "function"
            assert "function" in tool
            assert "name" in tool["function"]
            assert "description" in tool["function"]
            assert "parameters" in tool["function"]
    
    def test_tool_names_are_unique(self):
        """Test that all tool names are unique."""
        router = CommandRouter()
        names = [t["function"]["name"] for t in router.tools]
        assert len(names) == len(set(names)), "Duplicate tool names found"
    
    @pytest.mark.asyncio
    async def test_route_add_todo(self):
        """Test routing an add_todo command."""
        router = CommandRouter()
        
        # Mock the Ollama response
        mock_response = {
            "message": {
                "content": "",
                "tool_calls": [{
                    "function": {
                        "name": "add_todo",
                        "arguments": '{"content": "buy groceries"}'
                    }
                }]
            }
        }
        
        with patch.object(router, '_call_ollama', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_response
            
            command, response = await router.route("add todo: buy groceries")
            
            assert command is not None
            assert command["action"] == "add_todo"
            assert command["content"] == "buy groceries"
    
    @pytest.mark.asyncio
    async def test_route_search_web(self):
        """Test routing a web search command."""
        router = CommandRouter()
        
        mock_response = {
            "message": {
                "content": "",
                "tool_calls": [{
                    "function": {
                        "name": "search_web",
                        "arguments": '{"query": "weather in LA"}'
                    }
                }]
            }
        }
        
        with patch.object(router, '_call_ollama', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_response
            
            command, response = await router.route("what's the weather in LA?")
            
            assert command is not None
            assert command["action"] == "search_web"
            assert command["query"] == "weather in LA"
    
    @pytest.mark.asyncio
    async def test_route_vision_commands(self):
        """Test routing vision-related commands."""
        router = CommandRouter()
        
        # Test open_eyes
        mock_response = {
            "message": {
                "content": "",
                "tool_calls": [{
                    "function": {
                        "name": "open_eyes",
                        "arguments": "{}"
                    }
                }]
            }
        }
        
        with patch.object(router, '_call_ollama', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_response
            
            command, response = await router.route("open your eyes")
            
            assert command is not None
            assert command["action"] == "open_eyes"
    
    @pytest.mark.asyncio
    async def test_route_no_tool_returns_none(self):
        """Test that non-command text returns None."""
        router = CommandRouter()
        
        # LLM doesn't call any tool - just responds conversationally
        mock_response = {
            "message": {
                "content": "Hello! How can I help you today?",
                "tool_calls": None
            }
        }
        
        with patch.object(router, '_call_ollama', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_response
            
            command, response = await router.route("hello there")
            
            # No tool call means we should process as normal conversation
            assert command is None
    
    def test_tool_to_command_add_todo(self):
        """Test _tool_to_command for add_todo."""
        router = CommandRouter()
        result = router._tool_to_command("add_todo", {"content": "test task"})
        
        assert result[0]["action"] == "add_todo"
        assert result[0]["content"] == "test task"
        assert "Added to your to-do list" in result[1]
    
    def test_tool_to_command_search_web(self):
        """Test _tool_to_command for search_web."""
        router = CommandRouter()
        result = router._tool_to_command("search_web", {"query": "test query"})
        
        assert result[0]["action"] == "search_web"
        assert result[0]["query"] == "test query"
    
    def test_tool_to_command_docker_restart(self):
        """Test _tool_to_command for docker_restart."""
        router = CommandRouter()
        result = router._tool_to_command("docker_restart", {"container": "whisper"})
        
        assert result[0]["action"] == "docker_restart"
        assert result[0]["container"] == "whisper"


class TestIntentPatterns:
    """Test regex-based intent detection (fallback patterns)."""
    
    def test_detect_search_intent(self):
        """Test search intent detection."""
        from app.core.intent import detect_search_intent
        
        # Should detect search
        patterns_that_should_search = [
            "search for python tutorials",
            "look up the weather",
            "find out about quantum computing",
            "google best restaurants",
            "what is the capital of france",
        ]
        
        for text in patterns_that_should_search:
            is_search, query = detect_search_intent(text)
            assert is_search, f"Should detect search in: {text}"
            assert query, f"Should extract query from: {text}"
    
    def test_detect_workspace_command(self):
        """Test workspace command detection."""
        from app.core.intent import detect_workspace_command
        
        # Add todo
        cmd, resp = detect_workspace_command("add todo: buy milk")
        assert cmd is not None
        assert cmd["action"] == "add_todo"
        
        # Add note
        cmd, resp = detect_workspace_command("note: meeting at 3pm")
        assert cmd is not None
        assert cmd["action"] == "add_note"
        
        # Clear todos
        cmd, resp = detect_workspace_command("clear my todos")
        assert cmd is not None
        assert cmd["action"] == "clear_todos"
