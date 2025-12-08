import { useState, useRef, useCallback, useEffect } from 'react'

interface UseAudioRecorderReturn {
  isRecording: boolean
  isListening: boolean  // For VAD mode - mic is on but not recording speech yet
  startRecording: () => Promise<void>
  stopRecording: () => Promise<Blob | null>
  startVAD: (onSpeechEnd: (blob: Blob) => void) => Promise<void>
  stopVAD: () => void
  audioLevel: number
}

// VAD configuration
const VAD_SPEECH_THRESHOLD = 0.08  // Audio level to detect speech start
const VAD_SILENCE_THRESHOLD = 0.03  // Audio level to detect silence
const VAD_SILENCE_DURATION = 1500   // ms of silence before ending speech
const VAD_MIN_SPEECH_DURATION = 500 // ms minimum speech to be valid

export function useAudioRecorder(): UseAudioRecorderReturn {
  const [isRecording, setIsRecording] = useState(false)
  const [isListening, setIsListening] = useState(false)
  const [audioLevel, setAudioLevel] = useState(0)
  
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const audioChunksRef = useRef<Blob[]>([])
  const analyserRef = useRef<AnalyserNode | null>(null)
  const animationFrameRef = useRef<number | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const audioContextRef = useRef<AudioContext | null>(null)
  
  // VAD state
  const vadActiveRef = useRef(false)
  const speechStartTimeRef = useRef<number | null>(null)
  const silenceStartTimeRef = useRef<number | null>(null)
  const onSpeechEndRef = useRef<((blob: Blob) => void) | null>(null)

  const updateAudioLevel = useCallback(() => {
    if (!analyserRef.current) return
    
    const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount)
    analyserRef.current.getByteFrequencyData(dataArray)
    
    // Calculate average level
    const average = dataArray.reduce((a, b) => a + b, 0) / dataArray.length
    const level = average / 255
    setAudioLevel(level)
    
    // VAD logic
    if (vadActiveRef.current) {
      const now = Date.now()
      
      if (!isRecording && level > VAD_SPEECH_THRESHOLD) {
        // Speech started - begin recording
        console.log('🎤 VAD: Speech detected, starting recording')
        speechStartTimeRef.current = now
        silenceStartTimeRef.current = null
        
        // Start the MediaRecorder
        if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'inactive') {
          audioChunksRef.current = []
          mediaRecorderRef.current.start(100)
          setIsRecording(true)
        }
      } else if (isRecording) {
        if (level < VAD_SILENCE_THRESHOLD) {
          // Silence detected
          if (!silenceStartTimeRef.current) {
            silenceStartTimeRef.current = now
          } else if (now - silenceStartTimeRef.current > VAD_SILENCE_DURATION) {
            // Silence long enough - end recording
            const speechDuration = speechStartTimeRef.current 
              ? now - speechStartTimeRef.current - VAD_SILENCE_DURATION 
              : 0
            
            if (speechDuration >= VAD_MIN_SPEECH_DURATION) {
              console.log('🎤 VAD: Silence detected, ending recording')
              // Stop recording and send
              if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
                mediaRecorderRef.current.stop()
              }
            } else {
              // Too short, discard
              console.log('🎤 VAD: Speech too short, discarding')
              if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
                mediaRecorderRef.current.stop()
                audioChunksRef.current = []
              }
              setIsRecording(false)
            }
            silenceStartTimeRef.current = null
            speechStartTimeRef.current = null
          }
        } else {
          // Still speaking
          silenceStartTimeRef.current = null
        }
      }
    }
    
    if (isRecording || isListening) {
      animationFrameRef.current = requestAnimationFrame(updateAudioLevel)
    }
  }, [isRecording, isListening])

  const setupAudioStream = useCallback(async () => {
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        channelCount: 1,
        sampleRate: 16000,
        echoCancellation: true,
        noiseSuppression: true,
      }
    })
    
    streamRef.current = stream
    
    // Setup audio analysis for visualization
    const audioContext = new AudioContext({ sampleRate: 16000 })
    audioContextRef.current = audioContext
    const source = audioContext.createMediaStreamSource(stream)
    const analyser = audioContext.createAnalyser()
    analyser.fftSize = 256
    source.connect(analyser)
    analyserRef.current = analyser
    
    // Setup MediaRecorder
    const mediaRecorder = new MediaRecorder(stream, {
      mimeType: 'audio/webm;codecs=opus'
    })
    
    mediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        audioChunksRef.current.push(event.data)
      }
    }
    
    mediaRecorderRef.current = mediaRecorder
    return { stream, mediaRecorder }
  }, [])

  const startRecording = useCallback(async () => {
    try {
      await setupAudioStream()
      
      audioChunksRef.current = []
      mediaRecorderRef.current?.start(100) // Collect data every 100ms
      
      setIsRecording(true)
      updateAudioLevel()
      
    } catch (error) {
      console.error('Failed to start recording:', error)
      throw error
    }
  }, [setupAudioStream, updateAudioLevel])

  const startVAD = useCallback(async (onSpeechEnd: (blob: Blob) => void) => {
    try {
      await setupAudioStream()
      
      // Set up VAD callback
      onSpeechEndRef.current = onSpeechEnd
      vadActiveRef.current = true
      audioChunksRef.current = []
      
      // Set up onstop handler for VAD
      if (mediaRecorderRef.current) {
        mediaRecorderRef.current.onstop = async () => {
          if (audioChunksRef.current.length > 0) {
            const webmBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' })
            try {
              const pcmBlob = await convertToPCM(webmBlob)
              if (onSpeechEndRef.current && vadActiveRef.current) {
                onSpeechEndRef.current(pcmBlob)
              }
            } catch (e) {
              console.error('Audio conversion error:', e)
              if (onSpeechEndRef.current && vadActiveRef.current) {
                onSpeechEndRef.current(webmBlob)
              }
            }
          }
          audioChunksRef.current = []
          setIsRecording(false)
        }
      }
      
      setIsListening(true)
      updateAudioLevel()
      console.log('🎤 VAD mode started - listening for speech...')
      
    } catch (error) {
      console.error('Failed to start VAD:', error)
      throw error
    }
  }, [setupAudioStream, updateAudioLevel])

  const stopVAD = useCallback(() => {
    console.log('🎤 VAD mode stopped')
    vadActiveRef.current = false
    onSpeechEndRef.current = null
    
    // Stop any ongoing recording
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      mediaRecorderRef.current.stop()
    }
    
    // Cleanup stream
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop())
      streamRef.current = null
    }
    
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current)
    }
    
    setIsRecording(false)
    setIsListening(false)
    setAudioLevel(0)
  }, [])

  const stopRecording = useCallback(async (): Promise<Blob | null> => {
    return new Promise((resolve) => {
      if (!mediaRecorderRef.current || mediaRecorderRef.current.state === 'inactive') {
        resolve(null)
        return
      }
      
      mediaRecorderRef.current.onstop = async () => {
        // Convert webm to PCM for Whisper
        const webmBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' })
        
        try {
          const pcmBlob = await convertToPCM(webmBlob)
          resolve(pcmBlob)
        } catch (e) {
          console.error('Audio conversion error:', e)
          resolve(webmBlob)
        }
        
        // Cleanup
        if (streamRef.current) {
          streamRef.current.getTracks().forEach(track => track.stop())
        }
        if (animationFrameRef.current) {
          cancelAnimationFrame(animationFrameRef.current)
        }
        
        setIsRecording(false)
        setAudioLevel(0)
      }
      
      mediaRecorderRef.current.stop()
    })
  }, [])

  return {
    isRecording,
    isListening,
    startRecording,
    stopRecording,
    startVAD,
    stopVAD,
    audioLevel,
  }
}

// Convert webm audio to PCM for Whisper
async function convertToPCM(webmBlob: Blob): Promise<Blob> {
  const audioContext = new AudioContext({ sampleRate: 16000 })
  const arrayBuffer = await webmBlob.arrayBuffer()
  const audioBuffer = await audioContext.decodeAudioData(arrayBuffer)
  
  // Get mono channel
  const channelData = audioBuffer.getChannelData(0)
  
  // Convert to 16-bit PCM
  const pcmData = new Int16Array(channelData.length)
  for (let i = 0; i < channelData.length; i++) {
    const s = Math.max(-1, Math.min(1, channelData[i]))
    pcmData[i] = s < 0 ? s * 0x8000 : s * 0x7FFF
  }
  
  // Create WAV blob
  const wavBuffer = createWavBuffer(pcmData, 16000)
  return new Blob([wavBuffer], { type: 'audio/wav' })
}

function createWavBuffer(pcmData: Int16Array, sampleRate: number): ArrayBuffer {
  const buffer = new ArrayBuffer(44 + pcmData.length * 2)
  const view = new DataView(buffer)
  
  // WAV header
  writeString(view, 0, 'RIFF')
  view.setUint32(4, 36 + pcmData.length * 2, true)
  writeString(view, 8, 'WAVE')
  writeString(view, 12, 'fmt ')
  view.setUint32(16, 16, true) // fmt chunk size
  view.setUint16(20, 1, true) // audio format (PCM)
  view.setUint16(22, 1, true) // num channels
  view.setUint32(24, sampleRate, true)
  view.setUint32(28, sampleRate * 2, true) // byte rate
  view.setUint16(32, 2, true) // block align
  view.setUint16(34, 16, true) // bits per sample
  writeString(view, 36, 'data')
  view.setUint32(40, pcmData.length * 2, true)
  
  // PCM data
  const dataView = new Int16Array(buffer, 44)
  dataView.set(pcmData)
  
  return buffer
}

function writeString(view: DataView, offset: number, string: string) {
  for (let i = 0; i < string.length; i++) {
    view.setUint8(offset + i, string.charCodeAt(i))
  }
}

