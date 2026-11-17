import { useRef, useState } from 'react'
import type { CSSProperties, FormEvent, KeyboardEvent, PointerEvent } from 'react'
import { ArrowRight, Check, Eye, EyeOff, LockKeyhole, Mail, ShieldCheck, Sparkles, TriangleAlert } from 'lucide-react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { friendlyError } from '../services/api'
import { Button, CountUp, Notice } from '../components/UI'
import { DotField, PreviewCards, Rotator } from '../components/LoginArt'
import { greeting } from '../utils/display'

const delay = (i: number): CSSProperties => ({ ['--i' as string]: i })

export function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [busy, setBusy] = useState(false)
  const [done, setDone] = useState(false)
  const [error, setError] = useState('')
  const [shake, setShake] = useState(false)
  const [caps, setCaps] = useState(false)
  const stage = useRef<HTMLDivElement>(null)
  const { signIn, expired, clearExpired } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const redirect = (location.state as { from?: string } | null)?.from || '/cursos'
  const [hello] = useState(greeting)
  const fail = (message: string) => { setError(message); setShake(true); window.setTimeout(() => setShake(false), 500) }
  async function submit(e: FormEvent) {
    e.preventDefault()
    setError('')
    if (!email.trim() || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) { fail('Introduce un correo válido.'); return }
    if (!password) { fail('Introduce tu contraseña.'); return }
    setBusy(true)
    try {
      await signIn(email.trim(), password)
      setDone(true)
      await new Promise(r => window.setTimeout(r, 520))
      navigate(redirect, { replace: true, viewTransition: true })
    } catch (err) { fail(friendlyError(err)); setBusy(false) }
  }
  // El paralaje de las tarjetas y el brillo de la tarjeta principal siguen al cursor.
  const onStageMove = (e: PointerEvent<HTMLDivElement>) => {
    const el = stage.current
    if (!el) return
    el.style.setProperty('--mx', String(((e.clientX / window.innerWidth) - 0.5) * 2))
    el.style.setProperty('--my', String(((e.clientY / window.innerHeight) - 0.5) * 2))
  }
  const onCardMove = (e: PointerEvent<HTMLElement>) => {
    const r = e.currentTarget.getBoundingClientRect()
    e.currentTarget.style.setProperty('--cx', `${e.clientX - r.left}px`)
    e.currentTarget.style.setProperty('--cy', `${e.clientY - r.top}px`)
  }
  const onKey = (e: KeyboardEvent<HTMLInputElement>) => setCaps(e.getModifierState('CapsLock'))
  return <div className="lg" ref={stage} onPointerMove={onStageMove}>
    <div className="lg-bg" aria-hidden="true"><i className="blob b1"/><i className="blob b2"/><DotField/></div>
    <header className="lg-top reveal" style={delay(0)}>
      <div className="lg-brand">EduMonitor <b>AI</b></div>
      <Rotator/>
    </header>
    <main className="lg-center">
      <section className="lg-pitch" aria-label="Presentación de EduMonitor AI">
        <p className="pitch-title reveal" style={delay(1)}>El seguimiento académico, con <em>evidencia</em>.</p>
        <p className="pitch-sub reveal" style={delay(2)}>Indicadores verificables, alertas que explican su causa y un asistente que interpreta los datos de tus cursos de Moodle sin inventar nada.</p>
        <dl className="pitch-stats reveal" style={delay(3)}>
          <div><dd><CountUp value={5}/></dd><dt>herramientas del agente</dt></div>
          <div><dd><CountUp value={20}/></dd><dt>escenarios de evaluación aprobados</dt></div>
          <div><dd><CountUp value={309}/><small>/ 309</small></dd><dt>cifras con respaldo en los datos</dt></div>
        </dl>
        <div className="pitch-cards" aria-hidden="true"><PreviewCards/></div>
      </section>
      <section className={`lg-card${shake ? ' shake' : ''}`} aria-labelledby="login-title" onPointerMove={onCardMove}>
        <div className="lg-badge reveal" style={delay(2)}><Sparkles size={14}/> Plataforma para docentes</div>
        <h1 id="login-title" className="reveal" style={delay(3)}>{hello[0]} <em>{hello[1]}</em></h1>
        <p className="reveal" style={delay(4)}>Inicia sesión para consultar tus cursos, alertas y al asistente académico.</p>
        {expired && <div><Notice tone="warning">Tu sesión terminó. Vuelve a iniciar sesión.</Notice><button className="text-button" onClick={clearExpired}>Entendido</button></div>}
        {error && <Notice tone="danger">{error}</Notice>}
        <form onSubmit={submit} noValidate>
          <div className="field reveal" style={delay(5)}>
            <label htmlFor="email">Correo electrónico</label>
            <div className="input-wrap"><Mail size={18}/><input id="email" type="email" autoComplete="username" inputMode="email" autoCapitalize="none" spellCheck={false} value={email} onChange={e => setEmail(e.target.value)} placeholder="correo@institucion.edu" disabled={busy} required /></div>
          </div>
          <div className="field reveal" style={delay(6)}>
            <label htmlFor="password">Contraseña</label>
            <div className="input-wrap"><LockKeyhole size={18}/><input id="password" type={showPassword ? 'text' : 'password'} autoComplete="current-password" value={password} onChange={e => setPassword(e.target.value)} onKeyDown={onKey} onKeyUp={onKey} onBlur={() => setCaps(false)} placeholder="Tu contraseña" disabled={busy} required /><button type="button" className="reveal-btn" onClick={() => setShowPassword(v => !v)} aria-label={showPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'}>{showPassword ? <EyeOff size={18}/> : <Eye size={18}/>}</button></div>
            <p className="caps-hint" data-on={caps} role="status">{caps && <><TriangleAlert size={14}/> Bloq Mayús está activado</>}</p>
          </div>
          <Button className={`login-submit reveal${done ? ' is-done' : ''}`} style={delay(7)} type="submit" loading={busy && !done} disabled={busy}>{done ? <><Check size={18}/> Listo, entrando…</> : busy ? 'Validando credenciales…' : <>Iniciar sesión <ArrowRight size={18}/></>}</Button>
        </form>
        <div className="lg-help reveal" style={delay(8)}><ShieldCheck size={16}/> Tu sesión usa el token de acceso del gateway.</div>
      </section>
    </main>
    <footer className="lg-foot reveal" style={delay(9)}><span><ShieldCheck size={15}/> Solo lectura</span><span><LockKeyhole size={15}/> Acceso por curso</span><span><Sparkles size={15}/> IA local</span><span className="lg-foot-note">Vista previa ilustrativa</span></footer>
  </div>
}
