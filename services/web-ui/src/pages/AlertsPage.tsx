import { useCallback, useEffect, useMemo, useState } from 'react'
import { ArrowRight, BellRing, ChevronRight, Filter, Search } from 'lucide-react'
import { Link, useSearchParams } from 'react-router-dom'
import { Badge, Card, Notice, PageHeader, SectionTitle, StateView } from '../components/UI'
import { friendlyError } from '../services/api'
import { fetchAll, getAlerts, listCourses } from '../services/edumonitor'
import type { AcademicAlert, AlertSeverity, AlertStatus, Course } from '../types/api'
import { dateLabel, numberLabel, ruleLabels, severityLabels } from '../utils/display'

export function AlertsPage() {
  const [params,setParams] = useSearchParams()
  const [courses,setCourses] = useState<Course[]>([])
  const [courseId,setCourseId] = useState(params.get('curso') || '')
  const [severity,setSeverity] = useState<'all'|AlertSeverity>('all')
  const [status,setStatus] = useState<'all'|AlertStatus>('active')
  const [search,setSearch] = useState('')
  const [alerts,setAlerts] = useState<AcademicAlert[]>([])
  const [selected,setSelected] = useState<string | null>(null)
  const [loading,setLoading] = useState(true)
  const [error,setError] = useState('')
  const [partial,setPartial] = useState(false)
  const studentId = Number(params.get('estudiante')) || undefined
  useEffect(()=>{listCourses().then(cs=>{setCourses(cs);setCourseId(old=>old||String(cs[0]?.id || ''))}).catch(e=>setError(friendlyError(e)))},[])
  const load = useCallback(async () => {
    if (!courseId) {setLoading(false);return}
    setLoading(true);setError('');setPartial(false);setSelected(null)
    try {
      const statuses: AlertStatus[] = status==='all'?['active','resolved']:[status]
      const results = await Promise.all(statuses.map(state=>fetchAll((page,size)=>getAlerts(Number(courseId),{status:state,severity:severity==='all'?undefined:severity,studentId,page,pageSize:size}))))
      const data = results.flatMap(r=>r.items)
      setAlerts(data)
      setPartial(results.some(r=>r.truncated))
    } catch(e){setAlerts([]);setError(friendlyError(e))} finally {setLoading(false)}
  },[courseId,severity,status,studentId])
  useEffect(()=>{void load()},[load])
  const filtered = useMemo(()=>alerts.filter(a=>`${a.ruleCode} ${a.alertId} ${a.studentId || ''} ${a.evidence.map(e=>e.explanation).join(' ')}`.toLowerCase().includes(search.toLowerCase())),[alerts,search])
  const chosen = filtered.find(a=>a.alertId===selected) || filtered[0]
  const changeCourse = (v:string) => {setCourseId(v); const next=new URLSearchParams(params);next.set('curso',v);next.delete('estudiante');setParams(next)}
  return <><PageHeader eyebrow="MONITOREO ACADÉMICO" title="Alertas y evidencias" subtitle="Identifica situaciones relevantes y consulta las evidencias que justifican cada alerta." action={<Badge tone="info"><BellRing size={15}/> {filtered.length} resultados</Badge>}/>
    {partial&&<Notice tone="warning">La lista de alertas supera el límite de consulta. Los resultados visibles pueden ser parciales.</Notice>}{studentId&&<Notice>Filtro activo: estudiante #{studentId}. <Link className="inline-link" to={`/alertas?curso=${courseId}`}>Mostrar todo el curso</Link></Notice>}
    <Card className="filter-panel"><div className="filter-heading"><Filter size={18}/> Filtros de consulta</div><div className="alert-filters"><label>Curso<select value={courseId} onChange={e=>changeCourse(e.target.value)}>{!courses.length&&<option value="">Cargando cursos…</option>}{courses.map(c=><option key={c.id} value={c.id}>{c.fullName}</option>)}</select></label><label>Severidad<select value={severity} onChange={e=>setSeverity(e.target.value as 'all'|AlertSeverity)}><option value="all">Todas las severidades</option><option value="info">Informativa</option><option value="warning">Advertencia</option><option value="critical">Crítica</option></select></label><label>Estado<select value={status} onChange={e=>setStatus(e.target.value as 'all'|AlertStatus)}><option value="active">Activas</option><option value="resolved">Resueltas</option><option value="all">Todas</option></select></label><label className="grow">Buscar<div className="search-wrap"><Search size={17}/><input aria-label="Buscar en alertas" placeholder="Regla, estudiante o explicación" value={search} onChange={e=>setSearch(e.target.value)}/></div></label></div></Card>
    {error&&<Notice tone="danger">{error}</Notice>}
    {loading?<StateView kind="loading" title="Consultando alertas"/>:error?<StateView kind="error" detail={error} onRetry={()=>void load()}/>:!filtered.length?<StateView kind="empty" title="No hay alertas para esta consulta" detail="Prueba otro curso, estado o severidad. El mock solo dispone de alertas activas."/>:<div className="alerts-layout"><Card className="alert-list"><SectionTitle title="Listado de alertas" subtitle={`${filtered.length} coincidencias`}/>{filtered.map(a=><button type="button" key={a.alertId} className={`alert-row ${chosen?.alertId===a.alertId?'selected':''}`} onClick={()=>setSelected(a.alertId)}><div className="alert-row-title"><strong>{ruleLabels[a.ruleCode]||a.ruleCode}</strong><Badge tone={a.severity==='critical'?'danger':a.severity==='warning'?'warning':'info'}>{severityLabels[a.severity]}</Badge></div><span>{a.studentId===null||a.studentId===undefined?'Alerta de curso':`Estudiante #${a.studentId}`}</span><div className="alert-row-meta">{dateLabel(a.detectedAt)} · {a.status==='active'?'Activa':'Resuelta'}</div><ChevronRight className="alert-chevron" size={18}/></button>)}</Card><Card className="alert-details"><SectionTitle title="Detalle y evidencia" subtitle="Información verificable recibida del servicio"/>{chosen&&<><div className="detail-heading"><div className="detail-icon"><BellRing size={25}/></div><div><span className="eyebrow">{chosen.ruleCode}</span><h3>{ruleLabels[chosen.ruleCode]||chosen.ruleCode}</h3></div></div><div className="tags"><Badge tone={chosen.severity==='critical'?'danger':chosen.severity==='warning'?'warning':'info'}>{severityLabels[chosen.severity]}</Badge><Badge tone={chosen.status==='active'?'warning':'success'}>{chosen.status==='active'?'Activa':'Resuelta'}</Badge></div><div className="detail-grid"><div><span>Estudiante</span><strong>{chosen.studentId??'Alerta general del curso'}</strong></div><div><span>Detectada</span><strong>{dateLabel(chosen.detectedAt)}</strong></div><div><span>Resuelta</span><strong>{dateLabel(chosen.resolvedAt)}</strong></div><div><span>Curso</span><strong>#{chosen.courseId}</strong></div></div><h4>Evidencia verificable</h4>{chosen.evidence.map((ev,i)=><div className="evidence-item" key={i}><strong>{ev.metric}</strong><p>{ev.explanation}</p><div className="evidence-stats"><span>Valor observado: <strong>{ev.observedValue===null||ev.observedValue===undefined?'No disponible':numberLabel(ev.observedValue,2)}</strong></span><span>Umbral: <strong>{ev.threshold===null||ev.threshold===undefined?'No disponible':numberLabel(ev.threshold,2)}</strong></span></div>{ev.sourceIds?.length?<div className="source-list">Fuentes: {ev.sourceIds.join(' · ')}</div>:<div className="muted tiny">Sin identificadores de fuente</div>}</div>)}{chosen.studentId!=null&&<Link className="btn btn-primary" to={`/cursos/${chosen.courseId}/estudiantes/${chosen.studentId}`}>Abrir ficha individual <ArrowRight size={16}/></Link>}<div className="micro-note">La severidad y los umbrales son definidos por analytics-service, no por la interfaz.</div></>}</Card></div>}
  </>
}
