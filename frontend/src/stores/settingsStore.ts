import { create } from 'zustand'

export interface UserSettings {
  assistant_name: string
  assistant_nickname: string
  selected_model: string
  selected_voice: string
  response_style: 'concise' | 'conversational'
  activation_mode: 'push-to-talk' | 'vad' | 'wake-word'
  wake_word?: string
  transcript_visible: boolean
  theme: string
  language: string
  // TTS Provider: "piper" (fast, CPU) or "kokoro" (high quality, GPU)
  tts_provider: 'piper' | 'kokoro'
  // Voice tuning for more natural speech (Piper-specific)
  voice_speed: number      // 0.5-2.0 (1.0 = normal)
  voice_variation: number  // 0-1 (higher = more expressive)
  voice_phoneme_var: number // 0-1 (higher = more natural timing)
}

export interface OllamaModel {
  name: string
  size: string
  modified_at: string
}

export interface Voice {
  id: string
  name: string
  language: string
  quality: string
  gender: string
}

// Keep backward compatibility alias
export type PiperVoice = Voice

interface SettingsState {
  settings: UserSettings
  models: OllamaModel[]
  voices: Voice[]
  piperVoices: Voice[]
  kokoroVoices: Voice[]
  isLoading: boolean
  setSettings: (settings: UserSettings) => void
  updateSetting: <K extends keyof UserSettings>(key: K, value: UserSettings[K]) => void
  updateSettings: (updates: Partial<UserSettings>) => void
  setModels: (models: OllamaModel[]) => void
  setVoices: (voices: Voice[], piperVoices?: Voice[], kokoroVoices?: Voice[]) => void
  setLoading: (loading: boolean) => void
}

export const useSettingsStore = create<SettingsState>((set) => ({
  settings: {
    assistant_name: 'Galatea',
    assistant_nickname: 'Gala',
    selected_model: 'huihui_ai/qwen3-abliterated:8b',
    selected_voice: 'af_heart',  // Kokoro default voice
    response_style: 'conversational',
    activation_mode: 'push-to-talk',
    transcript_visible: true,
    theme: 'futuristic-dark',
    language: 'en',
    tts_provider: 'kokoro',  // Default to high-quality Kokoro
    // More natural voice defaults (Piper-specific)
    voice_speed: 1.0,
    voice_variation: 0.8,  // Higher than default for more expression
    voice_phoneme_var: 0.6,  // Higher than default for natural timing
  },
  models: [],
  voices: [],
  piperVoices: [],
  kokoroVoices: [],
  isLoading: true,
  
  setSettings: (settings) => set({ settings }),
  
  updateSetting: (key, value) => set((state) => ({
    settings: { ...state.settings, [key]: value }
  })),
  
  // Atomic batch update for multiple settings at once
  updateSettings: (updates) => set((state) => ({
    settings: { ...state.settings, ...updates }
  })),
  
  setModels: (models) => set({ models }),
  
  setVoices: (voices, piperVoices = [], kokoroVoices = []) => set({ 
    voices, 
    piperVoices, 
    kokoroVoices 
  }),
  
  setLoading: (isLoading) => set({ isLoading }),
}))

