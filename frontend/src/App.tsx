import { useState } from 'react'
import { VoiceInterface } from './components/VoiceInterface'
import { Settings } from './components/Settings'
import { Transcript } from './components/Transcript'
import { StatusBar } from './components/StatusBar'
import { useWebSocket } from './hooks/useWebSocket'
import { useSettingsStore } from './stores/settingsStore'
import { Settings as SettingsIcon } from 'lucide-react'

function App() {
  const [showSettings, setShowSettings] = useState(false)
  const { settings } = useSettingsStore()
  const websocket = useWebSocket()

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
        
        <button
          onClick={() => setShowSettings(!showSettings)}
          className="p-2 rounded-lg border border-cyber-accent/30 hover:border-cyber-accent 
                     hover:bg-cyber-accent/10 transition-all"
        >
          <SettingsIcon className="w-5 h-5 text-cyber-accent" />
        </button>
      </header>

      {/* Main content */}
      <main className="flex-1 flex relative z-10 overflow-hidden">
        {/* Voice Interface - Center */}
        <div className={`flex-1 flex flex-col items-center justify-center p-8 transition-all
                        ${showSettings ? 'mr-[420px]' : ''}`}>
          <VoiceInterface websocket={websocket} />
        </div>

        {/* Settings Panel - Right */}
        {showSettings && (
          <aside className="absolute right-0 top-0 bottom-0 w-[420px] bg-cyber-dark/95 
                           border-l border-cyber-accent/20 overflow-y-auto">
            <Settings 
              websocket={websocket} 
              onClose={() => setShowSettings(false)} 
            />
          </aside>
        )}
      </main>

      {/* Transcript - Bottom */}
      {settings.transcript_visible && (
        <div className="relative z-10 border-t border-cyber-accent/20">
          <Transcript />
        </div>
      )}

      {/* Status Bar */}
      <StatusBar />
    </div>
  )
}

export default App

