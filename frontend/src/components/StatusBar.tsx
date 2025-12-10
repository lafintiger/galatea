import { useConversationStore } from '../stores/conversationStore'
import { useSettingsStore } from '../stores/settingsStore'
import { Wifi, WifiOff, AlertCircle, RefreshCw, Volume2, Cpu } from 'lucide-react'

export function StatusBar() {
  const { connectionStatus, error, setError } = useConversationStore()
  const { settings, models } = useSettingsStore()

  // Find current model info
  const currentModel = models.find(m => m.name === settings.selected_model)
  const modelSize = currentModel?.size 
    ? (currentModel.size / 1e9).toFixed(1) + 'GB'
    : null

  const getConnectionIcon = () => {
    switch (connectionStatus) {
      case 'connected':
        return <Wifi className="w-4 h-4 text-green-400" />
      case 'connecting':
        return <Wifi className="w-4 h-4 text-amber-400 animate-pulse" />
      case 'error':
        return <AlertCircle className="w-4 h-4 text-red-400" />
      default:
        return <WifiOff className="w-4 h-4 text-slate-500" />
    }
  }

  const getConnectionText = () => {
    switch (connectionStatus) {
      case 'connected':
        return 'Connected'
      case 'connecting':
        return 'Connecting...'
      case 'error':
        return 'Connection Error'
      default:
        return 'Disconnected'
    }
  }

  const handleRetry = () => {
    setError(null)
    window.location.reload()
  }

  // Get friendly voice name
  const voiceName = settings.selected_voice.split('/').pop()?.replace(/-/g, ' ') || settings.selected_voice
  
  // Get TTS provider badge
  const ttsProvider = settings.tts_provider === 'kokoro' ? 'HD' : 'Fast'

  return (
    <div className="relative z-10 px-4 py-2 bg-cyber-dark/80 border-t border-cyber-accent/10
                    flex items-center justify-between text-xs text-slate-500">
      {/* Left - Connection Status */}
      <div className="flex items-center gap-2">
        {getConnectionIcon()}
        <span>{getConnectionText()}</span>
        
        {/* Retry button on error */}
        {(connectionStatus === 'error' || connectionStatus === 'disconnected') && (
          <button
            onClick={handleRetry}
            className="ml-2 p-1 rounded hover:bg-cyber-accent/20 text-slate-400 hover:text-cyber-accent transition-colors"
            title="Retry connection"
          >
            <RefreshCw className="w-3 h-3" />
          </button>
        )}
      </div>

      {/* Center - Error Message */}
      {error && (
        <div className="flex items-center gap-2 text-red-400">
          <AlertCircle className="w-3 h-3" />
          <span className="max-w-xs truncate">{error}</span>
          <button
            onClick={() => setError(null)}
            className="text-red-400 hover:text-red-300 ml-1"
          >
            ×
          </button>
        </div>
      )}

      {/* Right - Model & Voice Info */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-1.5" title={settings.selected_model}>
          <Cpu className="w-3 h-3 text-cyber-accent" />
          <span className="text-cyber-accent">{settings.selected_model.split('/').pop()?.split(':')[0]}</span>
          {modelSize && <span className="text-slate-600">({modelSize})</span>}
        </div>
        <div className="flex items-center gap-1.5" title={settings.selected_voice}>
          <Volume2 className="w-3 h-3 text-cyber-pink" />
          <span className="text-cyber-pink">{voiceName.slice(0, 15)}</span>
          <span className={`text-[10px] px-1 rounded ${
            settings.tts_provider === 'kokoro' 
              ? 'bg-cyber-purple/30 text-cyber-purple' 
              : 'bg-green-500/30 text-green-400'
          }`}>{ttsProvider}</span>
        </div>
      </div>
    </div>
  )
}



