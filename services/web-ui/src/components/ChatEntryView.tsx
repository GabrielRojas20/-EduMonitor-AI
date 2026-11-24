import { CheckCheck, Lightbulb, SearchCheck } from 'lucide-react'
import { Badge, Notice } from './UI'
import type { ChatResponse } from '../types/api'
import { dateLabel } from '../utils/display'

export type ChatEntry = { id: number; question: string; reply?: ChatResponse; error?: string }
export function ChatEntryView({ entry, onRetry }: { entry: ChatEntry; onRetry: (question: string) => void }) {
  return <div className="chat-entry">
        <div className="user-message"><div>{entry.question}</div></div>
        {entry.error ? <div className="assistant-message"><div className="message-content"><Notice tone="danger">{entry.error}</Notice><button type="button" className="text-button" onClick={() => onRetry(entry.question)}>Volver a escribir la pregunta</button></div></div>
          : entry.reply ? <div className="assistant-message"><div className="message-content">
            <div className="message-meta"><strong>EduMonitor AI</strong><Badge tone={entry.reply.meta.status === 'ok' ? 'success' : entry.reply.meta.status === 'partial' ? 'warning' : 'danger'}>{entry.reply.meta.status === 'ok' ? 'Respuesta' : entry.reply.meta.status === 'partial' ? 'Parcial' : entry.reply.meta.status === 'refused' ? 'Rechazada' : 'Error'}</Badge></div>
            {entry.reply.answer.message && <p>{entry.reply.answer.message}</p>}
            {entry.reply.meta.status === 'partial' && <Notice tone="warning">La respuesta es parcial; algunos datos no pudieron consultarse.</Notice>}
            {entry.reply.meta.status === 'refused' && <Notice tone="warning">El agente rechazó la consulta. No se mostraron datos no autorizados.</Notice>}
            {(entry.reply.answer.facts.length > 0 || entry.reply.answer.inferences.length > 0 || entry.reply.answer.recommendations.length > 0) &&
            <div className="answer-grid">
              <div className="answer-block"><h4><SearchCheck size={17}/> Hechos</h4>{entry.reply.answer.facts.length ? entry.reply.answer.facts.map((f, i) => <div className="answer-item" key={i}>{f.text}{f.sources.length > 0 && <div className="sources">Fuentes: {f.sources.map(s => `${s.tool} (paso ${s.stepN})`).join(' · ')}</div>}</div>) : <p className="muted small">No se recibieron hechos verificables.</p>}</div>
              <div className="answer-block"><h4><Lightbulb size={17}/> Inferencias</h4>{entry.reply.answer.inferences.length ? entry.reply.answer.inferences.map((f, i) => <div className="answer-item" key={i}>{f.text}{f.basedOn.length > 0 && <div className="sources">Basado en hechos: {f.basedOn.map(index => index + 1).join(', ')}</div>}</div>) : <p className="muted small">Sin inferencias disponibles.</p>}</div>
              <div className="answer-block"><h4><CheckCheck size={17}/> Recomendaciones</h4>{entry.reply.answer.recommendations.length ? entry.reply.answer.recommendations.map((f, i) => <div className="answer-item" key={i}>{f.text}</div>) : <p className="muted small">Sin recomendaciones disponibles.</p>}</div>
            </div>}
            {entry.reply.answer.unavailable.length > 0 && <Notice tone="warning">Datos no disponibles: {entry.reply.answer.unavailable.join(' · ')}</Notice>}
            <div className="chat-reply-footer">Última sincronización: {dateLabel(entry.reply.meta.lastSyncAt)} · Traza: {entry.reply.traceId}</div>
          </div></div>
          : <div className="assistant-message"><div className="message-content muted typing-row"><span className="typing" aria-hidden="true"><i/><i/><i/></span>Procesando consulta…</div></div>}

  </div>
}
