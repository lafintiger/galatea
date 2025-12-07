import { useState } from 'react'
import { useSettingsStore } from '../stores/settingsStore'
import { X, Volume2, Bot, Sparkles, Play, Loader2, Square, AlertCircle, Mic } from 'lucide-react'

interface SettingsProps {
  websocket: {
    updateSettings: (settings: any) => void
    clearHistory: () => void
  }
  onClose: () => void
}

export function Settings({ websocket, onClose }: SettingsProps) {
  const { settings, models, voices, updateSetting } = useSettingsStore()
  const [isTestingVoice, setIsTestingVoice] = useState(false)
  const [testingVoiceId, setTestingVoiceId] = useState<string | null>(null)
  const [voiceTestError, setVoiceTestError] = useState<string | null>(null)
  const [currentAudio, setCurrentAudio] = useState<HTMLAudioElement | null>(null)
  const [abortController, setAbortController] = useState<AbortController | null>(null)

  const handleSettingChange = <K extends keyof typeof settings>(
    key: K,
    value: typeof settings[K]
  ) => {
    updateSetting(key, value)
    websocket.updateSettings({ ...settings, [key]: value })
  }

  const stopVoiceTest = () => {
    if (currentAudio) {
      currentAudio.pause()
      currentAudio.src = ''
      setCurrentAudio(null)
    }
    if (abortController) {
      abortController.abort()
      setAbortController(null)
    }
    setIsTestingVoice(false)
    setTestingVoiceId(null)
  }

  const testVoice = async (voiceId: string) => {
    // Stop any existing test
    stopVoiceTest()
    
    setIsTestingVoice(true)
    setTestingVoiceId(voiceId)
    setVoiceTestError(null)
    
    const controller = new AbortController()
    setAbortController(controller)
    
    // Set a timeout of 30 seconds
    const timeoutId = setTimeout(() => {
      controller.abort()
      setVoiceTestError('Voice test timed out. Piper may be loading the voice model.')
      setIsTestingVoice(false)
      setTestingVoiceId(null)
    }, 30000)
    
    try {
      console.log('Testing voice:', voiceId)
      const response = await fetch(`/api/voices/test/${encodeURIComponent(voiceId)}`, {
        signal: controller.signal
      })
      
      clearTimeout(timeoutId)
      
      if (!response.ok) {
        let errorMsg = 'Voice test failed'
        try {
          const error = await response.json()
          errorMsg = error.error || errorMsg
        } catch {
          errorMsg = `HTTP ${response.status}: ${response.statusText}`
        }
        throw new Error(errorMsg)
      }
      
      const audioBlob = await response.blob()
      console.log('Received audio blob:', audioBlob.size, 'bytes')
      
      if (audioBlob.size < 100) {
        throw new Error('Received empty or invalid audio')
      }
      
      const audioUrl = URL.createObjectURL(audioBlob)
      const audio = new Audio(audioUrl)
      setCurrentAudio(audio)
      
      audio.onended = () => {
        URL.revokeObjectURL(audioUrl)
        setIsTestingVoice(false)
        setTestingVoiceId(null)
        setCurrentAudio(null)
      }
      
      audio.onerror = (e) => {
        console.error('Audio playback error:', e)
        URL.revokeObjectURL(audioUrl)
        setVoiceTestError('Failed to play audio')
        setIsTestingVoice(false)
        setTestingVoiceId(null)
        setCurrentAudio(null)
      }
      
      await audio.play()
    } catch (error) {
      clearTimeout(timeoutId)
      if (error instanceof Error && error.name === 'AbortError') {
        console.log('Voice test aborted')
      } else {
        console.error('Voice test error:', error)
        setVoiceTestError(error instanceof Error ? error.message : 'Unknown error')
      }
      setIsTestingVoice(false)
      setTestingVoiceId(null)
    }
  }

  return (
    <div className="p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h2 className="font-display text-xl text-cyber-accent">Settings</h2>
        <button
          onClick={onClose}
          className="p-1 rounded hover:bg-cyber-light/50 transition-colors"
        >
          <X className="w-5 h-5 text-slate-400" />
        </button>
      </div>

      <div className="space-y-6">
        {/* Assistant Identity */}
        <section>
          <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-300 mb-3">
            <Sparkles className="w-4 h-4 text-cyber-pink" />
            Identity
          </h3>
          
          <div className="space-y-3">
            <div>
              <label className="block text-xs text-slate-500 mb-1">Name</label>
              <input
                type="text"
                value={settings.assistant_name}
                onChange={(e) => handleSettingChange('assistant_name', e.target.value)}
                className="w-full px-3 py-2 rounded bg-cyber-dark border border-cyber-accent/30
                           text-slate-200 text-sm focus:outline-none focus:border-cyber-accent"
              />
            </div>
            
            <div>
              <label className="block text-xs text-slate-500 mb-1">Nickname</label>
              <input
                type="text"
                value={settings.assistant_nickname}
                onChange={(e) => handleSettingChange('assistant_nickname', e.target.value)}
                className="w-full px-3 py-2 rounded bg-cyber-dark border border-cyber-accent/30
                           text-slate-200 text-sm focus:outline-none focus:border-cyber-accent"
              />
            </div>
          </div>
        </section>

        {/* Model Selection */}
        <section>
          <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-300 mb-3">
            <Bot className="w-4 h-4 text-cyber-accent" />
            AI Model
          </h3>
          
          <select
            value={settings.selected_model}
            onChange={(e) => handleSettingChange('selected_model', e.target.value)}
            className="w-full px-3 py-2 rounded bg-cyber-dark border border-cyber-accent/30
                       text-slate-200 text-sm focus:outline-none focus:border-cyber-accent"
          >
            {models.map((model) => (
              <option key={model.name} value={model.name}>
                {model.name} ({model.size})
              </option>
            ))}
            {models.length === 0 && (
              <option value={settings.selected_model}>
                {settings.selected_model}
              </option>
            )}
          </select>
        </section>

        {/* Voice Selection */}
        <section>
          <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-300 mb-3">
            <Volume2 className="w-4 h-4 text-cyber-purple" />
            Voice
          </h3>
          
          <div className="flex gap-2">
            <select
              value={settings.selected_voice}
              onChange={(e) => handleSettingChange('selected_voice', e.target.value)}
              className="flex-1 px-3 py-2 rounded bg-cyber-dark border border-cyber-accent/30
                         text-slate-200 text-sm focus:outline-none focus:border-cyber-accent"
            >
              {/* Recommended high-quality English voices first */}
              <optgroup label="⭐ Recommended (High Quality)">
                {voices
                  .filter(v => v.id.includes('-high') && (v.language.startsWith('en_US') || v.language.startsWith('en_GB')))
                  .map((voice) => (
                    <option key={voice.id} value={voice.id}>
                      {voice.name} ({voice.language})
                    </option>
                  ))}
              </optgroup>
              <optgroup label="English (US & GB)">
                {voices
                  .filter(v => !v.id.includes('-high') && (v.language.startsWith('en_US') || v.language.startsWith('en_GB')))
                  .map((voice) => (
                    <option key={voice.id} value={voice.id}>
                      {voice.name} ({voice.language})
                    </option>
                  ))}
              </optgroup>
              <optgroup label="Other Languages">
                {voices
                  .filter(v => !v.language.startsWith('en_US') && !v.language.startsWith('en_GB'))
                  .map((voice) => (
                    <option key={voice.id} value={voice.id}>
                      {voice.name} ({voice.language})
                    </option>
                  ))}
              </optgroup>
              {voices.length === 0 && (
                <option value={settings.selected_voice}>
                  {settings.selected_voice}
                </option>
              )}
            </select>
            
            <button
              onClick={() => isTestingVoice ? stopVoiceTest() : testVoice(settings.selected_voice)}
              className={`px-3 py-2 rounded border transition-all flex items-center gap-1
                         ${isTestingVoice 
                           ? 'bg-red-500/20 border-red-500/50 text-red-400 hover:bg-red-500/30' 
                           : 'bg-cyber-purple/20 border-cyber-purple/50 text-cyber-purple hover:bg-cyber-purple/30 hover:border-cyber-purple'}`}
              title={isTestingVoice ? "Stop voice test" : "Test selected voice"}
            >
              {isTestingVoice && testingVoiceId === settings.selected_voice ? (
                <Square className="w-4 h-4" />
              ) : isTestingVoice ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Play className="w-4 h-4" />
              )}
            </button>
          </div>
          
          {/* Error Display */}
          {voiceTestError && (
            <div className="mt-2 p-2 rounded bg-red-500/10 border border-red-500/30 
                           flex items-start gap-2 text-xs text-red-400">
              <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
              <span>{voiceTestError}</span>
              <button 
                onClick={() => setVoiceTestError(null)}
                className="ml-auto text-red-400 hover:text-red-300"
              >
                ×
              </button>
            </div>
          )}
          
          {/* Voice Preview List */}
          <div className="mt-3 space-y-1 max-h-32 overflow-y-auto">
            <p className="text-xs text-slate-500 mb-2">Click to preview any voice:</p>
            {voices.map((voice) => (
              <button
                key={voice.id}
                onClick={() => {
                  handleSettingChange('selected_voice', voice.id)
                  testVoice(voice.id)
                }}
                disabled={isTestingVoice}
                className={`w-full px-2 py-1.5 rounded text-left text-xs transition-all
                           flex items-center justify-between gap-2
                           ${settings.selected_voice === voice.id 
                             ? 'bg-cyber-purple/20 border border-cyber-purple/50 text-cyber-purple' 
                             : 'bg-cyber-dark/50 border border-transparent text-slate-400 hover:border-cyber-accent/30'}
                           disabled:opacity-50`}
              >
                <span>{voice.name}</span>
                <span className="text-slate-500">{voice.language}</span>
                {isTestingVoice && testingVoiceId === voice.id && (
                  <Loader2 className="w-3 h-3 animate-spin text-cyber-purple" />
                )}
              </button>
            ))}
          </div>
          
          {/* Voice Tuning */}
          <div className="mt-4 pt-4 border-t border-cyber-accent/20">
            <p className="text-xs text-slate-500 mb-3">Voice Tuning (for more natural speech):</p>
            
            <div className="space-y-3">
              {/* Speed */}
              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-slate-400">Speed</span>
                  <span className="text-cyber-accent">{settings.voice_speed?.toFixed(1) || '1.0'}x</span>
                </div>
                <input
                  type="range"
                  min="0.5"
                  max="2.0"
                  step="0.1"
                  value={settings.voice_speed || 1.0}
                  onChange={(e) => handleSettingChange('voice_speed', parseFloat(e.target.value))}
                  className="w-full h-1 rounded-lg appearance-none cursor-pointer
                             bg-cyber-dark accent-cyber-accent"
                />
              </div>
              
              {/* Expressiveness */}
              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-slate-400">Expressiveness</span>
                  <span className="text-cyber-purple">{Math.round((settings.voice_variation || 0.8) * 100)}%</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.05"
                  value={settings.voice_variation || 0.8}
                  onChange={(e) => handleSettingChange('voice_variation', parseFloat(e.target.value))}
                  className="w-full h-1 rounded-lg appearance-none cursor-pointer
                             bg-cyber-dark accent-cyber-purple"
                />
              </div>
              
              {/* Natural Timing */}
              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-slate-400">Natural Timing</span>
                  <span className="text-green-400">{Math.round((settings.voice_phoneme_var || 0.6) * 100)}%</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.05"
                  value={settings.voice_phoneme_var || 0.6}
                  onChange={(e) => handleSettingChange('voice_phoneme_var', parseFloat(e.target.value))}
                  className="w-full h-1 rounded-lg appearance-none cursor-pointer
                             bg-cyber-dark accent-green-400"
                />
              </div>
            </div>
            
            <p className="text-xs text-slate-600 mt-2 italic">
              Higher expressiveness + timing = more conversational
            </p>
          </div>
        </section>

        {/* Response Style */}
        <section>
          <h3 className="text-sm font-semibold text-slate-300 mb-3">Response Style</h3>
          
          <div className="flex gap-2">
            <button
              onClick={() => handleSettingChange('response_style', 'concise')}
              className={`flex-1 px-3 py-2 rounded text-sm transition-all
                ${settings.response_style === 'concise'
                  ? 'bg-cyber-accent/20 border-cyber-accent text-cyber-accent'
                  : 'bg-cyber-dark border-cyber-accent/30 text-slate-400'}
                border`}
            >
              Concise
            </button>
            <button
              onClick={() => handleSettingChange('response_style', 'conversational')}
              className={`flex-1 px-3 py-2 rounded text-sm transition-all
                ${settings.response_style === 'conversational'
                  ? 'bg-cyber-accent/20 border-cyber-accent text-cyber-accent'
                  : 'bg-cyber-dark border-cyber-accent/30 text-slate-400'}
                border`}
            >
              Conversational
            </button>
          </div>
        </section>

        {/* Microphone Mode */}
        <section>
          <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-300 mb-3">
            <Mic className="w-4 h-4 text-green-400" />
            Microphone Mode
          </h3>
          
          <div className="flex gap-2">
            <button
              onClick={() => handleSettingChange('activation_mode', 'push-to-talk')}
              className={`flex-1 px-3 py-2 rounded text-sm transition-all
                ${settings.activation_mode === 'push-to-talk'
                  ? 'bg-green-500/20 border-green-500 text-green-400'
                  : 'bg-cyber-dark border-cyber-accent/30 text-slate-400'}
                border`}
            >
              Push to Talk
            </button>
            <button
              onClick={() => handleSettingChange('activation_mode', 'vad')}
              className={`flex-1 px-3 py-2 rounded text-sm transition-all
                ${settings.activation_mode === 'vad'
                  ? 'bg-green-500/20 border-green-500 text-green-400'
                  : 'bg-cyber-dark border-cyber-accent/30 text-slate-400'}
                border`}
            >
              Open Mic
            </button>
          </div>
          
          <p className="text-xs text-slate-500 mt-2">
            {settings.activation_mode === 'vad' 
              ? 'Always listening - speak anytime and Gala will respond when you pause'
              : 'Click the mic button to start/stop recording'}
          </p>
        </section>

        {/* Transcript Toggle */}
        <section>
          <div className="flex items-center justify-between">
            <span className="text-sm text-slate-300">Show Transcript</span>
            <button
              onClick={() => handleSettingChange('transcript_visible', !settings.transcript_visible)}
              className={`w-12 h-6 rounded-full transition-all relative
                ${settings.transcript_visible ? 'bg-cyber-accent' : 'bg-slate-600'}`}
            >
              <span className={`absolute top-1 w-4 h-4 rounded-full bg-white transition-all
                ${settings.transcript_visible ? 'left-7' : 'left-1'}`} />
            </button>
          </div>
        </section>

        {/* Actions */}
        <section className="pt-4 border-t border-cyber-accent/20">
          <button
            onClick={() => websocket.clearHistory()}
            className="w-full px-4 py-2 rounded bg-red-500/10 border border-red-500/30
                       text-red-400 text-sm hover:bg-red-500/20 transition-colors"
          >
            Clear Conversation
          </button>
        </section>
      </div>
    </div>
  )
}

