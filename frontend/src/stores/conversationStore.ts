import { create } from 'zustand'

export type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'error'
export type ConversationState = 'idle' | 'listening' | 'processing' | 'thinking' | 'speaking'

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
}

interface ConversationStoreState {
  connectionStatus: ConnectionStatus
  conversationState: ConversationState
  messages: Message[]
  currentTranscript: string
  currentResponse: string
  error: string | null
  
  setConnectionStatus: (status: ConnectionStatus) => void
  setConversationState: (state: ConversationState) => void
  addMessage: (message: Message) => void
  setCurrentTranscript: (transcript: string) => void
  setCurrentResponse: (response: string) => void
  appendToCurrentResponse: (chunk: string) => void
  clearCurrentResponse: () => void
  setError: (error: string | null) => void
  clearMessages: () => void
}

export const useConversationStore = create<ConversationStoreState>((set) => ({
  connectionStatus: 'disconnected',
  conversationState: 'idle',
  messages: [],
  currentTranscript: '',
  currentResponse: '',
  error: null,
  
  setConnectionStatus: (connectionStatus) => set({ connectionStatus }),
  
  setConversationState: (conversationState) => set({ conversationState }),
  
  addMessage: (message) => set((state) => ({
    messages: [...state.messages, message]
  })),
  
  setCurrentTranscript: (currentTranscript) => set({ currentTranscript }),
  
  setCurrentResponse: (currentResponse) => set({ currentResponse }),
  
  appendToCurrentResponse: (chunk) => set((state) => ({
    currentResponse: state.currentResponse + chunk
  })),
  
  clearCurrentResponse: () => set({ currentResponse: '' }),
  
  setError: (error) => set({ error }),
  
  clearMessages: () => set({ messages: [], currentTranscript: '', currentResponse: '' }),
}))

