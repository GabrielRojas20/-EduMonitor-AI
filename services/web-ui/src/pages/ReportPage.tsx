import { useCallback, useEffect, useState } from 'react'
import { ArrowLeft, CalendarDays, ClipboardList, FileText, RefreshCw, ShieldCheck } from 'lucide-react'
import { Link, useParams } from 'react-router-dom'
import { Badge, Button, Card, MetricCard, Notice, PageHeader, SectionTitle, StateView } from '../components/UI'
import { friendlyError } from '../services/api'
import { fetchAll, getCourse, getCourseReport, getStudents } from '../services/edumonitor'
import type { Course, CourseReportData, Metric } from '../types/api'
import { dateLabel, numberLabel, numberStudents, ruleLabels, studentLabel } from '../utils/display'
import type { StudentNumbering } from '../utils/display'

const METRICS: Record<string, string> = {
  averageScore10: 'Promedio académico',
  submissionRate: 'Tasa de entrega',
  gradingRate: 'Tasa de calificación',
  completionRate: 'Finalización',
  pendingGradingRate: 'Pendientes de calificar',
}

function metricTitle(key: string): string {
  return METRICS[key] || key
}

function observed(value: number | null | undefined): string {
  return value == null ? 'No disponible' : numberLabel(value, 2)
}

export function ReportPage() {
  const { id } = useParams()
  const courseId = Number(id)
  const [course, setCourse] = useState<Course | null>(null)
  const [report, setReport] = useState<CourseReportData | null>(null)
  const [numbering, setNumbering] = useState<StudentNumbering>(new Map())
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    if (!Number.isInteger(courseId) || courseId <= 0) {
      setError('El identificador del curso es inválido.')
      setLoading(false)
      return
    }
    try {
      const [nextCourse, nextReport, students] = await Promise.all([
        getCourse(courseId), getCourseReport(courseId),
        fetchAll((page, size) => getStudents(courseId, page, size)).catch(() => null), // sin la lista se muestran los ids
      ])
      setCourse(nextCourse)
      setReport(nextReport)
      // Cada estudiante se numera dentro de su curso (1 a N); el id de Moodle no sirve para eso.
      setNumbering(students ? numberStudents(students.items) : new Map())
    } catch (e) {
      setCourse(null)
      setReport(null)
      setError(friendlyError(e))
    } finally {
      setLoading(false)
    }
  }, [courseId])

  useEffect(() => {
    const timer = window.setTimeout(() => { void load() }, 0)
    return () => window.clearTimeout(timer)
  }, [load])

  if (loading) return <StateView kind="loading" title="Preparando informe" detail="Consultando métricas y evidencias del servicio de analítica…" />
  if (!report || !course) return <>
    <Link className="back-link" to="/cursos"><ArrowLeft size={17} /> Volver a mis cursos</Link>
    <StateView kind="error" title="No se pudo cargar el informe" detail={error || 'El informe de este curso no está disponible.'} onRetry={() => void load()} />
  </>

  const entries = Object.entries(report.metrics || {}) as [string, Metric][]
  const findings = report.findings || []
  const hasPartial = report.snapshot?.dataQuality !== 'complete'

  return <div className="academic-report">
    <Link className="back-link" to={`/cursos/${courseId}`}><ArrowLeft size={17} /> Volver al dashboard</Link>
    <PageHeader
      eyebrow={`INFORME ACADÉMICO · ${course.shortName}`}
      title="Informe del curso"
      subtitle={course.fullName}
      action={<Button variant="secondary" icon={<RefreshCw size={16} />} onClick={() => void load()}>Actualizar informe</Button>}
    />
    {hasPartial && <Notice tone="warning">Los indicadores incluyen datos parciales o no disponibles. No se sustituyen por cero.</Notice>}
    <Card className="report-meta">
      <div><CalendarDays size={19} /><span>Primera observación</span><strong>{dateLabel(report.periodStart)}</strong></div>
      <div><CalendarDays size={19} /><span>Última observación</span><strong>{dateLabel(report.periodEnd)}</strong></div>
      <div><ShieldCheck size={19} /><span>Corte de indicadores</span><strong>{dateLabel(report.snapshot?.calculatedAt)}</strong></div>
      <div><ClipboardList size={19} /><span>Alertas activas</span><strong>{typeof report.activeAlertCount === 'number' ? numberLabel(report.activeAlertCount, 0) : 'No disponible'}</strong></div>
    </Card>
    <section aria-labelledby="report-metrics-title" className="report-section">
      <div className="report-section-heading"><h2 id="report-metrics-title">Indicadores del curso</h2><p>Calculados por analytics-service sobre los datos sincronizados.</p></div>
      {entries.length ? <div className="metrics-grid stagger">{entries.map(([key, metric]) => <MetricCard key={key} title={metricTitle(key)} metric={metric} />)}</div>
        : <StateView kind="empty" title="Todavía no hay indicadores" detail="Sincroniza el curso y vuelve a consultar el informe." />}
    </section>
    <section aria-label="Hallazgos y evidencia" className="report-section">
      <Card className="report-findings">
        <SectionTitle title="Hallazgos y evidencia" subtitle="Cada hallazgo procede del informe calculado; no añadimos conclusiones que no estén en la fuente." right={<Badge tone="neutral">{findings.length} hallazgos</Badge>} />
        {findings.length ? <ol className="report-findings-list">{findings.map((finding, index) => <li key={`${finding.alertId || finding.metric || 'hallazgo'}-${index}`}>
          <div className="report-finding-icon"><FileText size={19} /></div>
          <div className="report-finding-content">
            <div className="report-finding-title"><strong>{finding.ruleCode ? ruleLabels[finding.ruleCode] || finding.ruleCode : finding.metric ? metricTitle(finding.metric) : `Hallazgo ${index + 1}`}</strong>{finding.studentId != null && <Badge tone="info">{studentLabel(numbering, finding.studentId)}</Badge>}</div>
            <p>{finding.text}</p>
            {(finding.observedValue != null || finding.threshold != null) && <div className="report-evidence"><span>Valor observado: <strong>{observed(finding.observedValue)}</strong></span><span>Umbral: <strong>{observed(finding.threshold)}</strong></span></div>}
            {finding.sourceIds?.length ? <div className="report-sources">Fuentes: {finding.sourceIds.join(' · ')}</div> : <div className="report-sources">Identificadores de fuente no disponibles</div>}
            {finding.alertId && <Link className="table-link" to={`/alertas?curso=${courseId}`}>Consultar alerta y evidencia</Link>}
          </div>
        </li>)}</ol> : <StateView kind="empty" title="Sin hallazgos registrados" detail="El servicio no devolvió hallazgos para este corte de datos. Comprueba el estado de los datos si esperabas alguno." />}
      </Card>
    </section>
    <div className="report-note"><ShieldCheck size={17} /> Informe de consulta académica basado en el contrato de analytics-service. Las recomendaciones pedagógicas del agente se consultan en el chat.</div>
  </div>
}
