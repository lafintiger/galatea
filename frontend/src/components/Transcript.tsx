import { useEffect, useRef } from 'react'
import { useConversationStore } from '../stores/conversationStore'
import { useSettingsStore } from '../stores/settingsStore'
import { User, Bot } from 'lucide-react'

export function Transcript() {
  const { messages, currentTranscript, currentResponse } = useConversationStore()
  const { settings } = useSettingsStore()
  const scrollRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages, currentTranscript, currentResponse])

  if (messages.length === 0 && !currentTranscript && !currentResponse) {
    return (
      <div className="h-32 flex items-center justify-center text-slate-500">
        <p className="text-sm">Conversation transcript will appear here...</p>
      </div>
    )
  }

  return (
    <div 
      ref={scrollRef}
      className="h-48 overflow-y-auto p-4 space-y-3"
    >
      {messages.map((message) => (
        <div
          key={message.id}
          className={`flex gap-3 ${message.role === 'user' ? 'flex-row-reverse' : ''}`}
        >
          {/* Avatar */}
          <div className={`
            flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center
            ${message.role === 'user' 
              ? 'bg-cyber-purple/20 border border-cyber-purple/50' 
              : 'bg-cyber-accent/20 border border-cyber-accent/50'}
          `}>
            {message.role === 'user' 
              ? <User className="w-4 h-4 text-cyber-purple" />
              : <Bot className="w-4 h-4 text-cyber-accent" />}
          </div>

          {/* Message */}
          <div className={`
            max-w-[70%] px-4 py-2 rounded-lg
            ${message.role === 'user'
              ? 'bg-cyber-purple/10 border border-cyber-purple/30'
              : 'bg-cyber-light border border-cyber-accent/20'}
          `}>
            <p className="text-sm text-slate-200 font-body whitespace-pre-wrap">
              {message.content}
            </p>
            <span className="text-xs text-slate-500 mt-1 block">
              {new Date(message.timestamp).toLocaleTimeString()}
            </span>
          </div>
        </div>
      ))}

      {/* Current transcription (user speaking) */}
      {currentTranscript && (
        <div className="flex gap-3 flex-row-reverse opacity-70">
          <div className="w-8 h-8 rounded-full bg-cyber-purple/20 border border-cyber-purple/50 
                          flex items-center justify-center">
            <User className="w-4 h-4 text-cyber-purple" />
          </div>
          <div className="max-w-[70%] px-4 py-2 rounded-lg bg-cyber-purple/10 border border-cyber-purple/30">
            <p className="text-sm text-slate-200 font-body italic">{currentTranscript}...</p>
          </div>
        </div>
      )}

      {/* Current response (assistant speaking) */}
      {currentResponse && (
        <div className="flex gap-3 opacity-70">
          <div className="w-8 h-8 rounded-full bg-cyber-accent/20 border border-cyber-accent/50 
                          flex items-center justify-center animate-pulse">
            <Bot className="w-4 h-4 text-cyber-accent" />
          </div>
          <div className="max-w-[70%] px-4 py-2 rounded-lg bg-cyber-light border border-cyber-accent/20">
            <p className="text-sm text-slate-200 font-body">{currentResponse}</p>
            <span className="inline-block w-2 h-4 bg-cyber-accent/50 animate-pulse ml-1" />
          </div>
        </div>
      )}
    </div>
  )
}

