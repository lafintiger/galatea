import { useState, useRef, useCallback } from 'react'
import { Camera, Upload, X, Eye, Loader2, ImageIcon } from 'lucide-react'
import { useSettingsStore } from '../stores/settingsStore'

interface VisionCaptureProps {
  onAnalyze: (imageBase64: string, prompt: string) => void
  isAnalyzing: boolean
}

export function VisionCapture({ onAnalyze, isAnalyzing }: VisionCaptureProps) {
  const { settings } = useSettingsStore()
  const [showModal, setShowModal] = useState(false)
  const [previewImage, setPreviewImage] = useState<string | null>(null)
  const [prompt, setPrompt] = useState('')
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    const reader = new FileReader()
    reader.onload = () => {
      const base64 = (reader.result as string).split(',')[1]
      setPreviewImage(reader.result as string)
    }
    reader.readAsDataURL(file)
  }, [])

  const handleScreenshot = useCallback(async () => {
    try {
      // Request screen capture
      const stream = await navigator.mediaDevices.getDisplayMedia({
        video: { displaySurface: 'monitor' } as any
      })
      
      // Create video element to capture frame
      const video = document.createElement('video')
      video.srcObject = stream
      await video.play()
      
      // Draw to canvas
      const canvas = document.createElement('canvas')
      canvas.width = video.videoWidth
      canvas.height = video.videoHeight
      const ctx = canvas.getContext('2d')!
      ctx.drawImage(video, 0, 0)
      
      // Stop the stream
      stream.getTracks().forEach(track => track.stop())
      
      // Get base64
      const dataUrl = canvas.toDataURL('image/png')
      setPreviewImage(dataUrl)
      
    } catch (err) {
      console.error('Screenshot failed:', err)
      alert('Screenshot capture was cancelled or failed')
    }
  }, [])

  const handleAnalyze = useCallback(() => {
    if (!previewImage) return
    
    const base64 = previewImage.split(',')[1]
    const finalPrompt = prompt.trim() || 'Describe this image in detail.'
    
    onAnalyze(base64, finalPrompt)
    
    // Reset state
    setShowModal(false)
    setPreviewImage(null)
    setPrompt('')
  }, [previewImage, prompt, onAnalyze])

  const handleClose = useCallback(() => {
    setShowModal(false)
    setPreviewImage(null)
    setPrompt('')
  }, [])

  return (
    <>
      {/* Trigger Button */}
      <button
        onClick={() => setShowModal(true)}
        disabled={isAnalyzing}
        className="p-2 rounded-lg border border-purple-500/50 bg-purple-500/10
                   hover:bg-purple-500/20 transition-colors disabled:opacity-50"
        title="Vision - Analyze Image"
      >
        {isAnalyzing ? (
          <Loader2 className="w-5 h-5 text-purple-400 animate-spin" />
        ) : (
          <Eye className="w-5 h-5 text-purple-400" />
        )}
      </button>

      {/* Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
          <div className="bg-cyber-dark border border-purple-500/30 rounded-lg w-full max-w-lg">
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-purple-500/20">
              <h3 className="font-display text-lg text-purple-400 flex items-center gap-2">
                <Eye className="w-5 h-5" />
                Vision Analysis
              </h3>
              <button
                onClick={handleClose}
                className="p-1 hover:bg-purple-500/20 rounded transition-colors"
              >
                <X className="w-5 h-5 text-slate-400" />
              </button>
            </div>

            <div className="p-4 space-y-4">
              {/* Image Preview or Capture Options */}
              {previewImage ? (
                <div className="space-y-3">
                  <div className="relative rounded-lg overflow-hidden border border-purple-500/20">
                    <img 
                      src={previewImage} 
                      alt="Preview" 
                      className="w-full max-h-64 object-contain bg-black"
                    />
                    <button
                      onClick={() => setPreviewImage(null)}
                      className="absolute top-2 right-2 p-1 bg-black/50 rounded-full
                                 hover:bg-black/70 transition-colors"
                    >
                      <X className="w-4 h-4 text-white" />
                    </button>
                  </div>
                  
                  {/* Prompt Input */}
                  <div>
                    <label className="block text-xs text-slate-500 mb-1">
                      What would you like to know? (optional)
                    </label>
                    <input
                      type="text"
                      value={prompt}
                      onChange={(e) => setPrompt(e.target.value)}
                      placeholder="Describe this image..."
                      className="w-full px-3 py-2 rounded bg-cyber-darker border border-purple-500/30
                                 text-slate-200 text-sm placeholder-slate-500
                                 focus:outline-none focus:border-purple-500"
                    />
                  </div>

                  {/* Quick Prompts */}
                  <div className="flex flex-wrap gap-2">
                    <button
                      onClick={() => setPrompt('What do you see in this image?')}
                      className="px-2 py-1 text-xs rounded bg-purple-500/10 border border-purple-500/30
                                 text-purple-400 hover:bg-purple-500/20 transition-colors"
                    >
                      Describe
                    </button>
                    <button
                      onClick={() => setPrompt('Read all the text in this image.')}
                      className="px-2 py-1 text-xs rounded bg-blue-500/10 border border-blue-500/30
                                 text-blue-400 hover:bg-blue-500/20 transition-colors"
                    >
                      Read Text
                    </button>
                    <button
                      onClick={() => setPrompt('What is happening in this image?')}
                      className="px-2 py-1 text-xs rounded bg-green-500/10 border border-green-500/30
                                 text-green-400 hover:bg-green-500/20 transition-colors"
                    >
                      Explain
                    </button>
                  </div>
                </div>
              ) : (
                <div className="grid grid-cols-2 gap-3">
                  {/* Screenshot Button */}
                  <button
                    onClick={handleScreenshot}
                    className="flex flex-col items-center gap-2 p-6 rounded-lg
                               bg-purple-500/10 border border-purple-500/30
                               hover:bg-purple-500/20 hover:border-purple-500/50
                               transition-colors group"
                  >
                    <Camera className="w-8 h-8 text-purple-400 group-hover:scale-110 transition-transform" />
                    <span className="text-sm text-purple-400">Screenshot</span>
                    <span className="text-xs text-slate-500">Capture your screen</span>
                  </button>

                  {/* Upload Button */}
                  <button
                    onClick={() => fileInputRef.current?.click()}
                    className="flex flex-col items-center gap-2 p-6 rounded-lg
                               bg-blue-500/10 border border-blue-500/30
                               hover:bg-blue-500/20 hover:border-blue-500/50
                               transition-colors group"
                  >
                    <Upload className="w-8 h-8 text-blue-400 group-hover:scale-110 transition-transform" />
                    <span className="text-sm text-blue-400">Upload</span>
                    <span className="text-xs text-slate-500">Choose an image</span>
                  </button>
                  
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/*"
                    onChange={handleFileSelect}
                    className="hidden"
                  />
                </div>
              )}

              {/* Action Buttons */}
              <div className="flex gap-3 pt-2">
                <button
                  onClick={handleClose}
                  className="flex-1 px-4 py-2 rounded-lg border border-slate-600 text-slate-400
                             hover:border-slate-500 transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleAnalyze}
                  disabled={!previewImage || isAnalyzing}
                  className="flex-1 px-4 py-2 rounded-lg bg-purple-500/20 border border-purple-500/50
                             text-purple-400 hover:bg-purple-500/30 transition-colors
                             disabled:opacity-50 disabled:cursor-not-allowed
                             flex items-center justify-center gap-2"
                >
                  {isAnalyzing ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Analyzing...
                    </>
                  ) : (
                    <>
                      <Eye className="w-4 h-4" />
                      Ask {settings.assistant_nickname}
                    </>
                  )}
                </button>
              </div>
            </div>

            {/* Footer Info */}
            <div className="px-4 py-3 border-t border-purple-500/20 bg-purple-500/5">
              <p className="text-xs text-slate-500 text-center">
                {settings.assistant_nickname} will analyze the image and describe what she sees
              </p>
            </div>
          </div>
        </div>
      )}
    </>
  )
}

