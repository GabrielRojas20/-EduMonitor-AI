import { describe, expect, it } from 'vitest'
import type { Grade, Metric } from '../types/api'
import { completionLabel, gradeDistribution, gradeLabel, metricLabel, submissionsDistribution } from './display'

const grade = (changes: Partial<Grade>): Grade => ({
  studentId: 1,
  activityId: 2,
  activityName: 'Actividad de prueba',
  status: 'graded',
  submissionStatus: 'submitted',
  score: 0,
  maxScore: 10,
  ...changes,
})

describe('Estados de calificaciones y actividades', () => {
  it('respeta la nota cero calificada', () => {
    expect(gradeLabel(grade({ score: 0 }))).toBe('0 / 10')
  })
  it('no interpreta una entrega sin calificar como cero', () => {
    expect(gradeLabel(grade({ status: 'pending_grading', score: null }))).toBe('Pendiente de calificar')
  })
  it('distingue actividad sin entrega y borrador sin enviar', () => {
    expect(gradeLabel(grade({ status: 'not_submitted', submissionStatus: 'none', score: null }))).toBe('Sin entrega')
    expect(gradeLabel(grade({ status: 'not_submitted', submissionStatus: 'draft', score: null }))).toBe('Borrador sin enviar')
  })
  it('mantiene el estado de finalización no disponible', () => {
    expect(completionLabel('not_available')).toBe('Finalización no disponible')
  })
  it('no agrupa un registro pendiente entre calificaciones válidas', () => {
    const bins = gradeDistribution([grade({ score: 0 }), grade({ status: 'pending_grading', score: null })])
    expect(bins.reduce((sum, bin) => sum + bin.cantidad, 0)).toBe(1)
    expect(bins[0].cantidad).toBe(1)
  })
  it('distribuye entregas, borradores y ausencias por separado', () => {
    const bins = submissionsDistribution([
      grade({ submissionStatus: 'submitted' }),
      grade({ submissionStatus: 'draft' }),
      grade({ submissionStatus: 'none' }),
    ])
    expect(bins.map(x => x.cantidad)).toEqual([1, 1, 1])
  })
})

describe('Indicadores ausentes', () => {
  it('muestra dato no disponible cuando no hay valor', () => {
    const metric: Metric = { value: null, unit: 'score_0_10', status: 'unavailable' }
    expect(metricLabel(metric)).toBe('No disponible')
    expect(metricLabel(undefined)).toBe('No disponible')
  })
  it('presenta un cero disponible como cero real', () => {
    const metric: Metric = { value: 0, unit: 'percent', status: 'available' }
    expect(metricLabel(metric)).toContain('0')
    expect(metricLabel(metric)).not.toBe('No disponible')
  })
})
