import { useCallback, useEffect, useMemo, useState } from 'react'
import type { CSSProperties } from 'react'
import { ArrowRight, BellRing, ChevronRight, Search } from 'lucide-react'
import { Link, useSearchParams } from 'react-router-dom'
import { Badge, Card, Notice, PageHeader, Segmented, SectionTitle, StateView } from '../components/UI'
import { friendlyError } from '../services/api'
import { fetchAll, getAlerts, getStudents, listCourses } from '../services/edumonitor'
import type { AcademicAlert, AlertSeverity, AlertStatus, Course } from '../types/api'
import { dateLabel, numberLabel, numberStudents, ruleLabels, severityLabels, studentLabel } from '../utils/display'
import type { StudentNumbering } from '../utils/display'

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
  const [numbering,setNumbering] = useState<StudentNumbering>(new Map())
  // Cada estudiante se numera dentro de su curso (1 a N): el id de Moodle es global y no sirve para contarlos.
  const who = (id?: number | null) => id==null ? 'Alerta de curso' : studentLabel(numbering,id)
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
      try { const all = await fetchAll((page,size)=>getStudents(Number(courseId),page,size)); setNumbering(numberStudents(all.items)) } catch { setNumbering(new Map()) }
    } catch(e){setAlerts([]);setError(friendlyError(e))} finally {setLoading(false)}
  },[courseId,severity,status,studentId])
  useEffect(() => {
    const timer = window.setTimeout(() => { void load() }, 0)
    return () => window.clearTimeout(timer)
  }, [load])
  const filtered = useMemo(()=>alerts.filter(a=>`${a.ruleCode} ${a.alertId} ${a.studentId ?? ''} ${a.studentId!=null?numbering.get(a.studentId)?.name||'':''} ${a.evidence.map(e=>e.explanation).join(' ')}`.toLowerCase().includes(search.toLowerCase())),[alerts,search,numbering])
  const chosen = filtered.find(a=>a.alertId===selected) || filtered[0]
  const changeCourse = (v:string) => {setCourseId(v); const next=new URLSearchParams(params);next.set('curso',v);next.delete('estudiante');setParams(next)}
  return <><PageHeader eyebrow="MONITOREO ACADÉMICO" title="Alertas y evidencias" subtitle="Identifica situaciones relevantes y consulta las evidencias que justifican cada alerta." action={<Badge tone="info"><BellRing size={15}/> {filtered.length} resultados</Badge>}/>
    {partial&&<Notice tone="warning">La lista de alertas supera el límite de consulta. Los resultados visibles pueden ser parciales.</Notice>}{studentId&&<Notice>Filtro activo: {who(studentId)}. <Link className="inline-link" to={`/alertas?curso=${courseId}`}>Mostrar todo el curso</Link></Notice>}
    <Card className="filter-panel"><div className="filter-group"><span>Curso</span><select aria-label="Curso" value={courseId} onChange={e=>changeCourse(e.target.value)}>{!courses.length&&<option value="">Cargando cursos…</option>}{courses.map(c=><option key={c.id} value={c.id}>{c.fullName}</option>)}</select></div><div className="filter-group"><span>Severidad</span><Segmented label="Severidad" value={severity} onChange={setSeverity} options={[{value:'all',label:'Todas'},{value:'critical',label:'Críticas'},{value:'warning',label:'Advertencias'},{value:'info',label:'Informativas'}]}/></div><div className="filter-group"><span>Estado</span><Segmented label="Estado" value={status} onChange={setStatus} options={[{value:'active',label:'Activas'},{value:'resolved',label:'Resueltas'},{value:'all',label:'Todas'}]}/></div><div className="search-wrap"><Search size={17}/><input aria-label="Buscar en alertas" placeholder="Regla, estudiante o explicación" value={search} onChange={e=>setSearch(e.target.value)}/></div></Card>
    {error&&<Notice tone="danger">{error}</Notice>}
    {loading?<StateView kind="loading" title="Consultando alertas"/>:error?<StateView kind="error" detail={error} onRetry={()=>void load()}/>:!filtered.length?<StateView kind="empty" title="No hay alertas para esta consulta" detail="Prueba otro curso, estado o severidad. El mock solo dispone de alertas activas."/>:<div className="alerts-layout"><Card className="alert-list"><SectionTitle title="Listado de alertas" subtitle={`${filtered.length} coincidencias`}/>{filtered.map((a,i)=><button type="button" key={a.alertId} style={{'--i': i} as CSSProperties} data-sev={a.severity} className={`alert-row ${chosen?.alertId===a.alertId?'selected':''}`} onClick={()=>setSelected(a.alertId)}><div className="alert-row-title"><strong>{ruleLabels[a.ruleCode]||a.ruleCode}</strong><Badge tone={a.severity==='critical'?'danger':a.severity==='warning'?'warning':'info'}>{severityLabels[a.severity]}</Badge></div><span>{who(a.studentId)}</span><div className="alert-row-meta">{dateLabel(a.detectedAt)} · {a.status==='active'?'Activa':'Resuelta'}</div><ChevronRight className="alert-chevron" size={18}/></button>)}</Card><Card className="alert-details"><SectionTitle title="Detalle y evidencia" subtitle="Información verificable recibida del servicio"/>{chosen&&<div className="detail-body" key={chosen.alertId}><div className="detail-heading"><div className="detail-icon"><BellRing size={25}/></div><div><span className="eyebrow">{chosen.ruleCode}</span><h3>{ruleLabels[chosen.ruleCode]||chosen.ruleCode}</h3></div></div><div className="tags"><Badge tone={chosen.severity==='critical'?'danger':chosen.severity==='warning'?'warning':'info'}>{severityLabels[chosen.severity]}</Badge><Badge tone={chosen.status==='active'?'warning':'success'}>{chosen.status==='active'?'Activa':'Resuelta'}</Badge></div><div className="detail-grid"><div><span>Estudiante</span><strong>{chosen.studentId==null?'Alerta general del curso':numbering.get(chosen.studentId)?.name||'Estudiante de otro curso'}</strong>{chosen.studentId!=null&&numbering.get(chosen.studentId)&&<div className="muted tiny">N.º {numbering.get(chosen.studentId)?.n} de {numbering.get(chosen.studentId)?.total} en el curso</div>}</div><div><span>Detectada</span><strong>{dateLabel(chosen.detectedAt)}</strong></div><div><span>Resuelta</span><strong>{dateLabel(chosen.resolvedAt)}</strong></div><div><span>Curso</span><strong>{courses.find(c=>c.id===chosen.courseId)?.fullName||`#${chosen.courseId}`}</strong></div></div><h4>Evidencia verificable</h4>{chosen.evidence.map((ev,i)=><div className="evidence-item" key={i}><strong>{ev.metric}</strong><p>{ev.explanation}</p><div className="evidence-stats"><span>Valor observado: <strong>{ev.observedValue===null||ev.observedValue===undefined?'No disponible':numberLabel(ev.observedValue,2)}</strong></span><span>Umbral: <strong>{ev.threshold===null||ev.threshold===undefined?'No disponible':numberLabel(ev.threshold,2)}</strong></span></div>{ev.sourceIds?.length?<div className="source-list">Fuentes: {ev.sourceIds.join(' · ')}</div>:<div className="muted tiny">Sin identificadores de fuente</div>}</div>)}{chosen.studentId!=null&&<Link viewTransition className="btn btn-primary" to={`/cursos/${chosen.courseId}/estudiantes/${chosen.studentId}`}>Abrir ficha individual <ArrowRight size={16}/></Link>}<div className="micro-note">La severidad y los umbrales son definidos por analytics-service, no por la interfaz.</div></div>}</Card></div>}
  </>
}
