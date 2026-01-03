import { create } from 'zustand'

export interface SpecialistModels {
  medical: string
  legal: string
  coding: string
  math: string
  finance: string
  science: string
  creative: string
  knowledge: string
  personality: string
}

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
  // User location for weather, local info
  user_location: string
  // TTS Provider: "piper" (fast), "kokoro" (high quality), "chatterbox" (SoTA + cloning)
  tts_provider: 'piper' | 'kokoro' | 'chatterbox'
  // Voice tuning for more natural speech (Piper-specific)
  voice_speed: number      // 0.5-2.0 (1.0 = normal)
  voice_variation: number  // 0-1 (higher = more expressive)
  voice_phoneme_var: number // 0-1 (higher = more natural timing)
  // Vision (Gala's Eyes)
  vision_enabled: boolean
  // Domain Routing - Specialist models
  domain_routing_enabled: boolean
  specialist_models: SpecialistModels
  tts_speed: number  // Alias for voice_speed
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
    selected_model: 'ministral-3:latest',
    selected_voice: 'af_heart',  // Kokoro default voice
    response_style: 'conversational',
    activation_mode: 'push-to-talk',
    transcript_visible: true,
    theme: 'futuristic-dark',
    language: 'en',
    user_location: '',  // e.g., "Redlands, California"
    tts_provider: 'kokoro',  // Default to high-quality Kokoro
    // Voice tuning (Piper-specific)
    voice_speed: 1.0,
    voice_variation: 0.8,
    voice_phoneme_var: 0.6,
    // Vision
    vision_enabled: false,
    // Domain routing
    domain_routing_enabled: false,
    specialist_models: {
      medical: 'koesn/llama3-openbiollm-8b:latest',
      legal: 'qwen3:32b',
      coding: 'huihui_ai/qwen3-coder-abliterated:latest',
      math: 'mightykatun/qwen2.5-math:7b',
      finance: 'fingpt:latest',
      science: 'rnj-1:latest',
      creative: 'huihui_ai/qwen3-abliterated:32b',
      knowledge: 'huihui_ai/gpt-oss-abliterated:20b-q8_0',
      personality: 'MartinRizzo/Regent-Dominique:24b-iq3_XXS',
    },
    tts_speed: 1.0,
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

