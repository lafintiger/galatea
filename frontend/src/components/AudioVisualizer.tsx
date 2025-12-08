import { useEffect, useRef } from 'react'

interface AudioVisualizerProps {
  isActive: boolean
  level: number
  mode: 'idle' | 'recording' | 'playing' | 'listening'
}

export function AudioVisualizer({ isActive, level, mode }: AudioVisualizerProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const animationRef = useRef<number | null>(null)
  const barsRef = useRef<number[]>(Array(32).fill(0))

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const resize = () => {
      canvas.width = canvas.offsetWidth * window.devicePixelRatio
      canvas.height = canvas.offsetHeight * window.devicePixelRatio
      ctx.scale(window.devicePixelRatio, window.devicePixelRatio)
    }
    resize()
    window.addEventListener('resize', resize)

    const draw = () => {
      const width = canvas.offsetWidth
      const height = canvas.offsetHeight
      
      // Clear canvas
      ctx.clearRect(0, 0, width, height)

      const barCount = 32
      const barWidth = width / barCount - 2
      const maxBarHeight = height * 0.8

      // Update bars
      for (let i = 0; i < barCount; i++) {
        if (isActive) {
          // Generate wave pattern based on audio level
          const targetHeight = Math.sin(Date.now() / 200 + i * 0.3) * 0.3 + 0.5
          const levelMultiplier = mode === 'recording' ? level * 2 : 0.5 + Math.sin(Date.now() / 100 + i) * 0.3
          barsRef.current[i] += (targetHeight * levelMultiplier - barsRef.current[i]) * 0.2
        } else {
          // Decay to idle state
          barsRef.current[i] += (0.1 - barsRef.current[i]) * 0.1
        }
      }

      // Draw bars
      for (let i = 0; i < barCount; i++) {
        const barHeight = Math.max(4, barsRef.current[i] * maxBarHeight)
        const x = i * (barWidth + 2) + 1
        const y = (height - barHeight) / 2

        // Gradient based on mode
        let gradient: CanvasGradient
        if (mode === 'recording') {
          gradient = ctx.createLinearGradient(x, y + barHeight, x, y)
          gradient.addColorStop(0, '#eab308')  // Yellow for active recording
          gradient.addColorStop(1, '#facc15')
        } else if (mode === 'listening') {
          gradient = ctx.createLinearGradient(x, y + barHeight, x, y)
          gradient.addColorStop(0, '#22c55e')  // Green for listening/ready
          gradient.addColorStop(1, '#4ade80')
        } else if (mode === 'playing') {
          gradient = ctx.createLinearGradient(x, y + barHeight, x, y)
          gradient.addColorStop(0, '#00f0ff')
          gradient.addColorStop(0.5, '#00c4cc')
          gradient.addColorStop(1, '#ff00aa')
        } else {
          gradient = ctx.createLinearGradient(x, y + barHeight, x, y)
          gradient.addColorStop(0, '#334155')
          gradient.addColorStop(1, '#475569')
        }

        ctx.fillStyle = gradient
        ctx.beginPath()
        ctx.roundRect(x, y, barWidth, barHeight, 2)
        ctx.fill()

        // Add glow effect when active
        if (isActive) {
          ctx.shadowColor = mode === 'recording' ? '#eab308' : mode === 'listening' ? '#22c55e' : '#00f0ff'
          ctx.shadowBlur = 10
          ctx.fill()
          ctx.shadowBlur = 0
        }
      }

      animationRef.current = requestAnimationFrame(draw)
    }

    draw()

    return () => {
      window.removeEventListener('resize', resize)
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current)
      }
    }
  }, [isActive, level, mode])

  return (
    <div className="w-full h-full relative">
      <canvas
        ref={canvasRef}
        className="w-full h-full"
      />
      
      {/* Center orb */}
      <div className={`
        absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2
        w-16 h-16 rounded-full
        ${mode === 'recording' ? 'bg-yellow-500/20 border-yellow-500' : 
          mode === 'listening' ? 'bg-green-500/20 border-green-500' :
          mode === 'playing' ? 'bg-cyber-accent/20 border-cyber-accent' : 
          'bg-slate-700/20 border-slate-600'}
        border-2 transition-all duration-300
        ${isActive ? 'scale-110' : 'scale-100'}
      `}>
        <div className={`
          absolute inset-2 rounded-full
          ${mode === 'recording' ? 'bg-yellow-500/30' : 
            mode === 'listening' ? 'bg-green-500/30' :
            mode === 'playing' ? 'bg-cyber-accent/30' : 
            'bg-slate-600/30'}
          ${isActive ? 'animate-pulse' : ''}
        `} />
      </div>
    </div>
  )
}

