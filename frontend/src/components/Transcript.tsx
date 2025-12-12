import { useEffect, useRef, useState } from 'react'
import { useConversationStore } from '../stores/conversationStore'
import { User, Bot, Trash2, Download, ChevronDown } from 'lucide-react'

interface TranscriptProps {
  onClear?: () => void
}

export function Transcript({ onClear }: TranscriptProps) {
  const { messages, currentTranscript, currentResponse, clearMessages, exportConversation } = useConversationStore()
  const scrollRef = useRef<HTMLDivElement>(null)
  const [showExportMenu, setShowExportMenu] = useState(false)

  const handleClear = () => {
    clearMessages()
    onClear?.()
  }

  const handleExport = (format: 'markdown' | 'text' | 'json') => {
    exportConversation(format)
    setShowExportMenu(false)
  }

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
    <div className="relative">
      {/* Action buttons */}
      {messages.length > 0 && (
        <div className="absolute top-2 right-2 flex gap-2 z-10">
          {/* Export dropdown */}
          <div className="relative">
            <button
              onClick={() => setShowExportMenu(!showExportMenu)}
              className="p-2 rounded-lg 
                         bg-cyber-dark/80 border border-slate-700 hover:border-cyber-accent/50
                         text-slate-500 hover:text-cyber-accent transition-colors
                         opacity-50 hover:opacity-100 flex items-center gap-1"
              title="Export conversation"
            >
              <Download className="w-4 h-4" />
              <ChevronDown className="w-3 h-3" />
            </button>
            
            {showExportMenu && (
              <div className="absolute right-0 mt-1 py-1 w-32 rounded-lg 
                              bg-cyber-dark border border-cyber-accent/30 shadow-lg">
                <button
                  onClick={() => handleExport('markdown')}
                  className="w-full px-3 py-1.5 text-left text-sm text-slate-300 
                             hover:bg-cyber-accent/20 hover:text-cyber-accent"
                >
                  Markdown
                </button>
                <button
                  onClick={() => handleExport('text')}
                  className="w-full px-3 py-1.5 text-left text-sm text-slate-300 
                             hover:bg-cyber-accent/20 hover:text-cyber-accent"
                >
                  Plain Text
                </button>
                <button
                  onClick={() => handleExport('json')}
                  className="w-full px-3 py-1.5 text-left text-sm text-slate-300 
                             hover:bg-cyber-accent/20 hover:text-cyber-accent"
                >
                  JSON
                </button>
              </div>
            )}
          </div>
          
          {/* Clear button */}
          <button
            onClick={handleClear}
            className="p-2 rounded-lg 
                       bg-cyber-dark/80 border border-slate-700 hover:border-red-500/50
                       text-slate-500 hover:text-red-400 transition-colors
                       opacity-50 hover:opacity-100"
            title="Clear conversation"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      )}
      
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
    </div>
  )
}



