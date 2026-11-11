import { useState } from 'react'
import type { FormEvent } from 'react'
import { Activity, ArrowRight, Eye, EyeOff, GraduationCap, LockKeyhole, Mail, ShieldCheck } from 'lucide-react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { friendlyError } from '../services/api'
import { Button, Notice } from '../components/UI'

export function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const { signIn, expired, clearExpired } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const redirect = (location.state as { from?: string } | null)?.from || '/cursos'
  async function submit(e: FormEvent) {
    e.preventDefault()
    setError('')
    if (!email.trim() || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) { setError('Introduce un correo válido.'); return }
    if (!password) { setError('Introduce tu contraseña.'); return }
    setBusy(true)
    try { await signIn(email.trim(), password); navigate(redirect, { replace: true }) }
    catch (err) { setError(friendlyError(err)) }
    finally { setBusy(false) }
  }
  return <div className="auth-page"><div className="auth-left">
    <div className="auth-brand"><div className="brand-icon"><Activity size={23}/></div><strong>EduMonitor <span>AI</span></strong></div>
    <div className="auth-hero"><div className="auth-pill"><GraduationCap size={15}/> Plataforma docente</div><h1>Entiende el progreso de tus estudiantes.</h1><p>Indicadores verificables, alertas con evidencia y apoyo inteligente para tomar mejores decisiones académicas.</p><div className="auth-features"><span><ShieldCheck size={18}/> Acceso seguro</span><span><Activity size={18}/> Información de Moodle</span></div></div>
    <div className="auth-bottom">Seguimiento académico basado en evidencia · EduMonitor AI</div>
  </div><div className="auth-right"><div className="login-box"><div className="login-symbol"><LockKeyhole size={28}/></div><span className="eyebrow">BIENVENIDO DE NUEVO</span><h2>Iniciar sesión</h2><p>Accede a tus cursos y consulta el rendimiento académico desde un solo lugar.</p>
    {expired && <div className="login-notice"><Notice tone="warning">Tu sesión terminó. Vuelve a iniciar sesión.</Notice><button className="text-button" onClick={clearExpired}>Entendido</button></div>}
    {error && <Notice tone="danger">{error}</Notice>}
    <form onSubmit={submit} noValidate><label htmlFor="email">Correo electrónico</label><div className="input-wrap"><Mail size={18}/><input id="email" type="email" autoComplete="username" value={email} onChange={e => setEmail(e.target.value)} placeholder="correo@institucion.edu" disabled={busy} required /></div>
      <label htmlFor="password">Contraseña</label><div className="input-wrap"><LockKeyhole size={18}/><input id="password" type={showPassword ? 'text' : 'password'} autoComplete="current-password" value={password} onChange={e => setPassword(e.target.value)} placeholder="Tu contraseña" disabled={busy} required /><button type="button" className="reveal" onClick={() => setShowPassword(v=>!v)} aria-label={showPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'}>{showPassword ? <EyeOff size={18}/> : <Eye size={18}/>}</button></div>
      <Button className="login-submit" type="submit" loading={busy} disabled={busy} icon={<ArrowRight size={18}/>}>{busy ? 'Validando credenciales…' : 'Iniciar sesión'}</Button></form>
    <div className="login-help"><ShieldCheck size={16}/> Tu sesión utiliza el token de acceso del gateway.</div>
  </div></div></div>
}
