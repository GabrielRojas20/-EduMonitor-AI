import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ChatEntryView } from './ChatEntryView'
import type { ChatEntry } from './ChatEntryView'
import type { ChatResponse } from '../types/api'

const reply = (answer: Partial<ChatResponse['answer']>): ChatResponse => ({
  traceId: 't-1', meta: { courseId: 201, lastSyncAt: null, status: 'ok' },
  answer: { message: null, facts: [], inferences: [], recommendations: [], unavailable: [], ...answer },
} as unknown as ChatResponse)
const entry = (answer: Partial<ChatResponse['answer']>): ChatEntry => ({ id: 1, question: '¿Hola?', reply: reply(answer) })

describe('Respuesta del agente', () => {
  it('muestra solo el mensaje cuando no trae hechos, inferencias ni recomendaciones', () => {
    render(<ChatEntryView entry={entry({ message: 'Puedo ayudarte con tus cursos.' })} onRetry={() => {}} />)
    expect(screen.getByText('Puedo ayudarte con tus cursos.')).toBeInTheDocument()
    expect(screen.queryByText('Hechos')).not.toBeInTheDocument()
    expect(screen.queryByText('Sin inferencias disponibles.')).not.toBeInTheDocument()
  })

  it('mantiene los tres bloques cuando hay al menos un hecho', () => {
    render(<ChatEntryView entry={entry({ facts: [{ text: '25 estudiantes', sources: [] }] as never })} onRetry={() => {}} />)
    expect(screen.getByText('Hechos')).toBeInTheDocument()
    expect(screen.getByText('Inferencias')).toBeInTheDocument()
    expect(screen.getByText('Recomendaciones')).toBeInTheDocument()
  })
})
