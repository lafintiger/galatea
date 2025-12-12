"""Conversation History Service - Save and load past conversations"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional
from pydantic import BaseModel


class ConversationMessage(BaseModel):
    """A single message in a conversation"""
    role: str  # user or assistant
    content: str
    timestamp: str


class SavedConversation(BaseModel):
    """A saved conversation with metadata"""
    id: str
    title: str
    created_at: str
    updated_at: str
    message_count: int
    preview: str  # First few words of conversation
    messages: list[ConversationMessage]


class ConversationSummary(BaseModel):
    """Summary of a conversation (without full messages)"""
    id: str
    title: str
    created_at: str
    updated_at: str
    message_count: int
    preview: str


class ConversationHistoryService:
    """Manages saving and loading conversation history"""
    
    def __init__(self, data_dir: str = "data/conversations"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def _generate_id(self) -> str:
        """Generate a unique conversation ID"""
        return datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def _generate_title(self, messages: list[dict]) -> str:
        """Generate a title from the first user message"""
        for msg in messages:
            if msg.get("role") == "user":
                content = msg.get("content", "")
                # Take first 50 chars
                title = content[:50]
                if len(content) > 50:
                    title += "..."
                return title
        return "Untitled Conversation"
    
    def _generate_preview(self, messages: list[dict]) -> str:
        """Generate a preview from the conversation"""
        if not messages:
            return ""
        # Get first exchange
        preview_parts = []
        for msg in messages[:2]:
            role = "You" if msg.get("role") == "user" else "Gala"
            content = msg.get("content", "")[:40]
            if len(msg.get("content", "")) > 40:
                content += "..."
            preview_parts.append(f"{role}: {content}")
        return " | ".join(preview_parts)
    
    def save_conversation(
        self, 
        messages: list[dict],
        conversation_id: Optional[str] = None,
        title: Optional[str] = None
    ) -> SavedConversation:
        """Save a conversation to disk
        
        Args:
            messages: List of message dicts with role, content, timestamp
            conversation_id: Optional ID to update existing conversation
            title: Optional custom title
            
        Returns:
            SavedConversation object
        """
        now = datetime.now().isoformat()
        
        if conversation_id:
            # Updating existing
            conv_id = conversation_id
            # Try to get original created_at
            existing = self.load_conversation(conv_id)
            created_at = existing.created_at if existing else now
        else:
            # New conversation
            conv_id = self._generate_id()
            created_at = now
        
        # Convert messages to proper format
        conv_messages = []
        for msg in messages:
            conv_messages.append(ConversationMessage(
                role=msg.get("role", "user"),
                content=msg.get("content", ""),
                timestamp=msg.get("timestamp", now) if isinstance(msg.get("timestamp"), str) 
                         else msg.get("timestamp", datetime.now()).isoformat() if hasattr(msg.get("timestamp"), 'isoformat')
                         else now
            ))
        
        conversation = SavedConversation(
            id=conv_id,
            title=title or self._generate_title(messages),
            created_at=created_at,
            updated_at=now,
            message_count=len(messages),
            preview=self._generate_preview(messages),
            messages=conv_messages
        )
        
        # Save to file
        file_path = self.data_dir / f"{conv_id}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(conversation.model_dump(), f, indent=2, ensure_ascii=False)
        
        return conversation
    
    def load_conversation(self, conversation_id: str) -> Optional[SavedConversation]:
        """Load a conversation from disk"""
        file_path = self.data_dir / f"{conversation_id}.json"
        
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return SavedConversation(**data)
        except Exception as e:
            print(f"Error loading conversation {conversation_id}: {e}")
            return None
    
    def list_conversations(self, limit: int = 50) -> list[ConversationSummary]:
        """List all saved conversations (most recent first)"""
        conversations = []
        
        for file_path in self.data_dir.glob("*.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                conversations.append(ConversationSummary(
                    id=data.get("id", file_path.stem),
                    title=data.get("title", "Untitled"),
                    created_at=data.get("created_at", ""),
                    updated_at=data.get("updated_at", ""),
                    message_count=data.get("message_count", 0),
                    preview=data.get("preview", "")
                ))
            except Exception as e:
                print(f"Error reading {file_path}: {e}")
        
        # Sort by updated_at descending
        conversations.sort(key=lambda x: x.updated_at, reverse=True)
        
        return conversations[:limit]
    
    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation"""
        file_path = self.data_dir / f"{conversation_id}.json"
        
        if file_path.exists():
            file_path.unlink()
            return True
        return False
    
    def rename_conversation(self, conversation_id: str, new_title: str) -> Optional[SavedConversation]:
        """Rename a conversation"""
        conversation = self.load_conversation(conversation_id)
        if not conversation:
            return None
        
        conversation.title = new_title
        conversation.updated_at = datetime.now().isoformat()
        
        file_path = self.data_dir / f"{conversation_id}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(conversation.model_dump(), f, indent=2, ensure_ascii=False)
        
        return conversation


# Singleton instance
conversation_history = ConversationHistoryService()




