import { useEffect, useRef, useState } from 'react'
import type { CSSProperties } from 'react'
import { Bot, ChevronDown } from 'lucide-react'
import { CountUp, Ring } from './UI'

const depth = (d: number, extra?: CSSProperties): CSSProperties => ({ ['--d' as string]: d, ...extra })

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

const SCRIPT = [
  { q: '¿Qué falta por calificar?', a: 'Hay 1 entrega pendiente de calificar en el curso.' },
  { q: '¿Qué alertas tiene el curso?', a: '10 alertas activas: 9 de atención y 1 informativa.' },
  { q: '¿Cómo va el progreso?', a: 'Entrega 50 % y finalización 44,4 %, con datos parciales.' },
]

/** Conversación de ejemplo que se escribe sola; se pausa al pasar el cursor y se puede elegir la pregunta. */
function ChatDemo() {
  const [i, setI] = useState(0)
  const [q, setQ] = useState('')
  const [a, setA] = useState('')
  const [think, setThink] = useState(false)
  const [paused, setPaused] = useState(false)
  useEffect(() => {
    if (paused) return
    const item = SCRIPT[i]
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    const timers: number[] = []
    let t = 0
    const at = (ms: number, fn: () => void) => { t += ms; timers.push(window.setTimeout(fn, t)) }
    if (reduce) { at(0, () => { setQ(item.q); setA(item.a); setThink(false) }); return () => timers.forEach(clearTimeout) }
    at(0, () => { setQ(''); setA(''); setThink(false) })
    for (let k = 1; k <= item.q.length; k++) at(34, () => setQ(item.q.slice(0, k)))
    at(280, () => setThink(true))
    at(900, () => setThink(false))
    for (let k = 1; k <= item.a.length; k++) at(15, () => setA(item.a.slice(0, k)))
    at(3200, () => setI(n => (n + 1) % SCRIPT.length))
    return () => timers.forEach(clearTimeout)
  }, [i, paused])
  return <div onPointerEnter={() => setPaused(true)} onPointerLeave={() => setPaused(false)}>
    <small>Asistente académico</small>
    <div className="demo-thread" aria-live="off">
      {q && <div className="bubble">{q}</div>}
      {think && <div className="answer think"><span className="typing" aria-hidden="true"><i/><i/><i/></span></div>}
      {a && <div className="answer"><Bot size={14}/> {a}</div>}
    </div>
    <div className="demo-dots" role="tablist" aria-label="Preguntas de ejemplo">{SCRIPT.map((s, n) => <button key={s.q} type="button" role="tab" aria-selected={n === i} aria-label={s.q} className={n === i ? 'on' : ''} onClick={() => setI(n)}/>)}</div>
  </div>
}

const BARS = [38, 62, 48, 80, 57]

/** Tarjetas de ejemplo que se desplazan con el mouse (paralaje) y reaccionan al cursor. */
export function PreviewCards() {
  const [open, setOpen] = useState(false)
  return <>
    <div className="fl a" style={depth(16)}><div className="fl-in card-kpi">
      <small>Promedio del curso</small>
      <div className="kpi-row"><div className="big"><CountUp value={7.8} digits={1}/><span>/ 10</span></div><Ring value={78}/></div>
    </div></div>
    <div className="fl b" style={depth(-12)}><button type="button" className="fl-in card-alert" aria-expanded={open} onClick={() => setOpen(o => !o)}>
      <small>Alerta con evidencia</small>
      <div className="row"><span className="pip"/>Entregas insuficientes<ChevronDown size={16} className="chev"/></div>
      <div className="evidence" data-open={open}><div className="ev-in"><div><span>Valor observado</span><b>40 %</b></div><div><span>Umbral</span><b>60 %</b></div></div></div>
    </button></div>
    <div className="fl c" style={depth(-20)}><div className="fl-in card-bars">
      <small>Entregas por actividad</small>
      <div className="bars">{BARS.map((v, n) => <i key={n} style={{ ['--h' as string]: `${v}%`, ['--n' as string]: n } as CSSProperties} data-v={`${v} %`} tabIndex={-1}/>)}</div>
    </div></div>
    <div className="fl d" style={depth(12)}><div className="fl-in card-chat"><ChatDemo/></div></div>
  </>
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
