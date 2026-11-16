import { useEffect, useRef, useState } from 'react'
import type { CSSProperties, FormEvent } from 'react'
import { ArrowUp, BookOpen, CheckCheck, Lightbulb, SearchCheck, Sparkles } from 'lucide-react'
import { useSearchParams } from 'react-router-dom'
import { Badge, Button, Notice } from '../components/UI'
import { friendlyError } from '../services/api'
import { listCourses, sendChat } from '../services/edumonitor'
import type { ChatResponse, Course } from '../types/api'
import { dateLabel } from '../utils/display'

type ChatEntry = { id: number; question: string; reply?: ChatResponse; error?: string }
const SUGGESTIONS = ['¿Qué cursos tengo asignados?', '¿Cuál es el progreso de mis estudiantes?', '¿Qué calificaciones están pendientes?', '¿Qué alertas tiene este curso?']
export function ChatPage() {
  const [params, setParams] = useSearchParams()
  const [courses, setCourses] = useState<Course[]>([])
  const [courseId, setCourseId] = useState(params.get('curso') || '')
  const [message, setMessage] = useState(params.get('q') || '')
  const [entries, setEntries] = useState<ChatEntry[]>([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const endRef = useRef<HTMLDivElement>(null)
  useEffect(() => { listCourses().then(cs => { setCourses(cs); setCourseId(v => v || String(cs[0]?.id || '')) }).catch(e => setError(friendlyError(e))) }, [])
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' }) }, [entries])
  const submit = async (e: FormEvent) => {
    e.preventDefault(); const prompt = message.trim(); if (!prompt || busy) return
    setError(''); setMessage(''); setBusy(true)
    const id = Date.now()
    setEntries(old => [...old, { id, question: prompt }])
    try { const response = await sendChat(prompt, courseId ? Number(courseId) : undefined); setEntries(old => old.map(c => c.id === id ? { ...c, reply: response } : c)) }
    catch (err) { setEntries(old => old.map(c => c.id === id ? { ...c, error: friendlyError(err) } : c)) }
    finally { setBusy(false) }
  }
  const ask = (suggestion: string) => { if (!busy) setMessage(suggestion) }
  return <div className="chat-page">
    <header className="chat-top">
      <div><span className="eyebrow">Asistente docente</span><h1>Agente de IA</h1></div>
      <label className="chat-course-select"><BookOpen size={16}/><select aria-label="Seleccionar curso del chat" value={courseId} onChange={e => { setCourseId(e.target.value); setParams(e.target.value ? { curso: e.target.value } : {}) }}><option value="">Sin curso específico</option>{courses.map(c => <option value={c.id} key={c.id}>{c.shortName}</option>)}</select></label>
    </header>
    {error && <Notice tone="warning">{error}</Notice>}
    <div className="chat-messages" aria-live="polite">
      {!entries.length && <div className="chat-empty"><span className="chat-hero-icon"><Sparkles size={34}/></span><h2>¿En qué puedo ayudarte?</h2><p>Pregunta por cursos, calificaciones, progreso o alertas. El agente consulta tus datos autorizados y separa hechos, inferencias y recomendaciones.</p><div className="suggestions">{SUGGESTIONS.map((s, i) => <button type="button" key={s} style={{ ['--i' as string]: i } as CSSProperties} onClick={() => ask(s)}>{s}</button>)}</div></div>}
      {entries.map(entry => <div className="chat-entry" key={entry.id}>
        <div className="user-message"><div>{entry.question}</div></div>
        {entry.error ? <div className="assistant-message"><div className="message-content"><Notice tone="danger">{entry.error}</Notice><button type="button" className="text-button" onClick={() => ask(entry.question)}>Volver a escribir la pregunta</button></div></div>
          : entry.reply ? <div className="assistant-message"><div className="message-content">
            <div className="message-meta"><strong>EduMonitor AI</strong><Badge tone={entry.reply.meta.status === 'ok' ? 'success' : entry.reply.meta.status === 'partial' ? 'warning' : 'danger'}>{entry.reply.meta.status === 'ok' ? 'Respuesta' : entry.reply.meta.status === 'partial' ? 'Parcial' : entry.reply.meta.status === 'refused' ? 'Rechazada' : 'Error'}</Badge></div>
            {entry.reply.answer.message && <p>{entry.reply.answer.message}</p>}
            {entry.reply.meta.status === 'partial' && <Notice tone="warning">La respuesta es parcial; algunos datos no pudieron consultarse.</Notice>}
            {entry.reply.meta.status === 'refused' && <Notice tone="warning">El agente rechazó la consulta. No se mostraron datos no autorizados.</Notice>}
            <div className="answer-grid">
              <div className="answer-block"><h4><SearchCheck size={17}/> Hechos</h4>{entry.reply.answer.facts.length ? entry.reply.answer.facts.map((f, i) => <div className="answer-item" key={i}>{f.text}{f.sources.length > 0 && <div className="sources">Fuentes: {f.sources.map(s => `${s.tool} (paso ${s.stepN})`).join(' · ')}</div>}</div>) : <p className="muted small">No se recibieron hechos verificables.</p>}</div>
              <div className="answer-block"><h4><Lightbulb size={17}/> Inferencias</h4>{entry.reply.answer.inferences.length ? entry.reply.answer.inferences.map((f, i) => <div className="answer-item" key={i}>{f.text}{f.basedOn.length > 0 && <div className="sources">Basado en hechos: {f.basedOn.join(', ')}</div>}</div>) : <p className="muted small">Sin inferencias disponibles.</p>}</div>
              <div className="answer-block"><h4><CheckCheck size={17}/> Recomendaciones</h4>{entry.reply.answer.recommendations.length ? entry.reply.answer.recommendations.map((f, i) => <div className="answer-item" key={i}>{f.text}</div>) : <p className="muted small">Sin recomendaciones disponibles.</p>}</div>
            </div>
            {entry.reply.answer.unavailable.length > 0 && <Notice tone="warning">Datos no disponibles: {entry.reply.answer.unavailable.join(' · ')}</Notice>}
            <div className="chat-reply-footer">Última sincronización: {dateLabel(entry.reply.meta.lastSyncAt)} · Traza: {entry.reply.traceId}</div>
          </div></div>
          : <div className="assistant-message"><div className="message-content muted typing-row"><span className="typing" aria-hidden="true"><i/><i/><i/></span>Procesando consulta…</div></div>}
      </div>)}
      <div ref={endRef}/>
    </div>
    <form className="chat-composer" onSubmit={submit}><label htmlFor="chat-message" className="sr-only">Escribe tu pregunta</label><textarea id="chat-message" rows={1} maxLength={2000} value={message} placeholder="Escribe tu pregunta sobre el curso…" onChange={e => setMessage(e.target.value)} onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); e.currentTarget.form?.requestSubmit() } }} disabled={busy}/><Button type="submit" disabled={busy || !message.trim()} loading={busy} icon={<ArrowUp size={18}/>}>{busy ? 'Consultando…' : 'Enviar'}</Button></form>
    <p className="chat-note">Cada pregunta se procesa de forma independiente. Las cifras provienen de las herramientas del agente; la interfaz no inventa respuestas.</p>
  </div>
}
