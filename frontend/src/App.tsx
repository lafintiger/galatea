import { useState } from 'react'
import { VoiceInterface } from './components/VoiceInterface'
import { Settings } from './components/Settings'
import { Transcript } from './components/Transcript'
import { StatusBar } from './components/StatusBar'
import { HistoryPanel } from './components/HistoryPanel'
import { SearchResultsPanel } from './components/SearchResultsPanel'
import { useWebSocket } from './hooks/useWebSocket'
import { useSettingsStore } from './stores/settingsStore'
import { useConversationStore } from './stores/conversationStore'
import { Settings as SettingsIcon, Clock } from 'lucide-react'

function App() {
  const [showSettings, setShowSettings] = useState(false)
  const [showHistory, setShowHistory] = useState(false)
  const { settings } = useSettingsStore()
  const { searchResults } = useConversationStore()
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

      {/* Transcript - Bottom */}
      {settings.transcript_visible && (
        <div className="relative z-10 border-t border-cyber-accent/20">
          <Transcript onClear={websocket.clearHistory} />
        </div>
      )}

      {/* Status Bar */}
      <StatusBar />
    </div>
  )
}

export default App

