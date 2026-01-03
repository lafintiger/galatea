import { useState, useCallback, useEffect } from 'react'
import { useConversationStore } from '../stores/conversationStore'
import { useSettingsStore } from '../stores/settingsStore'
import { useAudioRecorder } from '../hooks/useAudioRecorder'
import { AudioVisualizer } from './AudioVisualizer'
import { VisionCapture } from './VisionCapture'
import { Mic, MicOff, Square, Send, AlertCircle, Radio, Search, X, Brain, Eye, EyeOff } from 'lucide-react'

interface VoiceInterfaceProps {
  websocket: {
    sendAudio: (blob: Blob) => void
    sendText: (text: string) => void
    interrupt: () => void
    webSearch: (query: string, followUp?: string, provider?: 'auto' | 'searxng' | 'perplexica') => void
    analyzeImage: (imageBase64: string, prompt: string) => void
    openEyes: () => void
    closeEyes: () => void
  }
}

export function VoiceInterface({ websocket }: VoiceInterfaceProps) {
  const { conversationState, currentResponse, searchQuery, statusDetail, thinkingContent, isAnalyzingImage, visionLiveEnabled, visionLiveStatus } = useConversationStore()
  const { settings } = useSettingsStore()
  const [showThinking, setShowThinking] = useState(false)
  const { isRecording, isListening, startRecording, stopRecording, startVAD, stopVAD, audioLevel } = useAudioRecorder()
  const [textInput, setTextInput] = useState('')
  const [micError, setMicError] = useState<string | null>(null)
  const [showSearch, setShowSearch] = useState(false)
  const [searchDialogQuery, setSearchDialogQuery] = useState('')

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

  // Keyboard shortcuts - must be after handlePushToTalk is defined
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ignore if typing in an input
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
        return
      }

      // Escape to interrupt
      if (e.key === 'Escape' && (conversationState === 'speaking' || conversationState === 'processing' || conversationState === 'thinking')) {
        e.preventDefault()
        websocket.interrupt()
      }

      // Spacebar for push-to-talk (start recording)
      if (e.code === 'Space' && settings.activation_mode === 'push-to-talk' && !isRecording && conversationState === 'idle') {
        e.preventDefault()
        handlePushToTalk()
      }
    }

    const handleKeyUp = (e: KeyboardEvent) => {
      // Ignore if typing in an input
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
        return
      }

      // Spacebar release to stop recording
      if (e.code === 'Space' && settings.activation_mode === 'push-to-talk' && isRecording) {
        e.preventDefault()
        handlePushToTalk()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    window.addEventListener('keyup', handleKeyUp)
    return () => {
      window.removeEventListener('keydown', handleKeyDown)
      window.removeEventListener('keyup', handleKeyUp)
    }
  }, [conversationState, websocket, settings.activation_mode, isRecording, handlePushToTalk])

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

  const getStatusInfo = () => {
    // VAD mode statuses
    if (settings.activation_mode === 'vad' && isListening && !isRecording) {
      return { text: 'Open mic active', icon: '🎤', color: 'text-green-400', animate: false }
    }
    if (settings.activation_mode === 'vad' && isRecording) {
      return { text: 'Listening...', icon: '🎙️', color: 'text-yellow-400', animate: true }
    }

    // PTT mode statuses
    if (settings.activation_mode === 'push-to-talk' && isRecording) {
      return { text: 'Recording...', icon: '🎙️', color: 'text-red-400', animate: true }
    }

    // Conversation states
    switch (conversationState) {
      case 'listening':
        return { text: 'Listening...', icon: '👂', color: 'text-green-400', animate: true, detail: null }
      case 'processing':
        return { text: 'Transcribing...', icon: '📝', color: 'text-amber-400', animate: true, detail: null }
      case 'thinking':
        return { text: `${settings.assistant_nickname} is thinking...`, icon: '🧠', color: 'text-purple-400', animate: true, detail: statusDetail }
      case 'speaking':
        return { text: `${settings.assistant_nickname} is speaking`, icon: '🗣️', color: 'text-cyber-accent', animate: true, detail: null }
      case 'searching':
        return { 
          text: 'Searching the web...', 
          icon: '🔍', 
          color: 'text-blue-400', 
          animate: true, 
          detail: searchQuery ? `"${searchQuery}"` : statusDetail 
        }
      default:
        return { 
          text: `Ready to chat with ${settings.assistant_nickname}`, 
          icon: '●', 
          color: 'text-slate-400',
          animate: false,
          detail: null
        }
    }
  }

  const statusInfo = getStatusInfo()

  // Get emotion emoji
  const getEmotionEmoji = (emotion: string) => {
    const emotions: Record<string, string> = {
      happy: '😊',
      sad: '😢',
      angry: '😠',
      fear: '😨',
      surprise: '😲',
      disgust: '🤢',
      neutral: '😐',
    }
    return emotions[emotion.toLowerCase()] || '👤'
  }

  return (
    <div className="flex flex-col items-center gap-8 w-full max-w-2xl">
      {/* Vision Status - Shows when eyes are open */}
      {visionLiveEnabled && visionLiveStatus && (
        <div className="flex items-center gap-3 px-4 py-2 rounded-lg bg-green-500/10 border border-green-500/30">
          <span className="text-2xl">{getEmotionEmoji(visionLiveStatus.emotion)}</span>
          <div className="flex flex-col">
            <span className="text-xs text-green-400/70">
              👁️ {settings.assistant_nickname}'s eyes are open
            </span>
            <span className="text-sm text-green-400">
              {visionLiveStatus.present 
                ? `Seeing: ${visionLiveStatus.emotion}${visionLiveStatus.attentive ? ' (engaged)' : ''}`
                : 'No one in view'
              }
            </span>
          </div>
        </div>
      )}
      
      {/* Status */}
      <div className="flex flex-col items-center gap-2">
        <div className="flex items-center gap-3">
          <span className={`text-2xl ${statusInfo.animate ? 'animate-pulse' : ''}`}>
            {statusInfo.icon}
          </span>
          <span className={`font-body text-xl ${statusInfo.color} ${statusInfo.animate ? 'animate-pulse' : ''}`}>
            {statusInfo.text}
          </span>
        </div>
        
        {/* Status detail (search query, etc.) */}
        {statusInfo.detail && (
          <div className="px-4 py-2 rounded-lg bg-cyber-light/30 border border-cyber-accent/20 max-w-md">
            <p className="text-sm text-slate-400 font-body truncate">{statusInfo.detail}</p>
          </div>
        )}
        
        {/* Thinking toggle - only show when there's thinking content or in thinking state */}
        {(thinkingContent || conversationState === 'thinking') && (
          <button
            onClick={() => setShowThinking(!showThinking)}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs
                       bg-purple-500/10 border border-purple-500/30 text-purple-400
                       hover:bg-purple-500/20 transition-colors"
          >
            <Brain className="w-3 h-3" />
            {showThinking ? <EyeOff className="w-3 h-3" /> : <Eye className="w-3 h-3" />}
            {showThinking ? 'Hide' : 'Show'} Thoughts
          </button>
        )}
      </div>
      
      {/* Thinking Content Panel */}
      {showThinking && thinkingContent && (
        <div className="w-full max-w-2xl p-3 rounded-lg bg-purple-500/10 border border-purple-500/30 
                        max-h-32 overflow-y-auto">
          <div className="flex items-center gap-2 text-purple-400 text-xs mb-2">
            <Brain className="w-3 h-3" />
            <span className="font-medium">{settings.assistant_nickname}'s thoughts</span>
          </div>
          <p className="text-sm text-purple-300/80 font-body whitespace-pre-wrap">{thinkingContent}</p>
        </div>
      )}

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

        {/* Interrupt/Stop Button - Show during speaking, processing, or thinking */}
        {(conversationState === 'speaking' || conversationState === 'processing' || conversationState === 'thinking') && (
          <button
            onClick={handleInterrupt}
            className="w-16 h-16 rounded-full cyber-btn border-red-500/50 
                       hover:border-red-500 flex items-center justify-center
                       animate-pulse"
            title="Stop (Escape)"
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
          type="button"
          onClick={() => setShowSearch(true)}
          disabled={conversationState !== 'idle'}
          className="px-4 py-3 rounded-lg border border-blue-500/50 bg-blue-500/10 
                     hover:bg-blue-500/20 transition-colors disabled:opacity-50"
          title="Web Search"
        >
          <Search className="w-5 h-5 text-blue-400" />
        </button>
        <VisionCapture 
          onAnalyze={websocket.analyzeImage}
          isAnalyzing={isAnalyzingImage}
        />
        {/* Eye Toggle (Vision Live) */}
        <button
          type="button"
          onClick={() => visionLiveEnabled ? websocket.closeEyes() : websocket.openEyes()}
          disabled={conversationState !== 'idle'}
          className={`px-4 py-3 rounded-lg border transition-colors disabled:opacity-50 ${
            visionLiveEnabled 
              ? 'border-green-500/50 bg-green-500/20 hover:bg-green-500/30' 
              : 'border-slate-500/50 bg-slate-500/10 hover:bg-slate-500/20'
          }`}
          title={visionLiveEnabled ? "Close Eyes (Stop Vision)" : "Open Eyes (Start Vision)"}
        >
          {visionLiveEnabled ? (
            <Eye className="w-5 h-5 text-green-400" />
          ) : (
            <EyeOff className="w-5 h-5 text-slate-400" />
          )}
        </button>
        <button
          type="submit"
          disabled={!textInput.trim() || conversationState !== 'idle'}
          className="px-6 py-3 rounded-lg cyber-btn disabled:opacity-50"
        >
          <Send className="w-5 h-5" />
        </button>
      </form>

      {/* Search Dialog */}
      {showSearch && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-cyber-dark border border-cyber-accent/30 rounded-lg p-6 w-full max-w-md mx-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-display text-lg text-cyber-accent flex items-center gap-2">
                <Search className="w-5 h-5" />
                Web Search
              </h3>
              <button
                onClick={() => setShowSearch(false)}
                className="p-1 hover:bg-cyber-accent/20 rounded"
              >
                <X className="w-5 h-5 text-slate-400" />
              </button>
            </div>
            
            <form onSubmit={(e) => {
              e.preventDefault()
              if (searchDialogQuery.trim()) {
                websocket.webSearch(searchDialogQuery.trim())
                setShowSearch(false)
                setSearchDialogQuery('')
              }
            }}>
              <input
                type="text"
                value={searchDialogQuery}
                onChange={(e) => setSearchDialogQuery(e.target.value)}
                placeholder="What do you want to search for?"
                autoFocus
                className="w-full px-4 py-3 rounded-lg bg-cyber-darker border border-cyber-accent/30
                           text-slate-200 placeholder-slate-500 font-body
                           focus:outline-none focus:border-cyber-accent mb-4"
              />
              
              <div className="flex gap-3">
                <button
                  type="button"
                  onClick={() => setShowSearch(false)}
                  className="flex-1 px-4 py-2 rounded-lg border border-slate-600 text-slate-400
                             hover:border-slate-500 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={!searchDialogQuery.trim()}
                  className="flex-1 px-4 py-2 rounded-lg bg-blue-500/20 border border-blue-500/50
                             text-blue-400 hover:bg-blue-500/30 transition-colors
                             disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  <Search className="w-4 h-4" />
                  Search
                </button>
              </div>
            </form>
            
            <p className="text-xs text-slate-500 mt-4 text-center">
              {settings.assistant_nickname} will search the web and summarize results for you
            </p>
          </div>
        </div>
      )}

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
          ? 'Hold Space or click mic to record'
          : 'Start speaking when ready'}
        {(conversationState === 'speaking' || conversationState === 'processing') && (
          <span className="block mt-1 text-slate-600">Press Escape to interrupt</span>
        )}
      </p>
    </div>
  )
}

