import { useEffect, useRef, useCallback } from 'react'
import { useConversationStore } from '../stores/conversationStore'
import { useSettingsStore } from '../stores/settingsStore'

export function useWebSocket() {
  const wsRef = useRef<WebSocket | null>(null)
  const audioContextRef = useRef<AudioContext | null>(null)
  const audioQueueRef = useRef<string[]>([])
  const isPlayingRef = useRef(false)
  const currentSourceRef = useRef<AudioBufferSourceNode | null>(null)
  const isInterruptedRef = useRef(false)
  const {
    setConnectionStatus,
    setConversationState,
    addMessage,
    setCurrentTranscript,
    appendToCurrentResponse,
    clearCurrentResponse,
    setError,
    setSearchQuery,
    appendThinkingContent,
    clearThinkingContent,
    setStatusDetail,
    setSearchResults,
    setIsAnalyzingImage,
    setVisionResult,
    setVisionLiveEnabled,
    setVisionLiveStatus,
  } = useConversationStore()
  
  const { setSettings, setModels, setVoices } = useSettingsStore()

  // Stop all audio playback - defined early so it can be used in handlers
  const stopAllAudio = () => {
    console.log('🛑 Stopping all audio')
    
    // Set interrupted flag
    isInterruptedRef.current = true
    
    // Clear the audio queue
    audioQueueRef.current = []
    
    // Stop currently playing audio
    if (currentSourceRef.current) {
      try {
        currentSourceRef.current.stop()
        currentSourceRef.current = null
      } catch (e) {
        // May already be stopped
      }
    }
    
    isPlayingRef.current = false
  }

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return

    setConnectionStatus('connecting')
    
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/ws`
    
    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onopen = () => {
      console.log('🔌 WebSocket connected')
      setConnectionStatus('connected')
      setError(null)
      
      // Fetch models and voices
      fetchModels()
      fetchVoices()
    }

    ws.onclose = () => {
      console.log('🔌 WebSocket disconnected')
      setConnectionStatus('disconnected')
      // Attempt reconnect after 3 seconds
      setTimeout(connect, 3000)
    }

    ws.onerror = (error) => {
      console.error('❌ WebSocket error:', error)
      setConnectionStatus('error')
      setError('Connection error. Retrying...')
    }

    ws.onmessage = async (event) => {
      try {
        const data = JSON.parse(event.data)
        handleMessage(data)
      } catch (e) {
        console.error('Failed to parse message:', e)
      }
    }
  }, [])

  const handleMessage = useCallback(async (data: any) => {
    switch (data.type) {
      case 'status':
        setConversationState(data.state as any)
        if (data.settings) {
          setSettings(data.settings)
        }
        // Clear transient states when returning to idle
        if (data.state === 'idle') {
          setSearchQuery(null)
          setStatusDetail(null)
          clearThinkingContent()
        }
        break

      case 'search_start':
        console.log('🔍 Search started:', data.query)
        setSearchQuery(data.query)
        setStatusDetail(`Searching for: ${data.query}`)
        break

      case 'search_results':
        console.log('🔍 Search results:', data.data)
        setStatusDetail(`Found ${data.data?.results?.length || 0} results`)
        // Store full search results for display in UI
        if (data.data) {
          setSearchResults({
            query: data.data.query || '',
            provider: data.data.provider || 'unknown',
            summary: data.data.summary || '',
            sources: (data.data.results || []).map((r: any) => ({
              title: r.title || '',
              url: r.url || '',
              snippet: r.snippet || '',
            })),
            timestamp: new Date(),
          })
        }
        break

      case 'transcription':
        setCurrentTranscript(data.text)
        if (data.final) {
          addMessage({
            id: crypto.randomUUID(),
            role: 'user',
            content: data.text,
            timestamp: new Date(),
          })
        }
        break

      case 'llm_chunk':
        appendToCurrentResponse(data.text)
        break

      case 'thinking_chunk':
        // Accumulate thinking content for optional display
        appendThinkingContent(data.text)
        break

      case 'llm_complete':
        addMessage({
          id: crypto.randomUUID(),
          role: 'assistant',
          content: data.text,
          timestamp: new Date(),
        })
        clearCurrentResponse()
        break

      case 'audio_data':
        // Legacy single audio response
        await playAudio(data.audio)
        break

      case 'audio_chunk':
        // Streaming audio - queue for sequential playback
        queueAudioChunk(data.audio)
        break

      case 'settings_updated':
        setSettings(data.settings)
        break

      case 'interrupted':
        console.log('🛑 Received interrupt confirmation')
        stopAllAudio()
        clearCurrentResponse()
        setConversationState('idle')
        break

      case 'history_cleared':
        useConversationStore.getState().clearMessages()
        break

      case 'error':
        setError(data.message)
        setConversationState('idle')
        break
      
      case 'vision_status':
        console.log('👁️ Vision status:', data)
        setVisionLiveEnabled(data.eyes_open)
        break
      
      case 'vision_update':
        if (data.data?.latest_result) {
          const r = data.data.latest_result
          setVisionLiveStatus({
            present: r.present || false,
            emotion: r.emotion || 'unknown',
            emotionConfidence: r.emotion_confidence || 0,
            age: r.age || 0,
            gender: r.gender || 'unknown',
            attentive: r.attentive || false,
          })
        }
        break
    }
  }, [])

  const playAudioBuffer = async (base64Audio: string): Promise<void> => {
    return new Promise(async (resolve, reject) => {
      try {
        // Check if interrupted before playing
        if (isInterruptedRef.current) {
          resolve()
          return
        }

        if (!audioContextRef.current) {
          audioContextRef.current = new AudioContext()
        }
        
        // Resume context if suspended (browser autoplay policy)
        if (audioContextRef.current.state === 'suspended') {
          await audioContextRef.current.resume()
        }
        
        const audioData = atob(base64Audio)
        const arrayBuffer = new ArrayBuffer(audioData.length)
        const view = new Uint8Array(arrayBuffer)
        for (let i = 0; i < audioData.length; i++) {
          view[i] = audioData.charCodeAt(i)
        }
        
        const audioBuffer = await audioContextRef.current.decodeAudioData(arrayBuffer)
        const source = audioContextRef.current.createBufferSource()
        source.buffer = audioBuffer
        source.connect(audioContextRef.current.destination)
        
        // Track the current source so we can stop it on interrupt
        currentSourceRef.current = source
        
        source.onended = () => {
          currentSourceRef.current = null
          resolve()
        }
        // Note: AudioBufferSourceNode doesn't have onerror, errors are caught in try/catch
        source.start()
      } catch (e) {
        reject(e)
      }
    })
  }

  const processAudioQueue = async () => {
    if (isPlayingRef.current) return
    
    isPlayingRef.current = true
    isInterruptedRef.current = false
    
    while (audioQueueRef.current.length > 0 && !isInterruptedRef.current) {
      const audio = audioQueueRef.current.shift()
      if (audio) {
        try {
          await playAudioBuffer(audio)
        } catch (e) {
          console.error('Audio playback error:', e)
        }
      }
    }
    
    isPlayingRef.current = false
    
    // Only set idle if not interrupted (interrupt handler sets idle)
    if (!isInterruptedRef.current) {
      setConversationState('idle')
    }
  }

  const queueAudioChunk = (base64Audio: string) => {
    audioQueueRef.current.push(base64Audio)
    processAudioQueue()
  }

  const playAudio = async (base64Audio: string) => {
    // For legacy single audio messages, just queue it
    queueAudioChunk(base64Audio)
  }

  const sendAudio = useCallback((audioBlob: Blob) => {
    if (wsRef.current?.readyState !== WebSocket.OPEN) return

    const reader = new FileReader()
    reader.onloadend = () => {
      const base64 = (reader.result as string).split(',')[1]
      wsRef.current?.send(JSON.stringify({
        type: 'audio_data',
        audio: base64,
      }))
    }
    reader.readAsDataURL(audioBlob)
  }, [])

  const sendText = useCallback((text: string) => {
    console.log('📤 sendText called with:', text)
    console.log('📡 WebSocket readyState:', wsRef.current?.readyState, '(OPEN =', WebSocket.OPEN + ')')
    
    if (wsRef.current?.readyState !== WebSocket.OPEN) {
      console.error('❌ WebSocket not open, cannot send')
      setError('Not connected. Please wait for connection.')
      return
    }
    
    try {
      const message = JSON.stringify({
        type: 'text_message',
        content: text,
      })
      console.log('📨 Sending message:', message)
      wsRef.current.send(message)
      setConversationState('processing')
    } catch (e) {
      console.error('❌ Send error:', e)
      setError('Failed to send message')
    }
  }, [setError, setConversationState])

  const interrupt = useCallback(() => {
    console.log('🛑 Interrupt requested')
    
    // Immediately stop local audio playback for responsiveness
    stopAllAudio()
    clearCurrentResponse()
    
    // Send interrupt to backend to cancel TTS generation
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'interrupt',
      }))
    }
    
    setConversationState('idle')
  }, [clearCurrentResponse, setConversationState])

  const updateSettings = useCallback((settings: any) => {
    if (wsRef.current?.readyState !== WebSocket.OPEN) return
    
    wsRef.current.send(JSON.stringify({
      type: 'settings_update',
      settings,
    }))
  }, [])

  const webSearch = useCallback((query: string, followUp?: string, provider: 'auto' | 'searxng' | 'perplexica' = 'auto') => {
    if (wsRef.current?.readyState !== WebSocket.OPEN) return
    
    wsRef.current.send(JSON.stringify({
      type: 'web_search',
      query,
      follow_up: followUp,
      provider,
    }))
    
    setConversationState('processing')
  }, [setConversationState])

  const analyzeImage = useCallback(async (imageBase64: string, prompt: string) => {
    setIsAnalyzingImage(true)
    setStatusDetail(`Analyzing image...`)
    
    try {
      const response = await fetch('/api/vision/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image: imageBase64, prompt })
      })
      
      const result = await response.json()
      
      if (result.success) {
        setVisionResult({ description: result.description, model: result.model_used })
        
        // Add to conversation as an assistant message
        addMessage({
          id: crypto.randomUUID(),
          role: 'user',
          content: `[Shared an image] ${prompt}`,
          timestamp: new Date(),
        })
        
        addMessage({
          id: crypto.randomUUID(),
          role: 'assistant',
          content: result.description,
          timestamp: new Date(),
        })
        
        // Optionally speak the result via WebSocket
        if (wsRef.current?.readyState === WebSocket.OPEN) {
          wsRef.current.send(JSON.stringify({
            type: 'speak_text',
            text: result.description
          }))
        }
      } else {
        setError(result.error || 'Vision analysis failed')
      }
    } catch (e) {
      console.error('Vision analysis error:', e)
      setError('Failed to analyze image')
    } finally {
      setIsAnalyzingImage(false)
      setStatusDetail(null)
    }
  }, [setIsAnalyzingImage, setVisionResult, setStatusDetail, setError, addMessage])

  const clearHistory = useCallback(() => {
    if (wsRef.current?.readyState !== WebSocket.OPEN) return
    
    wsRef.current.send(JSON.stringify({
      type: 'clear_history',
    }))
  }, [])

  const openEyes = useCallback(() => {
    if (wsRef.current?.readyState !== WebSocket.OPEN) return
    
    wsRef.current.send(JSON.stringify({
      type: 'open_eyes',
    }))
  }, [])

  const closeEyes = useCallback(() => {
    if (wsRef.current?.readyState !== WebSocket.OPEN) return
    
    wsRef.current.send(JSON.stringify({
      type: 'close_eyes',
    }))
  }, [])

  const fetchModels = async () => {
    try {
      const response = await fetch('/api/models')
      const data = await response.json()
      setModels(data.models || [])
    } catch (e) {
      console.error('Failed to fetch models:', e)
    }
  }

  const fetchVoices = async () => {
    try {
      const response = await fetch('/api/voices')
      const data = await response.json()
      // New API returns { piper: [...], kokoro: [...], voices: [...] }
      const piperVoices = data.piper || []
      const kokoroVoices = data.kokoro || []
      const allVoices = data.voices || [...piperVoices, ...kokoroVoices]
      setVoices(allVoices, piperVoices, kokoroVoices)
    } catch (e) {
      console.error('Failed to fetch voices:', e)
    }
  }

  useEffect(() => {
    connect()
    
    return () => {
      if (wsRef.current) {
        wsRef.current.close()
      }
      if (audioContextRef.current) {
        audioContextRef.current.close()
      }
    }
  }, [connect])

  return {
    sendAudio,
    sendText,
    interrupt,
    updateSettings,
    clearHistory,
    webSearch,
    analyzeImage,
    openEyes,
    closeEyes,
  }
}

