import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { ArrowUp, History, Sparkles, Trash2, UserRound, X } from 'lucide-react'
import { Button, Card } from './UI'
import { useAuth } from '../hooks/useAuth'
import { friendlyError } from '../services/api'
import { sendChat } from '../services/edumonitor'
import { ChatEntryView } from './ChatEntryView'
import type { ChatEntry } from './ChatEntryView'

/** Consultas establecidas del curso: el docente las pulsa o escribe su propia pregunta. */
const COURSE_QUESTIONS = ['¿Cuántos estudiantes tengo?', '¿Qué alertas hay?', '¿Qué falta por calificar?', '¿Cómo va el curso?', 'Genera el informe del curso']
const studentQuestions = (name: string) => [`¿Cómo va ${name}?`, `¿Qué alertas tiene ${name}?`, `¿Qué notas tiene ${name}?`]

const MAX_SAVED = 30

/** El historial se guarda en este navegador, por docente y por curso. Solo se guardan las consultas que ya tienen respuesta. */
const storageKey = (userId: number | undefined, courseId: number) => `edumonitor.agent-history.${userId ?? 'anon'}.${courseId}`
function loadHistory(key: string): ChatEntry[] {
  try {
    const parsed: unknown = JSON.parse(localStorage.getItem(key) || '[]')
    return Array.isArray(parsed) ? (parsed as ChatEntry[]).filter(e => e && typeof e.question === 'string' && e.reply) : []
  } catch { return [] }
}
function saveHistory(key: string, entries: ChatEntry[]) {
  try { localStorage.setItem(key, JSON.stringify(entries.filter(e => e.reply).slice(-MAX_SAVED))) } catch { /* sin almacenamiento: el chat sigue funcionando */ }
}

export interface AgentStudent { id: number; name: string }

/** Chat del agente dentro de la página de un curso: el curso ya está fijado, así que no hay selector. */
export function AgentPanel({ courseId, courseName, student, onClearStudent, initialQuestion }: {
  courseId: number; courseName: string; student?: AgentStudent | null; onClearStudent?: () => void; initialQuestion?: string
}) {
  const { user } = useAuth()
  const key = storageKey(user?.id, courseId)
  const [entries, setEntries] = useState<ChatEntry[]>(() => loadHistory(key))
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)
  const root = useRef<HTMLDivElement>(null)
  const endRef = useRef<HTMLDivElement>(null)
  const asked = useRef(false)
  const saved = entries.filter(e => e.reply).length
  useEffect(() => { saveHistory(key, entries) }, [key, entries])
  useEffect(() => { if (entries.length) endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' }) }, [entries])
  const ask = async (question: string) => {
    const prompt = question.trim()
    if (!prompt || busy) return
    setMessage(''); setBusy(true)
    const id = Date.now()
    setEntries(old => [...old, { id, question: prompt }])
    try { const reply = await sendChat(prompt, courseId); setEntries(old => old.map(e => e.id === id ? { ...e, reply } : e)) }
    catch (err) { setEntries(old => old.map(e => e.id === id ? { ...e, error: friendlyError(err) } : e)) }
    finally { setBusy(false) }
  }
  // Al llegar desde una ficha o desde «Preguntar al agente», el panel se muestra y, si trae una pregunta, la envía una vez.
  useEffect(() => {
    if (!student && !initialQuestion) return
    root.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }, [student, initialQuestion])
  useEffect(() => {
    if (!initialQuestion || asked.current) return
    asked.current = true
    void ask(initialQuestion)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialQuestion])
  const questions = student ? studentQuestions(student.name) : COURSE_QUESTIONS
  const submit = (e: FormEvent) => { e.preventDefault(); void ask(message) }
  return <div id="agente" ref={root}><Card className="agent-panel">
    <div className="agent-head"><span className="agent-icon"><Sparkles size={18}/></span><div><h2>Agente de IA · {courseName}</h2><p>Consulta los datos de este curso. Cada pregunta se procesa de forma independiente.</p></div></div>
    {student && <div className="agent-context"><UserRound size={15}/><span>Ficha individual: <strong>{student.name}</strong></span>{onClearStudent && <button type="button" onClick={onClearStudent} aria-label="Quitar el contexto del estudiante"><X size={14}/></button>}</div>}
    <div className="suggestions agent-quick" role="group" aria-label="Consultas establecidas">{questions.map(q => <button type="button" key={q} disabled={busy} onClick={() => void ask(q)}>{q}</button>)}</div>
    {entries.length > 0 && <>
      <div className="agent-history-bar"><span><History size={14}/> Historial de este curso · {saved} {saved === 1 ? 'consulta guardada' : 'consultas guardadas'} en este navegador</span><button type="button" onClick={() => { setEntries([]); try { localStorage.removeItem(key) } catch { /* nada que borrar */ } }} disabled={busy}><Trash2 size={13}/> Borrar historial</button></div>
      <div className="agent-messages" aria-live="polite">{entries.map(entry => <ChatEntryView key={entry.id} entry={entry} onRetry={q => setMessage(q)}/>)}<div ref={endRef}/></div>
    </>}
    <form className="chat-composer" onSubmit={submit}>
      <label htmlFor="agent-panel-message" className="sr-only">Escribe tu pregunta sobre {courseName}</label>
      <textarea id="agent-panel-message" rows={1} maxLength={2000} value={message} placeholder={student ? `Escribe tu pregunta sobre ${student.name}…` : `Escribe tu pregunta sobre ${courseName}…`} onChange={e => setMessage(e.target.value)} onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); e.currentTarget.form?.requestSubmit() } }} disabled={busy}/>
      <Button type="submit" disabled={busy || !message.trim()} loading={busy} icon={<ArrowUp size={18}/>}>{busy ? 'Consultando…' : 'Enviar'}</Button>
    </form>
  </Card></div>
}
