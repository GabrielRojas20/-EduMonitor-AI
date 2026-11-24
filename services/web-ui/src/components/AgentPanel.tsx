import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { ArrowUp, Sparkles } from 'lucide-react'
import { Button, Card } from './UI'
import { friendlyError } from '../services/api'
import { sendChat } from '../services/edumonitor'
import { ChatEntryView } from '../pages/ChatPage'
import type { ChatEntry } from '../pages/ChatPage'

/** Consultas establecidas: el docente las pulsa o escribe su propia pregunta. */
const QUICK_QUESTIONS = ['¿Cuántos estudiantes tengo?', '¿Qué alertas hay?', '¿Qué falta por calificar?', '¿Cómo va el curso?', 'Genera el informe del curso']

/** Chat del agente dentro de la página de un curso: el curso ya está fijado, así que no hay selector. */
export function AgentPanel({ courseId, courseName }: { courseId: number; courseName: string }) {
  const [entries, setEntries] = useState<ChatEntry[]>([])
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)
  const endRef = useRef<HTMLDivElement>(null)
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
  const submit = (e: FormEvent) => { e.preventDefault(); void ask(message) }
  return <Card className="agent-panel">
    <div className="agent-head"><span className="agent-icon"><Sparkles size={18}/></span><div><h2>Agente de IA · {courseName}</h2><p>Consulta los datos de este curso. Cada pregunta se procesa de forma independiente.</p></div></div>
    <div className="suggestions agent-quick" role="group" aria-label="Consultas establecidas">{QUICK_QUESTIONS.map(q => <button type="button" key={q} disabled={busy} onClick={() => void ask(q)}>{q}</button>)}</div>
    {entries.length > 0 && <div className="agent-messages" aria-live="polite">{entries.map(entry => <ChatEntryView key={entry.id} entry={entry} onRetry={q => setMessage(q)}/>)}<div ref={endRef}/></div>}
    <form className="chat-composer" onSubmit={submit}>
      <label htmlFor="agent-panel-message" className="sr-only">Escribe tu pregunta sobre {courseName}</label>
      <textarea id="agent-panel-message" rows={1} maxLength={2000} value={message} placeholder={`Escribe tu pregunta sobre ${courseName}…`} onChange={e => setMessage(e.target.value)} onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); e.currentTarget.form?.requestSubmit() } }} disabled={busy}/>
      <Button type="submit" disabled={busy || !message.trim()} loading={busy} icon={<ArrowUp size={18}/>}>{busy ? 'Consultando…' : 'Enviar'}</Button>
    </form>
  </Card>
}
