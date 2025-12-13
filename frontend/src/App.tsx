import { useState, useRef, useCallback } from 'react'
import { VoiceInterface } from './components/VoiceInterface'
import { Settings } from './components/Settings'
import { Transcript } from './components/Transcript'
import { StatusBar } from './components/StatusBar'
import { HistoryPanel } from './components/HistoryPanel'
import { SearchResultsPanel } from './components/SearchResultsPanel'
import { OnboardingPanel } from './components/OnboardingPanel'
import WorkspacePanel from './components/WorkspacePanel'
import { useWebSocket } from './hooks/useWebSocket'
import { useSettingsStore } from './stores/settingsStore'
import { useConversationStore } from './stores/conversationStore'
import { useWorkspaceStore } from './stores/workspaceStore'
import { Settings as SettingsIcon, Clock, User, PanelRightOpen, GripHorizontal } from 'lucide-react'

function App() {
  const [showSettings, setShowSettings] = useState(false)
  const [showHistory, setShowHistory] = useState(false)
  const [showOnboarding, setShowOnboarding] = useState(false)
  const [transcriptHeight, setTranscriptHeight] = useState(200) // Default height in pixels
  const isDraggingRef = useRef(false)
  const startYRef = useRef(0)
  const startHeightRef = useRef(0)

  // Handle resize drag
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    isDraggingRef.current = true
    startYRef.current = e.clientY
    startHeightRef.current = transcriptHeight
    document.body.style.cursor = 'ns-resize'
    document.body.style.userSelect = 'none'
    
    const handleMouseMove = (e: MouseEvent) => {
      if (!isDraggingRef.current) return
      const delta = startYRef.current - e.clientY
      const newHeight = Math.max(100, Math.min(600, startHeightRef.current + delta))
      setTranscriptHeight(newHeight)
    }
    
    const handleMouseUp = () => {
      isDraggingRef.current = false
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
    }
    
    document.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('mouseup', handleMouseUp)
  }, [transcriptHeight])
  const { settings } = useSettingsStore()
  const { searchResults } = useConversationStore()
  const { isOpen: workspaceOpen, setIsOpen: setWorkspaceOpen } = useWorkspaceStore()
  const websocket = useWebSocket()

  // Close other panels when opening one
  const handleShowSettings = () => {
    setShowSettings(!showSettings)
    if (!showSettings) setShowHistory(false)
  }

  const handleShowHistory = () => {
    setShowHistory(!showHistory)
    if (!showHistory) setShowSettings(false)
  }

  return (
    <div className="h-full flex flex-col bg-cyber-darker cyber-grid relative overflow-hidden">
      {/* Ambient glow effects */}
      <div className="absolute top-0 left-1/4 w-96 h-96 bg-cyber-accent/5 rounded-full blur-3xl" />
      <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-cyber-pink/5 rounded-full blur-3xl" />
      
      {/* Header */}
      <header className="relative z-10 flex items-center justify-between px-6 py-4 border-b border-cyber-accent/20">
        <div className="flex items-center gap-4">
          <h1 className="font-display text-2xl tracking-wider text-cyber-accent glow-text-subtle">
            {settings.assistant_name}
          </h1>
          <span className="text-sm text-slate-500 font-body">
            ({settings.assistant_nickname})
          </span>
        </div>
        
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowOnboarding(true)}
            className="p-2 rounded-lg border border-cyber-accent/30 hover:border-cyber-accent hover:bg-cyber-accent/10 transition-all"
            title="Profile & Onboarding"
          >
            <User className="w-5 h-5 text-cyber-accent" />
          </button>
          <button
            onClick={handleShowHistory}
            className={`p-2 rounded-lg border transition-all
                       ${showHistory 
                         ? 'border-cyber-purple bg-cyber-purple/20' 
                         : 'border-cyber-accent/30 hover:border-cyber-accent hover:bg-cyber-accent/10'}`}
            title="Conversation History"
          >
            <Clock className={`w-5 h-5 ${showHistory ? 'text-cyber-purple' : 'text-cyber-accent'}`} />
          </button>
          <button
            onClick={handleShowSettings}
            className={`p-2 rounded-lg border transition-all
                       ${showSettings 
                         ? 'border-cyber-accent bg-cyber-accent/20' 
                         : 'border-cyber-accent/30 hover:border-cyber-accent hover:bg-cyber-accent/10'}`}
            title="Settings"
          >
            <SettingsIcon className="w-5 h-5 text-cyber-accent" />
          </button>
          <button
            onClick={() => setWorkspaceOpen(!workspaceOpen)}
            className={`p-2 rounded-lg border transition-all
                       ${workspaceOpen 
                         ? 'border-cyber-pink bg-cyber-pink/20' 
                         : 'border-cyber-accent/30 hover:border-cyber-accent hover:bg-cyber-accent/10'}`}
            title="Workspace (Notes, Todos, Data)"
          >
            <PanelRightOpen className={`w-5 h-5 ${workspaceOpen ? 'text-cyber-pink' : 'text-cyber-accent'}`} />
          </button>
        </div>
      </header>

      {/* Main content */}
      <main className="flex-1 flex relative z-10 overflow-hidden">
        {/* History Panel - Left */}
        {showHistory && (
          <aside className="absolute left-0 top-0 bottom-0 w-[350px] bg-cyber-dark/95 
                           border-r border-cyber-accent/20 overflow-hidden z-20">
            <HistoryPanel onClose={() => setShowHistory(false)} />
          </aside>
        )}

        {/* Voice Interface - Center */}
        <div className={`flex-1 flex flex-col items-center justify-center p-8 transition-all
                        ${showHistory ? 'ml-[350px]' : ''} ${showSettings ? 'mr-[420px]' : ''}`}>
          <VoiceInterface websocket={websocket} />
        </div>

        {/* Settings Panel - Right */}
        {showSettings && (
          <aside className="absolute right-0 top-0 bottom-0 w-[420px] bg-cyber-dark/95 
                           border-l border-cyber-accent/20 overflow-y-auto z-20">
            <Settings 
              websocket={websocket} 
              onClose={() => setShowSettings(false)} 
            />
          </aside>
        )}
      </main>

      {/* Search Results - Above Transcript */}
      {searchResults && (
        <div className="relative z-10 px-4 py-3 border-t border-cyber-accent/20">
          <SearchResultsPanel 
            results={searchResults} 
            onSaveToKnowledge={() => {
              // TODO: Implement save to RAG knowledge base
              console.log('Save to knowledge base:', searchResults)
              alert('Save to Knowledge Base coming soon!')
            }}
          />
        </div>
      )}

      {/* Transcript - Bottom (Resizable) */}
      {settings.transcript_visible && (
        <div className="relative z-10 flex flex-col">
          {/* Resize Handle */}
          <div 
            onMouseDown={handleMouseDown}
            className="h-2 bg-cyber-dark border-t border-b border-cyber-accent/20 cursor-ns-resize 
                       hover:bg-cyber-accent/10 transition-colors flex items-center justify-center group"
          >
            <GripHorizontal className="w-6 h-4 text-cyber-accent/30 group-hover:text-cyber-accent/60 transition-colors" />
          </div>
          {/* Transcript Content */}
          <div style={{ height: transcriptHeight }} className="overflow-hidden">
            <Transcript onClear={websocket.clearHistory} />
          </div>
        </div>
      )}

      {/* Status Bar */}
      <StatusBar />

      {/* Workspace Panel - Right side drawer */}
      <WorkspacePanel />

      {/* Onboarding Panel (Modal) */}
      <OnboardingPanel 
        isOpen={showOnboarding} 
        onClose={() => setShowOnboarding(false)} 
      />
    </div>
  )
}

export default App

