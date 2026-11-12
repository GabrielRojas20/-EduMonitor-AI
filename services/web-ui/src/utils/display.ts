import type { CompletionState, Grade, Metric, SyncState } from '../types/api'

export function dateLabel(value?: string | null): string {
  if (!value) return 'Sin fecha disponible'
  const d = new Date(value)
  return Number.isNaN(d.getTime()) ? 'Fecha no disponible' : d.toLocaleString('es-EC', { dateStyle: 'medium', timeStyle: 'short' })
}
export function numberLabel(n: number, digits = 1) { return n.toLocaleString('es-EC', { maximumFractionDigits: digits }) }
export function metricLabel(metric?: Metric): string {
  if (!metric || metric.status === 'unavailable' || metric.value === null) return 'No disponible'
  if (metric.unit === 'percent') return `${numberLabel(metric.value)} %`
  if (metric.unit === 'score_0_10') return `${numberLabel(metric.value, 2)} / 10`
  return numberLabel(metric.value, 0)
}
export function statusText(status?: SyncState) {
  return ({ never: 'Nunca sincronizado', running: 'Sincronizando', succeeded: 'Actualizado', failed: 'Fallida' } as Record<string, string>)[status || ''] || 'Estado no disponible'
}
export function gradeLabel(grade: Grade): string {
  if (grade.status === 'graded' && grade.score !== null && grade.score !== undefined) return `${numberLabel(grade.score, 2)} / ${numberLabel(grade.maxScore, 2)}`
  if (grade.status === 'pending_grading') return 'Pendiente de calificar'
  if (grade.submissionStatus === 'draft') return 'Borrador sin enviar'
  return 'Sin entrega'
}
export function submissionLabel(grade: Grade) {
  return ({ submitted: 'Entregada', draft: 'Borrador sin enviar', none: 'Sin entrega' } as const)[grade.submissionStatus]
}
export function completionLabel(state: CompletionState) {
  return ({ complete: 'Completada', incomplete: 'Incompleta', passed: 'Completada y aprobada', failed: 'Completada sin aprobar', not_available: 'Finalización no disponible' } as const)[state]
}
export const severityLabels = { info: 'Informativa', warning: 'Advertencia', critical: 'Crítica' } as const
export const ruleLabels: Record<string,string> = { LOW_AVERAGE: 'Promedio bajo', LOW_SUBMISSION: 'Entregas insuficientes', PENDING_GRADING: 'Calificaciones pendientes', LOW_COMPLETION: 'Finalización baja', NO_DATA: 'Datos no disponibles' }
export function gradeDistribution(grades: Grade[]) {
  const bins = [0, 0, 0, 0, 0]
  for (const g of grades) {
    if (g.status !== 'graded' || g.score === null || g.score === undefined || g.maxScore <= 0) continue
    const n = Math.min(10, Math.max(0, g.score / g.maxScore * 10))
    bins[Math.min(4, Math.floor(n / 2))]++
  }
  return ['0–1,9','2–3,9','4–5,9','6–7,9','8–10'].map((name, i) => ({ name, cantidad: bins[i] }))
}
export function submissionsDistribution(grades: Grade[]) {
  const result = [
    { name: 'Entregadas', cantidad: 0 },
    { name: 'Borradores', cantidad: 0 },
    { name: 'Sin entrega', cantidad: 0 },
  ]
  for (const g of grades) {
    result[g.submissionStatus === 'submitted' ? 0 : g.submissionStatus === 'draft' ? 1 : 2].cantidad++
  }
  return result
}
