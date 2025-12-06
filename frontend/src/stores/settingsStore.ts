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
  // Voice tuning for more natural speech
  voice_speed: number      // 0.5-2.0 (1.0 = normal)
  voice_variation: number  // 0-1 (higher = more expressive)
  voice_phoneme_var: number // 0-1 (higher = more natural timing)
}

export interface OllamaModel {
  name: string
  size: string
  modified_at: string
}

export interface PiperVoice {
  id: string
  name: string
  language: string
  quality: string
  gender: string
}

interface SettingsState {
  settings: UserSettings
  models: OllamaModel[]
  voices: PiperVoice[]
  isLoading: boolean
  setSettings: (settings: UserSettings) => void
  updateSetting: <K extends keyof UserSettings>(key: K, value: UserSettings[K]) => void
  setModels: (models: OllamaModel[]) => void
  setVoices: (voices: PiperVoice[]) => void
  setLoading: (loading: boolean) => void
}

export const useSettingsStore = create<SettingsState>((set) => ({
  settings: {
    assistant_name: 'Galatea',
    assistant_nickname: 'Gala',
    selected_model: 'huihui_ai/qwen3-abliterated:8b',
    selected_voice: 'en_US-lessac-high',  // High quality for better sound
    response_style: 'conversational',
    activation_mode: 'push-to-talk',
    transcript_visible: true,
    theme: 'futuristic-dark',
    language: 'en',
    // More natural voice defaults
    voice_speed: 1.0,
    voice_variation: 0.8,  // Higher than default for more expression
    voice_phoneme_var: 0.6,  // Higher than default for natural timing
  },
  models: [],
  voices: [],
  isLoading: true,
  
  setSettings: (settings) => set({ settings }),
  
  updateSetting: (key, value) => set((state) => ({
    settings: { ...state.settings, [key]: value }
  })),
  
  setModels: (models) => set({ models }),
  
  setVoices: (voices) => set({ voices }),
  
  setLoading: (isLoading) => set({ isLoading }),
}))

