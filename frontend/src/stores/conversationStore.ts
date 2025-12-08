import { create } from 'zustand'

export type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'error'
export type ConversationState = 'idle' | 'listening' | 'processing' | 'thinking' | 'speaking' | 'searching'

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
}

export interface SearchSource {
  title: string
  url: string
  snippet: string
}

export interface SearchResults {
  query: string
  provider: string
  summary: string
  sources: SearchSource[]
  timestamp: Date
}

interface ConversationStoreState {
  connectionStatus: ConnectionStatus
  conversationState: ConversationState
  messages: Message[]
  currentTranscript: string
  currentResponse: string
  error: string | null
  currentConversationId: string | null
  
  // Enhanced status tracking
  searchQuery: string | null        // Current search query
  thinkingContent: string           // Thinking model's internal thoughts
  statusDetail: string | null       // Additional status detail text
  
  // Search results display
  searchResults: SearchResults | null  // Latest search results to display
  
  // Vision analysis
  isAnalyzingImage: boolean
  visionResult: { description: string; model: string } | null
  
  setConnectionStatus: (status: ConnectionStatus) => void
  setConversationState: (state: ConversationState) => void
  addMessage: (message: Message) => void
  setMessages: (messages: Message[]) => void
  setCurrentTranscript: (transcript: string) => void
  setCurrentResponse: (response: string) => void
  appendToCurrentResponse: (chunk: string) => void
  clearCurrentResponse: () => void
  setError: (error: string | null) => void
  clearMessages: () => void
  setCurrentConversationId: (id: string | null) => void
  exportConversation: (format: 'markdown' | 'text' | 'json') => void
  
  // Enhanced status actions
  setSearchQuery: (query: string | null) => void
  appendThinkingContent: (chunk: string) => void
  clearThinkingContent: () => void
  setStatusDetail: (detail: string | null) => void
  
  // Search results actions
  setSearchResults: (results: SearchResults | null) => void
  clearSearchResults: () => void
  
  // Vision actions
  setIsAnalyzingImage: (analyzing: boolean) => void
  setVisionResult: (result: { description: string; model: string } | null) => void
}

export const useConversationStore = create<ConversationStoreState>((set) => ({
  connectionStatus: 'disconnected',
  conversationState: 'idle',
  messages: [],
  currentTranscript: '',
  currentResponse: '',
  error: null,
  currentConversationId: null,
  
  // Enhanced status tracking
  searchQuery: null,
  thinkingContent: '',
  statusDetail: null,
  
  // Search results
  searchResults: null,
  
  // Vision
  isAnalyzingImage: false,
  visionResult: null,
  
  setConnectionStatus: (connectionStatus) => set({ connectionStatus }),
  
  setConversationState: (conversationState) => set({ conversationState }),
  
  addMessage: (message) => set((state) => ({
    messages: [...state.messages, message]
  })),
  
  setMessages: (messages) => set({ messages, currentTranscript: '', currentResponse: '' }),
  
  setCurrentTranscript: (currentTranscript) => set({ currentTranscript }),
  
  setCurrentResponse: (currentResponse) => set({ currentResponse }),
  
  appendToCurrentResponse: (chunk) => set((state) => ({
    currentResponse: state.currentResponse + chunk
  })),
  
  clearCurrentResponse: () => set({ currentResponse: '' }),
  
  setError: (error) => set({ error }),
  
  clearMessages: () => set({ messages: [], currentTranscript: '', currentResponse: '', currentConversationId: null }),
  
  setCurrentConversationId: (currentConversationId) => set({ currentConversationId }),
  
  exportConversation: (format) => {
    const state = useConversationStore.getState()
    const messages = state.messages
    
    if (messages.length === 0) {
      alert('No conversation to export')
      return
    }
    
    let content: string
    let filename: string
    let mimeType: string
    
    const timestamp = new Date().toISOString().slice(0, 10)
    
    if (format === 'json') {
      content = JSON.stringify(messages, null, 2)
      filename = `galatea-chat-${timestamp}.json`
      mimeType = 'application/json'
    } else if (format === 'markdown') {
      content = `# Conversation with Galatea\n\n_Exported: ${new Date().toLocaleString()}_\n\n---\n\n`
      messages.forEach(msg => {
        const role = msg.role === 'user' ? '**You**' : '**Gala**'
        const time = new Date(msg.timestamp).toLocaleTimeString()
        content += `${role} _(${time})_:\n\n${msg.content}\n\n---\n\n`
      })
      filename = `galatea-chat-${timestamp}.md`
      mimeType = 'text/markdown'
    } else {
      content = `Conversation with Galatea\nExported: ${new Date().toLocaleString()}\n${'='.repeat(40)}\n\n`
      messages.forEach(msg => {
        const role = msg.role === 'user' ? 'You' : 'Gala'
        const time = new Date(msg.timestamp).toLocaleTimeString()
        content += `[${time}] ${role}:\n${msg.content}\n\n`
      })
      filename = `galatea-chat-${timestamp}.txt`
      mimeType = 'text/plain'
    }
    
    // Download file
    const blob = new Blob([content], { type: mimeType })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  },
  
  // Enhanced status actions
  setSearchQuery: (searchQuery) => set({ searchQuery }),
  
  appendThinkingContent: (chunk) => set((state) => ({
    thinkingContent: state.thinkingContent + chunk
  })),
  
  clearThinkingContent: () => set({ thinkingContent: '' }),
  
  setStatusDetail: (statusDetail) => set({ statusDetail }),
  
  // Search results actions
  setSearchResults: (searchResults) => set({ searchResults }),
  clearSearchResults: () => set({ searchResults: null }),
  
  // Vision actions
  setIsAnalyzingImage: (isAnalyzingImage) => set({ isAnalyzingImage }),
  setVisionResult: (visionResult) => set({ visionResult }),
}))



