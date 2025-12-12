import { useState, useEffect } from 'react'
import { useConversationStore } from '../stores/conversationStore'
import { X, Clock, Trash2, Save, Edit2, Check, MessageSquare } from 'lucide-react'

interface ConversationSummary {
  id: string
  title: string
  created_at: string
  updated_at: string
  message_count: number
  preview: string
}

interface HistoryPanelProps {
  onClose: () => void
}

export function HistoryPanel({ onClose }: HistoryPanelProps) {
  const [conversations, setConversations] = useState<ConversationSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editTitle, setEditTitle] = useState('')
  const [saving, setSaving] = useState(false)
  
  const { messages, clearMessages, setMessages, setCurrentConversationId, currentConversationId } = useConversationStore()

  const fetchConversations = async () => {
    try {
      setLoading(true)
      const response = await fetch('/api/conversations')
      const data = await response.json()
      setConversations(data.conversations || [])
      setError(null)
    } catch (e) {
      setError('Failed to load conversations')
      console.error('Error fetching conversations:', e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchConversations()
  }, [])

  const handleSave = async () => {
    if (messages.length === 0) {
      setError('No conversation to save')
      return
    }

    setSaving(true)
    try {
      const response = await fetch('/api/conversations', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: messages.map(m => ({
            role: m.role,
            content: m.content,
            timestamp: m.timestamp.toISOString()
          })),
          id: currentConversationId || undefined
        })
      })
      
      const data = await response.json()
      if (response.ok) {
        setCurrentConversationId(data.id)
        fetchConversations()
        setError(null)
      } else {
        setError(data.error || 'Failed to save')
      }
    } catch (e) {
      setError('Failed to save conversation')
    } finally {
      setSaving(false)
    }
  }

  const handleLoad = async (id: string) => {
    try {
      const response = await fetch(`/api/conversations/${id}`)
      const data = await response.json()
      
      if (response.ok && data.messages) {
        // Convert to frontend format
        const loadedMessages = data.messages.map((m: any) => ({
          id: crypto.randomUUID(),
          role: m.role,
          content: m.content,
          timestamp: new Date(m.timestamp)
        }))
        setMessages(loadedMessages)
        setCurrentConversationId(id)
        onClose()
      } else {
        setError(data.error || 'Failed to load')
      }
    } catch (e) {
      setError('Failed to load conversation')
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this conversation?')) return
    
    try {
      const response = await fetch(`/api/conversations/${id}`, {
        method: 'DELETE'
      })
      
      if (response.ok) {
        if (currentConversationId === id) {
          setCurrentConversationId(null)
        }
        fetchConversations()
      } else {
        setError('Failed to delete')
      }
    } catch (e) {
      setError('Failed to delete conversation')
    }
  }

  const handleRename = async (id: string) => {
    if (!editTitle.trim()) return
    
    try {
      const response = await fetch(`/api/conversations/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: editTitle.trim() })
      })
      
      if (response.ok) {
        setEditingId(null)
        fetchConversations()
      } else {
        setError('Failed to rename')
      }
    } catch (e) {
      setError('Failed to rename conversation')
    }
  }

  const handleNewConversation = () => {
    clearMessages()
    setCurrentConversationId(null)
    onClose()
  }

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    const now = new Date()
    const diff = now.getTime() - date.getTime()
    const days = Math.floor(diff / (1000 * 60 * 60 * 24))
    
    if (days === 0) {
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    } else if (days === 1) {
      return 'Yesterday'
    } else if (days < 7) {
      return date.toLocaleDateString([], { weekday: 'short' })
    } else {
      return date.toLocaleDateString([], { month: 'short', day: 'numeric' })
    }
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-cyber-accent/20">
        <h2 className="font-display text-lg text-cyber-accent flex items-center gap-2">
          <Clock className="w-5 h-5" />
          Conversation History
        </h2>
        <button
          onClick={onClose}
          className="p-1 hover:bg-cyber-accent/20 rounded transition-colors"
        >
          <X className="w-5 h-5 text-slate-400" />
        </button>
      </div>

      {/* Actions */}
      <div className="p-4 border-b border-cyber-accent/10 flex gap-2">
        <button
          onClick={handleSave}
          disabled={messages.length === 0 || saving}
          className="flex-1 px-3 py-2 rounded bg-cyber-accent/20 border border-cyber-accent/50
                     text-cyber-accent text-sm hover:bg-cyber-accent/30 transition-colors
                     disabled:opacity-50 disabled:cursor-not-allowed
                     flex items-center justify-center gap-2"
        >
          <Save className="w-4 h-4" />
          {saving ? 'Saving...' : currentConversationId ? 'Update' : 'Save Current'}
        </button>
        <button
          onClick={handleNewConversation}
          className="px-3 py-2 rounded bg-cyber-purple/20 border border-cyber-purple/50
                     text-cyber-purple text-sm hover:bg-cyber-purple/30 transition-colors
                     flex items-center justify-center gap-2"
        >
          <MessageSquare className="w-4 h-4" />
          New
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="mx-4 mt-2 p-2 rounded bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
          {error}
          <button onClick={() => setError(null)} className="ml-2 text-red-300">×</button>
        </div>
      )}

      {/* Conversation List */}
      <div className="flex-1 overflow-y-auto p-4 space-y-2">
        {loading ? (
          <div className="text-center text-slate-500 py-8">Loading...</div>
        ) : conversations.length === 0 ? (
          <div className="text-center text-slate-500 py-8">
            <Clock className="w-8 h-8 mx-auto mb-2 opacity-50" />
            <p>No saved conversations</p>
            <p className="text-xs mt-1">Save your current chat to see it here</p>
          </div>
        ) : (
          conversations.map((conv) => (
            <div
              key={conv.id}
              className={`p-3 rounded-lg border transition-all cursor-pointer
                         ${currentConversationId === conv.id 
                           ? 'bg-cyber-accent/20 border-cyber-accent/50' 
                           : 'bg-cyber-dark/50 border-cyber-accent/20 hover:border-cyber-accent/40'}`}
            >
              {editingId === conv.id ? (
                <div className="flex items-center gap-2">
                  <input
                    type="text"
                    value={editTitle}
                    onChange={(e) => setEditTitle(e.target.value)}
                    className="flex-1 px-2 py-1 rounded bg-cyber-dark border border-cyber-accent/30
                               text-slate-200 text-sm focus:outline-none focus:border-cyber-accent"
                    autoFocus
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') handleRename(conv.id)
                      if (e.key === 'Escape') setEditingId(null)
                    }}
                  />
                  <button
                    onClick={() => handleRename(conv.id)}
                    className="p-1 text-green-400 hover:bg-green-500/20 rounded"
                  >
                    <Check className="w-4 h-4" />
                  </button>
                </div>
              ) : (
                <>
                  <div className="flex items-start justify-between gap-2">
                    <h3 
                      className="text-sm text-slate-200 font-medium truncate flex-1"
                      onClick={() => handleLoad(conv.id)}
                    >
                      {conv.title}
                    </h3>
                    <div className="flex items-center gap-1 flex-shrink-0">
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          setEditingId(conv.id)
                          setEditTitle(conv.title)
                        }}
                        className="p-1 text-slate-500 hover:text-cyber-accent hover:bg-cyber-accent/20 rounded"
                        title="Rename"
                      >
                        <Edit2 className="w-3 h-3" />
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          handleDelete(conv.id)
                        }}
                        className="p-1 text-slate-500 hover:text-red-400 hover:bg-red-500/20 rounded"
                        title="Delete"
                      >
                        <Trash2 className="w-3 h-3" />
                      </button>
                    </div>
                  </div>
                  <p 
                    className="text-xs text-slate-500 mt-1 truncate"
                    onClick={() => handleLoad(conv.id)}
                  >
                    {conv.preview}
                  </p>
                  <div 
                    className="flex items-center justify-between mt-2 text-xs text-slate-600"
                    onClick={() => handleLoad(conv.id)}
                  >
                    <span>{conv.message_count} messages</span>
                    <span>{formatDate(conv.updated_at)}</span>
                  </div>
                </>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  )
}




