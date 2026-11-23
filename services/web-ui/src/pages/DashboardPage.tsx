import { useCallback, useEffect, useMemo, useState } from 'react'
import { ArrowLeft, ArrowRight, Bell, BookOpen, ClipboardList, RefreshCw, Search, TriangleAlert, UsersRound } from 'lucide-react'
import { Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Link, useLocation, useParams } from 'react-router-dom'
import { Avatar, Badge, Button, Card, CountUp, InView, MetricCard, Notice, SectionTitle, StateView } from '../components/UI'
import { ApiError, friendlyError } from '../services/api'
import { fetchAll, getAlerts, getAnalytics, getCourse, getGrades, getStudents, getSyncStatus, startSync } from '../services/edumonitor'
import type { AcademicAlert, Analytics, Course, Grade, Student, SyncStatus } from '../types/api'
import { dateLabel, gradeDistribution, numberLabel, statusText, submissionsDistribution } from '../utils/display'

const CHART_COLORS = ['#b42318','#c58a12','#525252']
const PAGE_SIZE = 8
export function DashboardPage() {
  const { id } = useParams()
  const courseId = Number(id)
  const hint = useLocation().state as { name?: string; code?: string } | null
  const [course, setCourse] = useState<Course | null>(null)
  const [analytics, setAnalytics] = useState<Analytics | null>(null)
  const [students, setStudents] = useState<Student[]>([])
  const [grades, setGrades] = useState<Grade[]>([])
  const [alerts, setAlerts] = useState<AcademicAlert[]>([])
  const [syncStatus, setSyncStatus] = useState<SyncStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [warnings, setWarnings] = useState<string[]>([])
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [syncing, setSyncing] = useState(false)
  const [success, setSuccess] = useState('')
  const load = useCallback(async () => {
    setLoading(true)
    if (!Number.isInteger(courseId) || courseId <= 0) { setError('Identificador de curso inválido.'); setLoading(false); return }
    setError(''); setWarnings([])
    const calls = await Promise.allSettled([
      getCourse(courseId), getAnalytics(courseId), fetchAll((p,s) => getStudents(courseId,p,s)),
      fetchAll((p,s)=>getGrades(courseId,p,s)), fetchAll((p,s)=>getAlerts(courseId,{page:p,pageSize:s})), getSyncStatus(courseId),
    ] as const)
    const [cr, an, st, gr, al, sy] = calls
    if (cr.status === 'fulfilled') setCourse(cr.value); else { setError(friendlyError(cr.reason)); setCourse(null) }
    if (an.status === 'fulfilled') setAnalytics(an.value); else setAnalytics(null)
    if (st.status === 'fulfilled') setStudents(st.value.items); else setStudents([])
    if (gr.status === 'fulfilled') setGrades(gr.value.items); else setGrades([])
    if (al.status === 'fulfilled') setAlerts(al.value.items); else setAlerts([])
    if (sy.status === 'fulfilled') setSyncStatus(sy.value); else setSyncStatus(null)
    const missing = [an, st, gr, al].filter(v => v.status === 'rejected')
    const missingMsgs = missing.map(v => v.status === 'rejected' ? friendlyError(v.reason) : '')
    if (st.status === 'fulfilled' && st.value.truncated) missingMsgs.push('La lista de estudiantes supera el límite de consulta de la interfaz.')
    if (gr.status === 'fulfilled' && gr.value.truncated) missingMsgs.push('La lista de calificaciones no está completa.')
    if (al.status === 'fulfilled' && al.value.truncated) missingMsgs.push('El listado de alertas no está completo.')
    setWarnings([...new Set(missingMsgs)])
    setLoading(false)
  }, [courseId])
  useEffect(() => {
    const timer = window.setTimeout(() => { void load() }, 0)
    return () => window.clearTimeout(timer)
  }, [load])
  useEffect(() => {
    if (syncStatus?.state !== 'running') return
    const timer = window.setInterval(async () => {
      try {
        const next = await getSyncStatus(courseId)
        setSyncStatus(next)
        if (next.state === 'succeeded') { setSuccess('Sincronización finalizada correctamente.'); void load() }
      } catch { /* conservamos el estado observado hasta el siguiente reintento */ }
    }, 3000)
    return () => window.clearInterval(timer)
  }, [syncStatus?.state, courseId, load])
  const sync = async () => {
    setSyncing(true); setSuccess('')
    try { await startSync(courseId); setSyncStatus(s => ({ ...s, state:'running' })) }
    catch (e) { if (e instanceof ApiError && e.code==='SYNC_IN_PROGRESS') setSyncStatus(s => ({ ...s, state:'running' })); else setError(friendlyError(e)) }
    finally { setSyncing(false) }
  }
  const filtered = useMemo(() => students.filter(s => s.fullName.toLowerCase().includes(search.toLowerCase()) || String(s.id).includes(search)), [students, search])
  const pages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE))
  const visible = filtered.slice((page-1)*PAGE_SIZE,page*PAGE_SIZE)
  const perStudent = useMemo(() => {
    const summary: Record<number, { zero: number; pending: number; missing: number }> = {}
    for (const g of grades) {
      summary[g.studentId] ||= {zero:0,pending:0,missing:0}
      if (g.status==='graded' && g.score===0) summary[g.studentId].zero++
      if (g.status==='pending_grading') summary[g.studentId].pending++
      if (g.status==='not_submitted') summary[g.studentId].missing++
    }
    return summary
  },[grades])
  const pie = useMemo(() => {
    const values = [0,0,0]
    for (const a of alerts) values[a.severity === 'critical' ? 0 : a.severity === 'warning' ? 1 : 2]++
    return [{name:'Críticas',cantidad:values[0]},{name:'Advertencias',cantidad:values[1]},{name:'Informativas',cantidad:values[2]}]
  }, [alerts])
  const focus = useMemo(() => {
    const names = new Map(students.map(st => [st.id, st.fullName]))
    const perStudentAlerts = new Map<number, number>()
    for (const a of alerts) if (a.studentId != null) perStudentAlerts.set(a.studentId, (perStudentAlerts.get(a.studentId) || 0) + 1)
    const top = [...perStudentAlerts.entries()].sort((x, y) => y[1] - x[1]).slice(0, 3).map(([sid, n]) => ({ id: sid, name: names.get(sid) || `Estudiante #${sid}`, n }))
    const pending = new Map<string, number>()
    for (const g of grades) if (g.status === 'pending_grading') pending.set(g.activityName, (pending.get(g.activityName) || 0) + 1)
    const worst = [...pending.entries()].sort((x, y) => y[1] - x[1])[0]
    return { top, activity: worst ? { name: worst[0], n: worst[1] } : null, pendingTotal: [...pending.values()].reduce((x, y) => x + y, 0) }
  }, [alerts, grades, students])
  if (loading) return <><Link className="back-link" to="/cursos" viewTransition><ArrowLeft size={17}/> Mis cursos</Link>{hint?.name && <section className="dash-head"><div><div className="eyebrow">{`Curso · ${hint.code || ''}`}</div><h1 style={{ viewTransitionName: `course-title-${courseId}` }}>{hint.name}</h1></div></section>}<StateView kind="loading" title="Preparando el dashboard" detail="Consultando indicadores, estudiantes, actividades y alertas…"/></>
  if (!course) return <><Link className="back-link" to="/cursos" viewTransition><ArrowLeft size={17}/> Volver a cursos</Link><StateView kind="error" detail={error || 'El curso no existe o no tienes permiso.'} onRetry={()=>{setLoading(true);void load()}}/></>
  return <><Link className="back-link" to="/cursos" viewTransition><ArrowLeft size={17}/> Mis cursos</Link><section className="dash-head"><div><div className="eyebrow">{`Curso · ${course.shortName}`}</div><h1 style={{ viewTransitionName: `course-title-${courseId}` }}>{course.fullName}</h1><p>Información de rendimiento académico del curso, basada en la fuente sincronizada.</p></div><div className="button-group"><Badge tone={syncStatus?.state==='succeeded'?'success':syncStatus?.state==='running'?'info':'neutral'}>{statusText(syncStatus?.state)}</Badge><Button variant="secondary" icon={<RefreshCw size={16}/>} onClick={()=>{setLoading(true);void load()}}>Actualizar</Button><Button icon={<RefreshCw size={16}/>} loading={syncing || syncStatus?.state==='running'} disabled={syncStatus?.state==='running'} onClick={()=>void sync()}>Sincronizar</Button><Link className="btn btn-secondary" to={`/cursos/${courseId}/informe`}><ClipboardList size={16}/> Ver informe</Link></div></section>
  {error && <Notice tone="danger">{error}</Notice>}{success && <Notice tone="success">{success}</Notice>}{warnings.map((w,i)=><Notice tone="warning" key={i}>{w}</Notice>)}
  {analytics?.snapshot.dataQuality !== 'complete' && <Notice tone="warning">{analytics ? 'Los indicadores contienen información parcial o no disponible. Los valores ausentes no se sustituyen por cero.' : 'No hay indicadores disponibles. Sincroniza el curso o comprueba analytics-service.'}</Notice>}
  <div className="info-row"><span><BookOpen size={16}/> {course.shortName}</span><span>Última sincronización exitosa: <strong>{dateLabel(syncStatus?.lastSuccessAt || course.lastSyncAt)}</strong></span><span>Indicadores calculados: <strong>{dateLabel(analytics?.snapshot.calculatedAt)}</strong></span></div>
  <section className="focus-row stagger" aria-label="Lo más importante"><Card className="focus-card"><div className="focus-head"><span className="focus-icon"><TriangleAlert size={18}/></span><div><h2>Requieren atención</h2><p>Estudiantes con más alertas activas</p></div></div>{focus.top.length ? <ul className="focus-list">{focus.top.map(t => <li key={t.id}><Link viewTransition to={`/cursos/${courseId}/estudiantes/${t.id}`}><Avatar name={t.name}/><span>{t.name}</span><Badge tone="warning">{t.n} {t.n === 1 ? 'alerta' : 'alertas'}</Badge><ArrowRight size={15}/></Link></li>)}</ul> : <p className="muted small">No hay alertas activas por estudiante.</p>}</Card><Card className="focus-card"><div className="focus-head"><span className="focus-icon"><ClipboardList size={18}/></span><div><h2>Por calificar</h2><p>Entregas que esperan nota</p></div></div><div className="focus-big"><CountUp value={focus.pendingTotal}/><small>{focus.pendingTotal === 1 ? 'entrega pendiente' : 'entregas pendientes'}</small></div><p className="muted small">{focus.activity ? <>La actividad con más pendientes es <strong>{focus.activity.name}</strong> ({focus.activity.n}).</> : 'No hay entregas pendientes de calificar.'}</p></Card><Card className="focus-card focus-dark"><div className="focus-head"><span className="focus-icon"><Bell size={18}/></span><div><h2>Alertas activas</h2><p>En todo el curso</p></div></div><div className="focus-big"><CountUp value={alerts.length}/><small>{alerts.length === 1 ? 'alerta' : 'alertas'}</small></div><Link viewTransition className="focus-link" to={`/alertas?curso=${courseId}`}>Ver alertas y evidencias <ArrowRight size={15}/></Link></Card></section>
  <div className="metrics-grid stagger"><Card className="metric-card"><span className="metric-title">Estudiantes</span><div className="metric-value">{typeof (course.studentCount ?? students.length) === 'number' && (course.studentCount ?? students.length) > 0 ? <CountUp value={course.studentCount ?? students.length}/> : 'No disponible'}</div><div className="metric-footer"><UsersRound size={16}/> Autorizados en el curso</div></Card><MetricCard title="Promedio del curso" metric={analytics?.averageScore10}/><MetricCard title="Tasa de entrega" metric={analytics?.submissionRate}/><MetricCard title="Tasa de calificación" metric={analytics?.gradingRate}/><MetricCard title="Finalización" metric={analytics?.completionRate}/><MetricCard title="Pendientes de calificar" metric={analytics?.pendingGradingRate}/></div>
  <div className="charts-grid stagger"><Card><SectionTitle title="Distribución de calificaciones" subtitle="Notas de actividades normalizadas a escala 0–10 (para visualizar, no recalcula el promedio)."/>{grades.some(g=>g.status==='graded') ? <InView className="chart"><ResponsiveContainer width="100%" height="100%"><BarChart data={gradeDistribution(grades)} margin={{left:-22,top:12,right:8,bottom:3}}><CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e7e5e4"/><XAxis dataKey="name" tick={{fontSize:11,fill:'#6b6b6b'}} axisLine={false} tickLine={false}/><YAxis allowDecimals={false} tick={{fontSize:11,fill:'#6b6b6b'}} axisLine={false} tickLine={false}/><Tooltip cursor={{fill:"rgba(0,0,0,0.05)"}} contentStyle={{borderRadius:12,border:"1px solid #e7e5e4",boxShadow:"0 10px 28px -14px rgba(0,0,0,.2)"}}/><Bar dataKey="cantidad" fill="#163a2c" radius={[6,6,0,0]} animationDuration={1100} animationEasing="ease-out"/></BarChart></ResponsiveContainer></InView> : <StateView kind="empty" title="Sin notas disponibles" detail="No se recibieron calificaciones válidas."/>}</Card>
    <Card><SectionTitle title="Estado de entregas" subtitle="Número de registros por estado de envío."/>{grades.length ? <InView className="chart"><ResponsiveContainer width="100%" height="100%"><BarChart data={submissionsDistribution(grades)} margin={{left:-22,top:12,right:8,bottom:3}}><CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e7e5e4"/><XAxis dataKey="name" tick={{fontSize:11,fill:'#6b6b6b'}} axisLine={false} tickLine={false}/><YAxis allowDecimals={false} tick={{fontSize:11,fill:'#6b6b6b'}} axisLine={false} tickLine={false}/><Tooltip cursor={{fill:"rgba(0,0,0,0.05)"}} contentStyle={{borderRadius:12,border:"1px solid #e7e5e4",boxShadow:"0 10px 28px -14px rgba(0,0,0,.2)"}}/><Bar dataKey="cantidad" fill="#a3a3a3" radius={[6,6,0,0]} animationDuration={1100} animationEasing="ease-out"/></BarChart></ResponsiveContainer></InView> : <StateView kind="empty" title="Sin entregas registradas"/>}</Card>
    <Card><SectionTitle title="Alertas por severidad" subtitle="Alertas activas devueltas por la API."/>{alerts.length ? <InView className="chart"><ResponsiveContainer width="100%" height="100%"><PieChart><Pie data={pie} dataKey="cantidad" nameKey="name" cx="50%" cy="46%" innerRadius={55} outerRadius={83} paddingAngle={3} animationDuration={1100} animationEasing="ease-out">{pie.map((x,i)=><Cell key={x.name} fill={CHART_COLORS[i]}/>)}</Pie><Tooltip cursor={{fill:"rgba(0,0,0,0.05)"}} contentStyle={{borderRadius:12,border:"1px solid #e7e5e4",boxShadow:"0 10px 28px -14px rgba(0,0,0,.2)"}}/><Legend verticalAlign="bottom" height={30}/></PieChart></ResponsiveContainer></InView> : <StateView kind="empty" title="Sin alertas activas" detail="No hay alertas activas o la información aún no está disponible."/>}</Card></div>
  <Card className="table-panel"><SectionTitle title="Estudiantes del curso" subtitle="Consulta su ficha para ver notas, entregas y finalización." right={<Link className="btn btn-secondary" to={`/alertas?curso=${courseId}`}><Bell size={16}/> Ver alertas <ArrowRight size={15}/></Link>}/><div className="table-toolbar"><div className="search-wrap"><Search size={18}/><input placeholder="Buscar estudiante por nombre o ID…" aria-label="Buscar estudiante" value={search} onChange={e=>{setSearch(e.target.value);setPage(1)}}/></div><span>{filtered.length} estudiantes</span></div>{!visible.length ? <StateView kind="empty" title="No se encontraron estudiantes"/> : <div className="table-scroll"><table><thead><tr><th>Estudiante</th><th>Calificaciones</th><th>Casos registrados</th><th></th></tr></thead><tbody>{visible.map(s => {const count=perStudent[s.id];return <tr key={s.id}><td><div className="person"><Avatar name={s.fullName}/><div><strong>{s.fullName}</strong><div className="muted tiny">ID #{s.id}</div></div></div></td><td>{count ? (count.zero+count.pending+count.missing===0?'Registros calificados':`${count.pending} pendiente(s)`) : 'Sin registros consultables'}</td><td><div className="tags">{count?.zero ? <Badge tone="warning">Nota cero: {count.zero}</Badge> : null}{count?.missing ? <Badge tone="neutral">Sin entrega: {count.missing}</Badge> : null}{count?.pending ? <Badge tone="info">Por calificar: {count.pending}</Badge> : null}{!count && <span className="muted tiny">No disponible</span>}</div></td><td><Link className="table-link" to={`/cursos/${courseId}/estudiantes/${s.id}`} viewTransition>Ver ficha <ArrowRight size={15}/></Link></td></tr>})}</tbody></table></div>}
  <div className="table-footer"><span>Página {page} de {pages} · {numberLabel(filtered.length,0)} estudiantes</span><div className="button-group"><Button variant="ghost" disabled={page<=1} onClick={()=>setPage(p=>p-1)}>Anterior</Button><Button variant="secondary" disabled={page>=pages} onClick={()=>setPage(p=>p+1)}>Siguiente</Button></div></div></Card>
  </>
}
