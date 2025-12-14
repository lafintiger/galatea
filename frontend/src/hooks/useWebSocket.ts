import { useEffect, useRef, useCallback } from 'react'
import { useConversationStore } from '../stores/conversationStore'
import { useSettingsStore } from '../stores/settingsStore'
import { useWorkspaceStore, waitForHydration, getHasHydrated } from '../stores/workspaceStore'

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

  // Handle workspace commands from backend
  // Now sends confirmation back so backend only speaks on success
  const handleWorkspaceCommand = async (command: any, initialConfirmationText?: string) => {
    let success = false
    let errorMessage = ''
    let confirmationText = initialConfirmationText || ''
    
    try {
      // Wait for store hydration if not already done
      if (!getHasHydrated()) {
        console.log('⏳ Waiting for workspace store hydration...')
        await waitForHydration()
        console.log('✅ Workspace store hydrated, proceeding with command')
      }
      
      // Always get fresh state for each operation
      const store = useWorkspaceStore
      
      console.log('📝 Workspace command received:', command)
      console.log('📝 Action type:', typeof command.action, `"${command.action}"`)
      
      switch (command.action) {
        case 'add_note':
          console.log('✅ MATCHED add_note case')
          console.log('Adding note:', command.content)
          const notesBefore = store.getState().notes
          store.getState().appendToNotes(command.content)
          // Small delay to ensure state update propagates
          const notesAfter = store.getState().notes
          console.log('Notes before:', notesBefore?.length || 0, 'chars')
          console.log('Notes after:', notesAfter?.length || 0, 'chars')
          // Verify the note was actually added
          if (notesAfter && notesAfter.includes(command.content)) {
            success = true
            console.log('✅ Note verified in store')
          } else {
            errorMessage = 'Note was not added to store'
            console.error('❌ Note NOT found in store after append!')
          }
          store.getState().setIsOpen(true)
          store.getState().setActiveTab('notes')
          break
          
        case 'add_todo':
          console.log('✅ MATCHED add_todo case')
          const todosBefore = store.getState().todos.length
          console.log('Todos before:', todosBefore)
          store.getState().addTodo(command.content)
          const todosAfter = store.getState().todos.length
          console.log('Todos after:', todosAfter)
          if (todosAfter > todosBefore) {
            success = true
            console.log('✅ Todo verified in store, count:', todosAfter)
          } else {
            errorMessage = 'Todo was not added to store'
            console.error('❌ Todo count did not increase!')
          }
          store.getState().setIsOpen(true)
          store.getState().setActiveTab('todos')
          break
        
      case 'complete_todo':
        // Find a todo that matches the search text
        console.log('✅ MATCHED complete_todo case')
        const allTodos = store.getState().todos
        const matchingTodo = allTodos.find(t => 
          t.text.toLowerCase().includes(command.search.toLowerCase()) && !t.done
        )
        if (matchingTodo) {
          store.getState().toggleTodo(matchingTodo.id)
          success = true
          console.log('✅ Todo completed:', matchingTodo.text)
        } else {
          errorMessage = `Could not find todo matching "${command.search}"`
          console.error('❌ No matching todo found')
        }
        store.getState().setIsOpen(true)
        store.getState().setActiveTab('todos')
        break
        
      case 'read_todos':
        console.log('✅ MATCHED read_todos case')
        const allTodosForRead = store.getState().todos
        console.log('📋 Raw todos from store:', allTodosForRead)
        // Explicitly check done === true, treating undefined/false as pending
        const pendingTodos = allTodosForRead.filter(t => t.done !== true)
        const completedTodos = allTodosForRead.filter(t => t.done === true)
        console.log(`📋 Pending: ${pendingTodos.length}, Completed: ${completedTodos.length}`)
        store.getState().setIsOpen(true)
        store.getState().setActiveTab('todos')
        success = true
        // Override confirmation text with actual todo info
        if (pendingTodos.length === 0) {
          confirmationText = "Your to-do list is empty. You have no pending tasks."
        } else if (pendingTodos.length === 1) {
          confirmationText = `You have 1 pending task: ${pendingTodos[0].text}`
        } else {
          const todoList = pendingTodos.slice(0, 5).map(t => t.text).join(', ')
          confirmationText = `You have ${pendingTodos.length} pending tasks: ${todoList}`
          if (pendingTodos.length > 5) {
            confirmationText += `, and ${pendingTodos.length - 5} more.`
          }
        }
        if (completedTodos.length > 0) {
          confirmationText += ` Plus ${completedTodos.length} completed.`
        }
        console.log('📋 Todo summary:', confirmationText)
        break
        
      case 'read_notes':
        console.log('✅ MATCHED read_notes case')
        const notes = store.getState().notes
        store.getState().setIsOpen(true)
        store.getState().setActiveTab('notes')
        success = true
        // Override confirmation text with note info
        if (!notes || notes.trim().length === 0) {
          confirmationText = "Your notes are empty."
        } else {
          const wordCount = notes.split(/\s+/).filter(w => w.length > 0).length
          const preview = notes.substring(0, 200).replace(/\n/g, ' ')
          confirmationText = `Your notes have about ${wordCount} words. Here's a preview: ${preview}${notes.length > 200 ? '...' : ''}`
        }
        console.log('📝 Notes summary:', confirmationText)
        break

      case 'clear_todos':
        console.log('✅ MATCHED clear_todos case')
        const todosBeforeClear = store.getState().todos.length
        store.getState().clearAllTodos()
        const todosAfterClear = store.getState().todos.length
        if (todosAfterClear === 0) {
          success = true
          console.log(`✅ Cleared ${todosBeforeClear} todos`)
        } else {
          errorMessage = 'Failed to clear todos'
          console.error('❌ Todos not cleared')
        }
        store.getState().setIsOpen(true)
        store.getState().setActiveTab('todos')
        break

      case 'clear_notes':
        console.log('✅ MATCHED clear_notes case')
        store.getState().clearNotes()
        const notesAfterClear = store.getState().notes
        if (!notesAfterClear || notesAfterClear.length === 0) {
          success = true
          console.log('✅ Notes cleared')
        } else {
          errorMessage = 'Failed to clear notes'
          console.error('❌ Notes not cleared')
        }
        store.getState().setIsOpen(true)
        store.getState().setActiveTab('notes')
        break

      case 'log_data':
        console.log('✅ MATCHED log_data case')
        const entriesBefore = store.getState().dataEntries.length
        store.getState().addDataEntry({
          type: command.type,
          date: new Date().toISOString().split('T')[0],
          value: command.value,
          unit: command.unit,
          notes: command.notes
        })
        const entriesAfter = store.getState().dataEntries.length
        console.log('Entries before:', entriesBefore, 'after:', entriesAfter)
        if (entriesAfter > entriesBefore) {
          success = true
          console.log('✅ Data entry verified in store')
        } else {
          errorMessage = 'Data entry was not added'
          console.error('❌ Data entry count did not increase!')
        }
        store.getState().setIsOpen(true)
        store.getState().setActiveTab('data')
        break
        
      case 'open_workspace':
        store.getState().setIsOpen(true)
        success = true
        break
        
      default:
        console.log('❌ UNMATCHED action:', command.action)
        errorMessage = `Unknown action: ${command.action}`
    }
    } catch (error) {
      console.error('❌ Error in handleWorkspaceCommand:', error)
      errorMessage = error instanceof Error ? error.message : 'Unknown error'
    }
    
    // Send confirmation back to backend
    // Backend will ONLY speak if we confirm success
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      const confirmMsg = {
        type: 'workspace_result',
        success,
        action: command.action,
        content: command.content,
        confirmation_text: confirmationText,
        error: errorMessage || undefined
      }
      console.log('📤 Sending workspace confirmation:', confirmMsg)
      wsRef.current.send(JSON.stringify(confirmMsg))
    } else {
      console.error('❌ Cannot send confirmation - WebSocket not open')
    }
  }

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
        console.log('📝 Transcription received:', data.text, 'final:', data.final)
        setCurrentTranscript(data.text)
        if (data.final) {
          console.log('📝 Adding USER message to transcript')
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
        console.log('🤖 LLM_COMPLETE received!', data)
        console.log('🤖 Text:', data.text?.substring(0, 100))
        if (data.text) {
          console.log('🤖 Adding ASSISTANT message to transcript store')
          addMessage({
            id: crypto.randomUUID(),
            role: 'assistant',
            content: data.text,
            timestamp: new Date(),
          })
          console.log('🤖 Message added, clearing current response')
        } else {
          console.warn('🤖 No text in llm_complete!')
        }
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
      
      case 'workspace_command':
        console.log('Received workspace_command:', data.command)
        await handleWorkspaceCommand(data.command, data.confirmation_text)
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

