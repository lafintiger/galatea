import { useEffect, useRef, useCallback } from 'react'
import { useConversationStore } from '../stores/conversationStore'
import { useSettingsStore } from '../stores/settingsStore'

export function useWebSocket() {
  const wsRef = useRef<WebSocket | null>(null)
  const audioContextRef = useRef<AudioContext | null>(null)
  const audioQueueRef = useRef<string[]>([])
  const isPlayingRef = useRef(false)
  const {
    setConnectionStatus,
    setConversationState,
    addMessage,
    setCurrentTranscript,
    appendToCurrentResponse,
    clearCurrentResponse,
    setError,
  } = useConversationStore()
  
  const { setSettings, setModels, setVoices } = useSettingsStore()

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
        setConversationState(data.state)
        if (data.settings) {
          setSettings(data.settings)
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
        setConversationState('idle')
        break

      case 'history_cleared':
        useConversationStore.getState().clearMessages()
        break

      case 'error':
        setError(data.message)
        setConversationState('idle')
        break
    }
  }, [])

  const playAudioBuffer = async (base64Audio: string): Promise<void> => {
    return new Promise(async (resolve, reject) => {
      try {
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
        source.onended = () => resolve()
        source.onerror = () => reject(new Error('Audio playback error'))
        source.start()
      } catch (e) {
        reject(e)
      }
    })
  }

  const processAudioQueue = async () => {
    if (isPlayingRef.current) return
    
    isPlayingRef.current = true
    
    while (audioQueueRef.current.length > 0) {
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
    setConversationState('idle')
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
    if (wsRef.current?.readyState !== WebSocket.OPEN) return
    
    wsRef.current.send(JSON.stringify({
      type: 'interrupt',
    }))
  }, [])

  const updateSettings = useCallback((settings: any) => {
    if (wsRef.current?.readyState !== WebSocket.OPEN) return
    
    wsRef.current.send(JSON.stringify({
      type: 'settings_update',
      settings,
    }))
  }, [])

  const clearHistory = useCallback(() => {
    if (wsRef.current?.readyState !== WebSocket.OPEN) return
    
    wsRef.current.send(JSON.stringify({
      type: 'clear_history',
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
      setVoices(data.voices || [])
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
  }
}

