import { useEffect, useRef, useState } from 'react'

/** Campo de puntos que crecen y se oscurecen cerca del cursor. */
export function DotField() {
  const ref = useRef<HTMLCanvasElement>(null)
  useEffect(() => {
    const canvas = ref.current
    const ctx = canvas?.getContext('2d')
    if (!canvas || !ctx) return
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    const GAP = 28
    let w = 0, h = 0, mx = -999, my = -999, tx = -999, ty = -999, raf = 0, running = false
    const draw = () => {
      ctx.clearRect(0, 0, w, h)
      ctx.fillStyle = '#0a0a0a'
      for (let x = GAP / 2; x < w; x += GAP) {
        for (let y = GAP / 2; y < h; y += GAP) {
          const k = Math.max(0, 1 - Math.hypot(x - mx, y - my) / 180)
          ctx.globalAlpha = 0.13 + k * 0.72
          ctx.beginPath()
          ctx.arc(x, y, 1 + k * 2.8, 0, Math.PI * 2)
          ctx.fill()
        }
      }
    }
    const resize = () => {
      const dpr = Math.min(2, window.devicePixelRatio || 1)
      w = canvas.clientWidth; h = canvas.clientHeight
      canvas.width = w * dpr; canvas.height = h * dpr
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
      draw()
    }
    const tick = () => {
      mx += (tx - mx) * 0.16; my += (ty - my) * 0.16
      draw()
      if (Math.hypot(tx - mx, ty - my) > 0.6) raf = requestAnimationFrame(tick)
      else running = false
    }
    const kick = () => { if (!reduce && !running) { running = true; raf = requestAnimationFrame(tick) } }
    const move = (e: PointerEvent) => {
      const r = canvas.getBoundingClientRect()
      tx = e.clientX - r.left; ty = e.clientY - r.top
      if (mx < -900) { mx = tx; my = ty }
      kick()
    }
    const leave = () => { tx = -999; ty = -999; mx = Math.min(mx, w + 400); kick() }
    resize()
    window.addEventListener('resize', resize)
    window.addEventListener('pointermove', move)
    document.addEventListener('pointerleave', leave)
    return () => { cancelAnimationFrame(raf); window.removeEventListener('resize', resize); window.removeEventListener('pointermove', move); document.removeEventListener('pointerleave', leave) }
  }, [])
  return <canvas ref={ref} className="dot-field" aria-hidden="true"/>
}

const PHRASES = ['Indicadores verificables', 'Alertas con evidencia', 'Un asistente que no inventa', 'Datos de Moodle, solo lectura']

/** Frase que cambia sola cada pocos segundos. */
export function Rotator() {
  const [i, setI] = useState(0)
  useEffect(() => {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
    const t = window.setInterval(() => setI(n => (n + 1) % PHRASES.length), 2800)
    return () => window.clearInterval(t)
  }, [])
  return <span className="rotator" aria-live="off"><span className="rot-dot"/><span className="rot-text" key={i}>{PHRASES[i]}</span></span>
}
