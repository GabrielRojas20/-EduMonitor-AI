import { useCallback, useEffect, useState } from 'react'
import { ArrowLeft, ArrowRight, Bell, BookOpen, MessageSquareText, UserRound } from 'lucide-react'
import { Link, useParams } from 'react-router-dom'
import { Badge, Card, MetricCard, Notice, PageHeader, SectionTitle, StateView } from '../components/UI'
import { friendlyError } from '../services/api'
import { fetchAll, getAlerts, getCourse, getStudentAnalytics, getStudentDetail } from '../services/edumonitor'
import type { AcademicAlert, Analytics, Course, StudentDetail } from '../types/api'
import { completionLabel, dateLabel, gradeLabel, ruleLabels, submissionLabel } from '../utils/display'

export function StudentPage() {
  const { id, sid } = useParams()
  const courseId = Number(id), studentId = Number(sid)
  const [course, setCourse] = useState<Course | null>(null)
  const [detail, setDetail] = useState<StudentDetail | null>(null)
  const [metrics, setMetrics] = useState<Analytics | null>(null)
  const [alerts, setAlerts] = useState<AcademicAlert[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [warnings, setWarnings] = useState<string[]>([])
  const load = useCallback(async () => {
    setLoading(true); setError(''); setWarnings([])
    const [c, d, m, a] = await Promise.allSettled([
      getCourse(courseId), getStudentDetail(courseId,studentId), getStudentAnalytics(courseId,studentId), fetchAll((p,s)=>getAlerts(courseId,{studentId,page:p,pageSize:s})),
    ] as const)
    if (c.status==='fulfilled') setCourse(c.value); else setCourse(null)
    if (d.status==='fulfilled') setDetail(d.value); else {setDetail(null);setError(friendlyError(d.reason))}
    if (m.status==='fulfilled') setMetrics(m.value); else setMetrics(null)
    if (a.status==='fulfilled') setAlerts(a.value.items); else setAlerts([])
    const others = [m,a].filter(r=>r.status==='rejected').map(r=>r.status==='rejected'?friendlyError(r.reason):'')
    if (a.status==='fulfilled' && a.value.truncated) others.push('La lista de alertas de este estudiante está incompleta.')
    setWarnings(others);setLoading(false)
  },[courseId,studentId])
  useEffect(()=>{setCourse(null);setDetail(null);setMetrics(null);setAlerts([]);void load()},[load])
  if (loading) return <StateView kind="loading" title="Cargando ficha individual"/>
  if (!detail) return <><Link className="back-link" to={`/cursos/${courseId}`}><ArrowLeft size={17}/> Volver al curso</Link><StateView kind="error" detail={error || 'No hay datos para este estudiante.'} onRetry={()=>void load()}/></>
  const {student,grades,activities}=detail
  const progress = new Map(activities.map(item=>[item.activityId,item.completionState]))
  return <><Link className="back-link" to={`/cursos/${courseId}`}><ArrowLeft size={17}/> Volver al dashboard</Link><PageHeader eyebrow={`FICHA INDIVIDUAL · ESTUDIANTE #${student.id}`} title={student.fullName} subtitle={`Curso: ${course?.fullName || `#${courseId}`}`} action={<div className="button-group"><Link className="btn btn-secondary" to={`/alertas?curso=${courseId}&estudiante=${studentId}`}><Bell size={16}/> Ver alertas</Link><Link className="btn btn-primary" to={`/chat?curso=${courseId}`}><MessageSquareText size={16}/> Consultar al agente</Link></div>}/>
  {warnings.map((w,i)=><Notice key={i} tone="warning">{w}</Notice>)}{metrics && metrics.snapshot.dataQuality!=='complete' && <Notice tone="warning">Datos parciales: algunas actividades no tienen información de finalización. La ausencia de información no se interpreta como cero.</Notice>}{!metrics && <Notice tone="warning">No fue posible consultar los indicadores individuales; las actividades se muestran con la información disponible del gateway.</Notice>}
  <Card className="student-info"><span className="student-avatar"><UserRound size={26}/></span><div><h2>{student.fullName}</h2><p><BookOpen size={15}/> {course?.fullName || `Curso #${courseId}`}</p></div><div className="student-info-date">Indicadores calculados<br/><strong>{dateLabel(metrics?.snapshot.calculatedAt)}</strong></div></Card>
  <div className="metrics-grid student-metrics"><MetricCard title="Promedio individual" metric={metrics?.averageScore10}/><MetricCard title="Tasa de entrega" metric={metrics?.submissionRate}/><MetricCard title="Finalización" metric={metrics?.completionRate}/><MetricCard title="Por calificar" metric={metrics?.pendingGradingRate}/></div>
  <Card className="table-panel"><SectionTitle title="Actividades y calificaciones" subtitle="Escalas originales, estado de entrega y progreso según Moodle."/>{grades.length ? <div className="table-scroll"><table><thead><tr><th>Actividad</th><th>Nota</th><th>Entrega</th><th>Finalización</th></tr></thead><tbody>{grades.map((g,i)=>{const completion=progress.get(g.activityId) || 'not_available';return <tr key={`${g.activityId}-${i}`}><td><strong>{g.activityName}</strong><div className="muted tiny">Actividad #{g.activityId}</div></td><td><strong>{gradeLabel(g)}</strong>{g.status==='graded' && g.score===0 && <div><Badge tone="warning">Nota cero válida</Badge></div>}{g.status==='pending_grading' && <div><Badge tone="info">Sin nota todavía</Badge></div>}</td><td>{submissionLabel(g)}</td><td><Badge tone={completion==='not_available'?'neutral':completion==='passed'||completion==='complete'?'success':'warning'}>{completionLabel(completion)}</Badge></td></tr>})}</tbody></table></div> : <StateView kind="empty" title="Sin actividades registradas" detail="No se recibieron notas o entregas para este estudiante."/>}</Card>
  <Card><SectionTitle title="Evidencia de alertas asociadas" subtitle="Las explicaciones y umbrales provienen del servicio de analítica." right={<Link className="table-link" to={`/alertas?curso=${courseId}&estudiante=${studentId}`}>Ver todas las alertas <ArrowRight size={15}/></Link>}/>{alerts.length ? <div className="evidence-list">{alerts.map(a=><div className="evidence-item" key={a.alertId}><div className="evidence-item-head"><strong>{ruleLabels[a.ruleCode] || a.ruleCode}</strong><Badge tone={a.severity==='critical'?'danger':a.severity==='warning'?'warning':'info'}>{a.severity}</Badge></div>{a.evidence.map((ev,j)=><div className="evidence-text" key={j}>{ev.explanation}<div className="muted tiny">Origen: {ev.sourceIds?.join(', ') || 'Sin identificadores de fuente'}</div></div>)}</div>)}</div> : <StateView kind="empty" title="Sin alertas activas para este estudiante" detail="Esto no implica que los datos estén completos; consulta el estado de sincronización del curso."/>}</Card>
  </>
}
