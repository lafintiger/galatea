import { useState, useCallback, useEffect } from 'react'
import { useConversationStore } from '../stores/conversationStore'
import { useSettingsStore } from '../stores/settingsStore'
import { useAudioRecorder } from '../hooks/useAudioRecorder'
import { AudioVisualizer } from './AudioVisualizer'
import { Mic, MicOff, Square, Send, AlertCircle, Radio } from 'lucide-react'

interface VoiceInterfaceProps {
  websocket: {
    sendAudio: (blob: Blob) => void
    sendText: (text: string) => void
    interrupt: () => void
  }
}

export function VoiceInterface({ websocket }: VoiceInterfaceProps) {
  const { conversationState, currentResponse } = useConversationStore()
  const { settings } = useSettingsStore()
  const { isRecording, isListening, startRecording, stopRecording, startVAD, stopVAD, audioLevel } = useAudioRecorder()
  const [textInput, setTextInput] = useState('')
  const [micError, setMicError] = useState<string | null>(null)

  // Handle VAD mode changes
  useEffect(() => {
    if (settings.activation_mode === 'vad') {
      // Start VAD when in open mic mode and not already listening
      if (!isListening && conversationState === 'idle') {
        startVAD((audioBlob) => {
          console.log('🎤 VAD: Speech ended, sending audio')
          websocket.sendAudio(audioBlob)
        }).catch((error) => {
          console.error('VAD start error:', error)
          if (error instanceof DOMException && error.name === 'NotAllowedError') {
            setMicError('🎤 Microphone access denied. Please allow microphone permission.')
          }
        })
      }
    } else {
      // Stop VAD when switching to push-to-talk
      if (isListening) {
        stopVAD()
      }
    }
  }, [settings.activation_mode, conversationState, isListening, startVAD, stopVAD, websocket])

  // Stop VAD when Gala is speaking
  useEffect(() => {
    if (settings.activation_mode === 'vad' && conversationState === 'speaking') {
      stopVAD()
    } else if (settings.activation_mode === 'vad' && conversationState === 'idle' && !isListening) {
      // Restart VAD after Gala finishes speaking
      const timer = setTimeout(() => {
        startVAD((audioBlob) => {
          console.log('🎤 VAD: Speech ended, sending audio')
          websocket.sendAudio(audioBlob)
        }).catch(console.error)
      }, 500)
      return () => clearTimeout(timer)
    }
  }, [conversationState, settings.activation_mode, isListening, startVAD, stopVAD, websocket])

  const handlePushToTalk = useCallback(async () => {
    setMicError(null)
    
    if (isRecording) {
      const audioBlob = await stopRecording()
      if (audioBlob) {
        websocket.sendAudio(audioBlob)
      }
    } else {
      try {
        await startRecording()
      } catch (error) {
        console.error('Microphone error:', error)
        if (error instanceof DOMException) {
          if (error.name === 'NotAllowedError') {
            setMicError('🎤 Microphone access denied. Please allow microphone permission in your browser.')
          } else if (error.name === 'NotFoundError') {
            setMicError('🎤 No microphone found. Please connect a microphone.')
          } else {
            setMicError(`🎤 Microphone error: ${error.message}`)
          }
        } else {
          setMicError('🎤 Failed to access microphone. Please check your browser settings.')
        }
      }
    }
  }, [isRecording, startRecording, stopRecording, websocket])

  const toggleVAD = useCallback(async () => {
    setMicError(null)
    
    if (isListening) {
      stopVAD()
    } else {
      try {
        await startVAD((audioBlob) => {
          console.log('🎤 VAD: Speech ended, sending audio')
          websocket.sendAudio(audioBlob)
        })
      } catch (error) {
        console.error('VAD error:', error)
        if (error instanceof DOMException && error.name === 'NotAllowedError') {
          setMicError('🎤 Microphone access denied. Please allow microphone permission.')
        } else {
          setMicError('🎤 Failed to access microphone.')
        }
      }
    }
  }, [isListening, startVAD, stopVAD, websocket])

  const handleInterrupt = useCallback(() => {
    websocket.interrupt()
  }, [websocket])

  const handleTextSubmit = useCallback((e: React.FormEvent) => {
    e.preventDefault()
    console.log('handleTextSubmit called, textInput:', textInput)
    if (textInput.trim()) {
      console.log('Calling websocket.sendText with:', textInput.trim())
      websocket.sendText(textInput.trim())
      setTextInput('')
    }
  }, [textInput, websocket])

  const getStatusText = () => {
    if (settings.activation_mode === 'vad' && isListening && !isRecording) {
      return '🎤 Open mic - speak anytime...'
    }
    if (settings.activation_mode === 'vad' && isRecording) {
      return '🎤 Listening to you...'
    }
    switch (conversationState) {
      case 'listening':
        return 'Listening...'
      case 'processing':
        return 'Processing...'
      case 'thinking':
        return `${settings.assistant_nickname} is thinking...`
      case 'speaking':
        return `${settings.assistant_nickname} is speaking...`
      default:
        if (settings.activation_mode === 'vad') {
          return isListening ? '🎤 Open mic active' : `Ready to chat with ${settings.assistant_nickname}`
        }
        return `Ready to chat with ${settings.assistant_nickname}`
    }
  }

  const getStatusColor = () => {
    switch (conversationState) {
      case 'listening':
        return 'text-green-400'
      case 'processing':
      case 'thinking':
        return 'text-amber-400'
      case 'speaking':
        return 'text-cyber-accent'
      default:
        return 'text-slate-400'
    }
  }

  return (
    <div className="flex flex-col items-center gap-8 w-full max-w-2xl">
      {/* Status */}
      <div className="flex items-center gap-3">
        <div className={`status-dot ${conversationState}`} />
        <span className={`font-body text-lg ${getStatusColor()}`}>
          {getStatusText()}
        </span>
      </div>

      {/* Audio Visualizer */}
      <div className="w-full h-32 flex items-center justify-center">
        <AudioVisualizer 
          isActive={isRecording || isListening || conversationState === 'speaking'} 
          level={audioLevel}
          mode={isRecording ? 'recording' : isListening ? 'listening' : conversationState === 'speaking' ? 'playing' : 'idle'}
        />
      </div>

      {/* Current Response Preview */}
      {currentResponse && (
        <div className="w-full p-4 rounded-lg bg-cyber-light/50 border border-cyber-accent/20 
                        max-h-48 overflow-y-auto">
          <p className="text-slate-300 font-body">{currentResponse}</p>
        </div>
      )}

      {/* Voice Control */}
      <div className="flex items-center gap-4">
        {/* Push-to-Talk Button */}
        {settings.activation_mode === 'push-to-talk' && (
          <button
            onClick={handlePushToTalk}
            disabled={conversationState === 'processing' || conversationState === 'thinking'}
            className={`
              relative w-24 h-24 rounded-full cyber-btn
              flex items-center justify-center
              ${isRecording ? 'border-green-500 bg-green-500/10' : ''}
              ${isRecording ? 'animate-pulse-glow' : ''}
            `}
          >
            {isRecording ? (
              <MicOff className="w-10 h-10 text-green-400" />
            ) : (
              <Mic className="w-10 h-10" />
            )}
            
            {/* Pulse rings when recording */}
            {isRecording && (
              <>
                <span className="absolute inset-0 rounded-full border border-green-500/50 pulse-ring" />
                <span className="absolute inset-0 rounded-full border border-green-500/30 pulse-ring" 
                      style={{ animationDelay: '0.5s' }} />
              </>
            )}
          </button>
        )}

        {/* Open Mic / VAD Button */}
        {settings.activation_mode === 'vad' && (
          <button
            onClick={toggleVAD}
            disabled={conversationState === 'processing' || conversationState === 'thinking' || conversationState === 'speaking'}
            className={`
              relative w-24 h-24 rounded-full cyber-btn
              flex items-center justify-center
              ${isListening ? 'border-green-500 bg-green-500/10' : ''}
              ${isRecording ? 'border-yellow-500 bg-yellow-500/20' : ''}
            `}
          >
            {isRecording ? (
              <Radio className="w-10 h-10 text-yellow-400 animate-pulse" />
            ) : isListening ? (
              <Radio className="w-10 h-10 text-green-400" />
            ) : (
              <Mic className="w-10 h-10" />
            )}
            
            {/* Pulse rings when listening */}
            {isListening && !isRecording && (
              <>
                <span className="absolute inset-0 rounded-full border border-green-500/30 pulse-ring" />
              </>
            )}
            
            {/* Active recording indicator */}
            {isRecording && (
              <>
                <span className="absolute inset-0 rounded-full border border-yellow-500/50 pulse-ring" />
                <span className="absolute inset-0 rounded-full border border-yellow-500/30 pulse-ring" 
                      style={{ animationDelay: '0.5s' }} />
              </>
            )}
          </button>
        )}

        {/* Interrupt Button */}
        {conversationState === 'speaking' && (
          <button
            onClick={handleInterrupt}
            className="w-16 h-16 rounded-full cyber-btn border-red-500/50 
                       hover:border-red-500 flex items-center justify-center"
          >
            <Square className="w-6 h-6 text-red-400" />
          </button>
        )}
      </div>

      {/* Text Input Alternative */}
      <form onSubmit={handleTextSubmit} className="w-full flex gap-3">
        <input
          type="text"
          value={textInput}
          onChange={(e) => setTextInput(e.target.value)}
          placeholder={`Type a message to ${settings.assistant_nickname}...`}
          disabled={conversationState !== 'idle'}
          className="flex-1 px-4 py-3 rounded-lg bg-cyber-dark border border-cyber-accent/30
                     text-slate-200 placeholder-slate-500 font-body
                     focus:outline-none focus:border-cyber-accent
                     disabled:opacity-50 disabled:cursor-not-allowed"
        />
        <button
          type="submit"
          disabled={!textInput.trim() || conversationState !== 'idle'}
          className="px-6 py-3 rounded-lg cyber-btn disabled:opacity-50"
        >
          <Send className="w-5 h-5" />
        </button>
      </form>

      {/* Microphone Error */}
      {micError && (
        <div className="w-full max-w-md p-3 rounded-lg bg-red-500/10 border border-red-500/30 
                       flex items-start gap-2 text-sm text-red-400">
          <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <p>{micError}</p>
            <p className="text-xs text-red-400/70 mt-1">
              Click the 🔒 icon in your browser's address bar to manage permissions.
            </p>
          </div>
          <button 
            onClick={() => setMicError(null)}
            className="text-red-400 hover:text-red-300 text-lg"
          >
            ×
          </button>
        </div>
      )}

      {/* Instructions */}
      <p className="text-sm text-slate-500 text-center">
        {settings.activation_mode === 'push-to-talk' 
          ? 'Click the microphone to start/stop recording'
          : 'Start speaking when ready'}
      </p>
    </div>
  )
}

