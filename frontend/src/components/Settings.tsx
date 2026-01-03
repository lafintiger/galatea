import { useState } from 'react'
import { useSettingsStore } from '../stores/settingsStore'
import { X, Volume2, Bot, Sparkles, Play, Loader2, Square, AlertCircle, Mic, Zap, Crown } from 'lucide-react'

interface SettingsProps {
  websocket: {
    updateSettings: (settings: any) => void
    clearHistory: () => void
  }
  onClose: () => void
}

export function Settings({ websocket, onClose }: SettingsProps) {
  const { settings, models, piperVoices, kokoroVoices, updateSetting, updateSettings } = useSettingsStore()
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

  const handleBatchSettingChange = (updates: Partial<typeof settings>) => {
    // Atomic update - update all settings at once to ensure re-render
    updateSettings(updates)
    
    // Send merged settings to backend
    websocket.updateSettings({ ...settings, ...updates })
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
      console.log('Testing voice:', voiceId, 'with provider:', settings.tts_provider)
      const provider = settings.tts_provider || 'piper'
      const response = await fetch(`/api/voices/test/${encodeURIComponent(voiceId)}?provider=${provider}`, {
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

        {/* TTS Engine Selection */}
        <section>
          <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-300 mb-3">
            <Volume2 className="w-4 h-4 text-cyber-purple" />
            Voice Engine
          </h3>

          <div className="flex gap-2 mb-4">
            <button
              onClick={() => {
                const updates: any = { tts_provider: 'piper' }
                // Auto-select a Piper voice if switching
                if (piperVoices.length > 0) {
                  updates.selected_voice = piperVoices[0].id
                }
                handleBatchSettingChange(updates)
              }}
              className={`flex-1 px-3 py-2 rounded text-sm transition-all flex items-center justify-center gap-2
                ${settings.tts_provider === 'piper'
                  ? 'bg-green-500/20 border-green-500 text-green-400'
                  : 'bg-cyber-dark border-cyber-accent/30 text-slate-400'}
                border`}
            >
              <Zap className="w-4 h-4" />
              Fast
            </button>
            <button
              onClick={() => {
                const updates: any = { tts_provider: 'kokoro' }
                // Auto-select a Kokoro voice if switching
                if (kokoroVoices.length > 0) {
                  updates.selected_voice = kokoroVoices[0].id
                }
                handleBatchSettingChange(updates)
              }}
              className={`flex-1 px-3 py-2 rounded text-sm transition-all flex items-center justify-center gap-2
                ${settings.tts_provider === 'kokoro'
                  ? 'bg-cyber-purple/20 border-cyber-purple text-cyber-purple'
                  : 'bg-cyber-dark border-cyber-accent/30 text-slate-400'}
                border`}
            >
              <Crown className="w-4 h-4" />
              HD
            </button>
            <button
              onClick={() => {
                const updates: any = { tts_provider: 'chatterbox' }
                // Chatterbox uses 'default' voice initially
                updates.selected_voice = 'default'
                handleBatchSettingChange(updates)
              }}
              className={`flex-1 px-3 py-2 rounded text-sm transition-all flex items-center justify-center gap-2
                ${settings.tts_provider === 'chatterbox'
                  ? 'bg-amber-500/20 border-amber-500 text-amber-400'
                  : 'bg-cyber-dark border-cyber-accent/30 text-slate-400'}
                border`}
            >
              <Sparkles className="w-4 h-4" />
              Clone
            </button>
          </div>

          <p className="text-xs text-slate-500 mb-4">
            {settings.tts_provider === 'chatterbox'
              ? '🎭 State-of-the-art with voice cloning & [laugh] tags (GPU, ~1-2s latency)'
              : settings.tts_provider === 'kokoro'
              ? '✨ High-quality natural speech (CPU-based, ~1-2s latency)'
              : '⚡ Fast response times (CPU-based, <500ms latency)'}
          </p>
        </section>

        {/* Voice Selection */}
        <section>
          <h3 className="text-sm font-semibold text-slate-300 mb-3">
            Voice Selection
          </h3>

          <div className="flex gap-2">
            <select
              value={settings.selected_voice}
              onChange={(e) => handleSettingChange('selected_voice', e.target.value)}
              className="flex-1 px-3 py-2 rounded bg-cyber-dark border border-cyber-accent/30
                         text-slate-200 text-sm focus:outline-none focus:border-cyber-accent"
            >
              {settings.tts_provider === 'chatterbox' ? (
                // Chatterbox voices (default + cloned)
                <>
                  <option value="default">Default (Female)</option>
                  {/* Cloned voices would appear here from API */}
                </>
              ) : settings.tts_provider === 'kokoro' ? (
                // Kokoro voices grouped by language
                <>
                  {/* English (US) */}
                  <optgroup label="🇺🇸 English (US) - Female">
                    {kokoroVoices
                      .filter(v => v.id.startsWith('af_'))
                      .map((voice) => (
                        <option key={voice.id} value={voice.id}>
                          {voice.name}
                        </option>
                      ))}
                  </optgroup>
                  <optgroup label="🇺🇸 English (US) - Male">
                    {kokoroVoices
                      .filter(v => v.id.startsWith('am_'))
                      .map((voice) => (
                        <option key={voice.id} value={voice.id}>
                          {voice.name}
                        </option>
                      ))}
                  </optgroup>

                  {/* English (UK) */}
                  <optgroup label="🇬🇧 English (UK) - Female">
                    {kokoroVoices
                      .filter(v => v.id.startsWith('bf_'))
                      .map((voice) => (
                        <option key={voice.id} value={voice.id}>
                          {voice.name}
                        </option>
                      ))}
                  </optgroup>
                  <optgroup label="🇬🇧 English (UK) - Male">
                    {kokoroVoices
                      .filter(v => v.id.startsWith('bm_'))
                      .map((voice) => (
                        <option key={voice.id} value={voice.id}>
                          {voice.name}
                        </option>
                      ))}
                  </optgroup>

                  {/* Japanese */}
                  <optgroup label="🇯🇵 Japanese - Female">
                    {kokoroVoices
                      .filter(v => v.id.startsWith('jf_'))
                      .map((voice) => (
                        <option key={voice.id} value={voice.id}>
                          {voice.name}
                        </option>
                      ))}
                  </optgroup>
                  <optgroup label="🇯🇵 Japanese - Male">
                    {kokoroVoices
                      .filter(v => v.id.startsWith('jm_'))
                      .map((voice) => (
                        <option key={voice.id} value={voice.id}>
                          {voice.name}
                        </option>
                      ))}
                  </optgroup>

                  {/* Chinese */}
                  <optgroup label="🇨🇳 Chinese - Female">
                    {kokoroVoices
                      .filter(v => v.id.startsWith('zf_'))
                      .map((voice) => (
                        <option key={voice.id} value={voice.id}>
                          {voice.name}
                        </option>
                      ))}
                  </optgroup>
                  <optgroup label="🇨🇳 Chinese - Male">
                    {kokoroVoices
                      .filter(v => v.id.startsWith('zm_'))
                      .map((voice) => (
                        <option key={voice.id} value={voice.id}>
                          {voice.name}
                        </option>
                      ))}
                  </optgroup>

                  {/* French */}
                  <optgroup label="🇫🇷 French">
                    {kokoroVoices
                      .filter(v => v.id.startsWith('ff_'))
                      .map((voice) => (
                        <option key={voice.id} value={voice.id}>
                          {voice.name}
                        </option>
                      ))}
                  </optgroup>

                  {/* Spanish */}
                  <optgroup label="🇪🇸 Spanish - Female">
                    {kokoroVoices
                      .filter(v => v.id.startsWith('ef_'))
                      .map((voice) => (
                        <option key={voice.id} value={voice.id}>
                          {voice.name}
                        </option>
                      ))}
                  </optgroup>
                  <optgroup label="🇪🇸 Spanish - Male">
                    {kokoroVoices
                      .filter(v => v.id.startsWith('em_'))
                      .map((voice) => (
                        <option key={voice.id} value={voice.id}>
                          {voice.name}
                        </option>
                      ))}
                  </optgroup>

                  {/* Italian */}
                  <optgroup label="🇮🇹 Italian - Female">
                    {kokoroVoices
                      .filter(v => v.id.startsWith('if_'))
                      .map((voice) => (
                        <option key={voice.id} value={voice.id}>
                          {voice.name}
                        </option>
                      ))}
                  </optgroup>
                  <optgroup label="🇮🇹 Italian - Male">
                    {kokoroVoices
                      .filter(v => v.id.startsWith('im_'))
                      .map((voice) => (
                        <option key={voice.id} value={voice.id}>
                          {voice.name}
                        </option>
                      ))}
                  </optgroup>

                  {/* Portuguese */}
                  <optgroup label="🇵🇹 Portuguese - Female">
                    {kokoroVoices
                      .filter(v => v.id.startsWith('pf_'))
                      .map((voice) => (
                        <option key={voice.id} value={voice.id}>
                          {voice.name}
                        </option>
                      ))}
                  </optgroup>
                  <optgroup label="🇵🇹 Portuguese - Male">
                    {kokoroVoices
                      .filter(v => v.id.startsWith('pm_'))
                      .map((voice) => (
                        <option key={voice.id} value={voice.id}>
                          {voice.name}
                        </option>
                      ))}
                  </optgroup>

                  {/* Hindi */}
                  <optgroup label="🇮🇳 Hindi - Female">
                    {kokoroVoices
                      .filter(v => v.id.startsWith('hf_'))
                      .map((voice) => (
                        <option key={voice.id} value={voice.id}>
                          {voice.name}
                        </option>
                      ))}
                  </optgroup>
                  <optgroup label="🇮🇳 Hindi - Male">
                    {kokoroVoices
                      .filter(v => v.id.startsWith('hm_'))
                      .map((voice) => (
                        <option key={voice.id} value={voice.id}>
                          {voice.name}
                        </option>
                      ))}
                  </optgroup>
                </>
              ) : (
                // Piper voices
                <>
                  <optgroup label="⭐ Recommended (High Quality)">
                    {piperVoices
                      .filter(v => v.id.includes('-high') && (v.language.startsWith('en_US') || v.language.startsWith('en_GB')))
                      .map((voice) => (
                        <option key={voice.id} value={voice.id}>
                          {voice.name} ({voice.language})
                        </option>
                      ))}
                  </optgroup>
                  <optgroup label="English (US & GB)">
                    {piperVoices
                      .filter(v => !v.id.includes('-high') && (v.language.startsWith('en_US') || v.language.startsWith('en_GB')))
                      .map((voice) => (
                        <option key={voice.id} value={voice.id}>
                          {voice.name} ({voice.language})
                        </option>
                      ))}
                  </optgroup>
                  <optgroup label="Other Languages">
                    {piperVoices
                      .filter(v => !v.language.startsWith('en_US') && !v.language.startsWith('en_GB'))
                      .map((voice) => (
                        <option key={voice.id} value={voice.id}>
                          {voice.name} ({voice.language})
                        </option>
                      ))}
                  </optgroup>
                </>
              )}
              {settings.tts_provider !== 'chatterbox' && (settings.tts_provider === 'kokoro' ? kokoroVoices : piperVoices).length === 0 && (
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
            <p className="text-xs text-slate-500 mb-2">
              {settings.tts_provider === 'chatterbox' 
                ? 'Chatterbox uses voice cloning. Upload a 10s audio clip to create custom voices.'
                : 'Click to preview any voice:'}
            </p>
            {settings.tts_provider === 'chatterbox' ? (
              <button
                onClick={() => testVoice('default')}
                disabled={isTestingVoice}
                className="w-full flex items-center gap-2 p-2 rounded text-sm hover:bg-cyber-accent/10 
                          text-left transition-colors text-amber-400 border border-amber-500/30"
              >
                {testingVoiceId === 'default' ? (
                  <Loader2 className="w-3 h-3 animate-spin" />
                ) : (
                  <Play className="w-3 h-3" />
                )}
                <span>Test Default Voice</span>
                <Sparkles className="w-3 h-3 ml-auto" />
              </button>
            ) : (settings.tts_provider === 'kokoro' ? kokoroVoices : piperVoices).map((voice) => (
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
            <div className="flex items-center justify-between mb-3">
              <p className="text-xs text-slate-500">Voice Tuning:</p>
              {/* Preset Buttons */}
              <div className="flex gap-1">
                <button
                  onClick={() => {
                    handleSettingChange('voice_speed', 1.0)
                    if (settings.tts_provider === 'piper') {
                      handleSettingChange('voice_variation', 0.8)
                      handleSettingChange('voice_phoneme_var', 0.6)
                    }
                  }}
                  className="px-2 py-0.5 text-xs rounded bg-cyber-accent/10 text-cyber-accent 
                             hover:bg-cyber-accent/20 border border-cyber-accent/30 transition-all"
                  title="Natural, conversational tone"
                >
                  Natural
                </button>
                <button
                  onClick={() => {
                    handleSettingChange('voice_speed', 1.1)
                    if (settings.tts_provider === 'piper') {
                      handleSettingChange('voice_variation', 0.5)
                      handleSettingChange('voice_phoneme_var', 0.4)
                    }
                  }}
                  className="px-2 py-0.5 text-xs rounded bg-cyber-purple/10 text-cyber-purple 
                             hover:bg-cyber-purple/20 border border-cyber-purple/30 transition-all"
                  title="Clear and professional tone"
                >
                  Clear
                </button>
                <button
                  onClick={() => {
                    handleSettingChange('voice_speed', 0.95)
                    if (settings.tts_provider === 'piper') {
                      handleSettingChange('voice_variation', 0.9)
                      handleSettingChange('voice_phoneme_var', 0.7)
                    }
                  }}
                  className="px-2 py-0.5 text-xs rounded bg-pink-500/10 text-pink-400 
                             hover:bg-pink-500/20 border border-pink-500/30 transition-all"
                  title="Warm, expressive tone"
                >
                  Warm
                </button>
              </div>
            </div>

            <div className="space-y-3">
              {/* Speed - Available for both */}
              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-slate-400">Speed</span>
                  <span className="text-cyber-accent">{settings.voice_speed?.toFixed(1) || '1.0'}x</span>
                </div>
                <input
                  type="range"
                  min="0.5"
                  max="1.5"
                  step="0.05"
                  value={settings.voice_speed || 1.0}
                  onChange={(e) => handleSettingChange('voice_speed', parseFloat(e.target.value))}
                  className="w-full h-1 rounded-lg appearance-none cursor-pointer
                             bg-cyber-dark accent-cyber-accent"
                />
                <div className="flex justify-between text-[10px] text-slate-600 mt-0.5">
                  <span>Slower</span>
                  <span>1.0 = Normal</span>
                  <span>Faster</span>
                </div>
              </div>

              {/* Piper-specific controls */}
              {settings.tts_provider === 'piper' && (
                <>
                  {/* Expressiveness */}
                  <div>
                    <div className="flex justify-between text-xs mb-1">
                      <span className="text-slate-400">Expressiveness</span>
                      <span className="text-cyber-purple">{Math.round((settings.voice_variation || 0.8) * 100)}%</span>
                    </div>
                    <input
                      type="range"
                      min="0.3"
                      max="1"
                      step="0.05"
                      value={settings.voice_variation || 0.8}
                      onChange={(e) => handleSettingChange('voice_variation', parseFloat(e.target.value))}
                      className="w-full h-1 rounded-lg appearance-none cursor-pointer
                                 bg-cyber-dark accent-cyber-purple"
                    />
                    <div className="flex justify-between text-[10px] text-slate-600 mt-0.5">
                      <span>Monotone</span>
                      <span>80% = Best</span>
                      <span>Animated</span>
                    </div>
                  </div>

                  {/* Natural Timing */}
                  <div>
                    <div className="flex justify-between text-xs mb-1">
                      <span className="text-slate-400">Natural Timing</span>
                      <span className="text-green-400">{Math.round((settings.voice_phoneme_var || 0.6) * 100)}%</span>
                    </div>
                    <input
                      type="range"
                      min="0.2"
                      max="0.9"
                      step="0.05"
                      value={settings.voice_phoneme_var || 0.6}
                      onChange={(e) => handleSettingChange('voice_phoneme_var', parseFloat(e.target.value))}
                      className="w-full h-1 rounded-lg appearance-none cursor-pointer
                                 bg-cyber-dark accent-green-400"
                    />
                    <div className="flex justify-between text-[10px] text-slate-600 mt-0.5">
                      <span>Robotic</span>
                      <span>60% = Best</span>
                      <span>Natural</span>
                    </div>
                  </div>
                </>
              )}
            </div>

            <p className="text-xs text-slate-600 mt-2 italic">
              {settings.tts_provider === 'piper'
                ? '💡 "Natural" preset: Speed 1.0, Expression 80%, Timing 60%'
                : '💡 Kokoro voices are pre-tuned for natural speech'}
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

