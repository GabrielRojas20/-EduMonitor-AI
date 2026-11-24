import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { ReportPage } from './ReportPage'
import { fetchAll, getCourse, getCourseReport } from '../services/edumonitor'

vi.mock('../services/edumonitor', () => ({ getCourse: vi.fn(), getCourseReport: vi.fn(), getStudents: vi.fn(), fetchAll: vi.fn() }))

const renderPage = () => render(<MemoryRouter initialEntries={['/cursos/2/informe']}><Routes><Route path="/cursos/:id/informe" element={<ReportPage />} /></Routes></MemoryRouter>)

describe('Informe académico del curso', () => {
  beforeEach(() => {
    vi.mocked(getCourse).mockReset().mockResolvedValue({ id: 2, shortName: 'PRUEBA01', fullName: 'Curso ficticio' })
    vi.mocked(getCourseReport).mockReset()
    vi.mocked(fetchAll).mockReset().mockResolvedValue({ items: [], truncated: false })
  })

  it('muestra indicadores e información con respaldo de la API', async () => {
    vi.mocked(getCourseReport).mockResolvedValue({
      courseId: 2,
      snapshot: { snapshotId: 'snap-1', calculatedAt: '2026-11-20T12:00:00Z', dataQuality: 'complete' },
      periodStart: null,
      periodEnd: null,
      activeAlertCount: 1,
      metrics: { averageScore10: { value: 0, unit: 'score_0_10', status: 'available' } },
      findings: [{ text: 'El promedio requiere atención.', ruleCode: 'LOW_AVERAGE', observedValue: 0, threshold: 6, sourceIds: ['activity:2'] }],
    })
    renderPage()
    expect(await screen.findByText('El promedio requiere atención.')).toBeInTheDocument()
    expect(screen.getByText('activity:2', { exact: false })).toBeInTheDocument()
    expect(screen.getByText('Promedio académico')).toBeInTheDocument()
  })

  it('muestra un estado de error si analytics-service no responde', async () => {
    vi.mocked(getCourseReport).mockRejectedValue(new Error('API offline'))
    renderPage()
    expect(await screen.findByText('No se pudo cargar el informe')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Reintentar/i })).toBeInTheDocument()
  })

  it('muestra estado vacío si no hay hallazgos ni métricas', async () => {
    vi.mocked(getCourseReport).mockResolvedValue({
      courseId: 2,
      snapshot: { snapshotId: 'snap-2', calculatedAt: '2026-11-20T12:00:00Z', dataQuality: 'partial' },
      metrics: {},
      findings: [],
    })
    renderPage()
    expect(await screen.findByText('Sin hallazgos registrados')).toBeInTheDocument()
    expect(screen.getByText('Todavía no hay indicadores')).toBeInTheDocument()
  })
  it('numera a los estudiantes dentro del curso y no muestra el id de Moodle', async () => {
    vi.mocked(fetchAll).mockResolvedValue({ items: [{ id: 307, fullName: 'Zoe Zambrano' }, { id: 12, fullName: 'Ana Acosta' }], truncated: false } as never)
    vi.mocked(getCourseReport).mockResolvedValue({
      courseId: 2,
      snapshot: { snapshotId: 'snap-1', calculatedAt: '2026-11-20T12:00:00Z', dataQuality: 'complete' },
      periodStart: null, periodEnd: null, activeAlertCount: 1, metrics: {},
      findings: [{ text: 'Entrega baja.', ruleCode: 'LOW_SUBMISSION', studentId: 307, observedValue: 50, threshold: 80, sourceIds: [] }],
    } as never)
    renderPage()
    expect(await screen.findByText('N.º 2 · Zoe Zambrano')).toBeInTheDocument()
    expect(screen.queryByText(/307/)).not.toBeInTheDocument()
  })
})
