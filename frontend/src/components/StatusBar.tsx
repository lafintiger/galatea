import { useConversationStore } from '../stores/conversationStore'
import { useSettingsStore } from '../stores/settingsStore'
import { Wifi, WifiOff, AlertCircle } from 'lucide-react'

export function StatusBar() {
  const { connectionStatus, error } = useConversationStore()
  const { settings } = useSettingsStore()

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

  return (
    <div className="relative z-10 px-4 py-2 bg-cyber-dark/80 border-t border-cyber-accent/10
                    flex items-center justify-between text-xs text-slate-500">
      {/* Left - Connection Status */}
      <div className="flex items-center gap-2">
        {getConnectionIcon()}
        <span>{getConnectionText()}</span>
      </div>

      {/* Center - Error Message */}
      {error && (
        <div className="flex items-center gap-2 text-red-400">
          <AlertCircle className="w-3 h-3" />
          <span>{error}</span>
        </div>
      )}

      {/* Right - Model Info */}
      <div className="flex items-center gap-4">
        <span>Model: <span className="text-cyber-accent">{settings.selected_model.split('/').pop()}</span></span>
        <span>Voice: <span className="text-cyber-pink">{settings.selected_voice}</span></span>
      </div>
    </div>
  )
}

