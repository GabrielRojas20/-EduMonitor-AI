import { useCallback, useEffect, useMemo, useState } from 'react'
import { ArrowRight, Bell, CalendarDays, MessageSquareText, RefreshCw, Search, UsersRound } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { Button, Card, Badge, CountUp, Notice, PageHeader, Segmented, StateView } from '../components/UI'
import { ApiError, friendlyError } from '../services/api'
import { getAlerts, getAnalytics, getSyncStatus, listCourses, startSync } from '../services/edumonitor'
import type { AcademicAlert, Course, Metric, SyncStatus } from '../types/api'
import { dateLabel, ruleLabels, statusText } from '../utils/display'

const MAX_SUMMARY = 6
const QUICK = ['¿Qué falta por calificar?', '¿Qué alertas tiene este curso?', '¿Cómo va el curso y qué me recomiendas?']
const FILTERS = [
  { value: 'all', label: 'Todos' },
  { value: 'succeeded', label: 'Actualizados' },
  { value: 'running', label: 'Sincronizando' },
  { value: 'never', label: 'Sin sincronizar' },
  { value: 'failed', label: 'Fallidos' },
]

export function CoursesPage() {
  const { user } = useAuth()
  const [courses, setCourses] = useState<Course[]>([])
  const [statuses, setStatuses] = useState<Record<number, SyncStatus>>({})
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState('all')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState<number | null>(null)
  const [message, setMessage] = useState('')
  const [extras, setExtras] = useState<Record<number, { submission?: Metric; alerts?: number; pending?: number; recent?: AcademicAlert[] }>>({})
  const load = useCallback(async () => {
    setError('')
    try {
      const cs = await listCourses()
      setCourses(cs)
      const results = await Promise.allSettled(cs.map(c => getSyncStatus(c.id)))
      setStatuses(Object.fromEntries(results.flatMap((r, i) => r.status === 'fulfilled' ? [[cs[i].id, r.value] as const] : [])))
      // Datos de cada tarjeta: tasa de entrega y alertas activas. Si fallan, la tarjeta dice «No disponible».
      // Se limita a los primeros cursos para no alargar la carga cuando el docente tiene muchos.
      void Promise.allSettled(cs.slice(0, MAX_SUMMARY).map(async c => {
        const [an, al] = await Promise.allSettled([getAnalytics(c.id), getAlerts(c.id, { page: 1, pageSize: 4 })])
        return [c.id, { submission: an.status === 'fulfilled' ? an.value.submissionRate : undefined, pending: an.status === 'fulfilled' ? an.value.counts?.pendingGradingCount : undefined, alerts: al.status === 'fulfilled' ? al.value.total : undefined, recent: al.status === 'fulfilled' ? al.value.items : undefined }] as const
      })).then(rs => setExtras(Object.fromEntries(rs.flatMap(r => r.status === 'fulfilled' ? [r.value] : []))))
    } catch (e) { setError(friendlyError(e)) }
    finally { setLoading(false) }
  }, [])
  useEffect(() => {
    const timer = window.setTimeout(() => { void load() }, 0)
    return () => window.clearTimeout(timer)
  }, [load])
  useEffect(() => {
    if (!Object.values(statuses).some(s => s.state === 'running')) return
    const timer = window.setInterval(async () => {
      const active = Object.entries(statuses).filter(([, s]) => s.state === 'running').map(([id]) => Number(id))
      const result = await Promise.allSettled(active.map(id => getSyncStatus(id)))
      let completed = false
      setStatuses(prev => {
        const next = { ...prev }
        result.forEach((r, i) => {
          if (r.status === 'fulfilled') { next[active[i]] = r.value; if (r.value.state === 'succeeded') completed = true }
        })
        return next
      })
      if (completed) { setMessage('Sincronización terminada. Datos actualizados.'); void load() }
    }, 3000)
    return () => window.clearInterval(timer)
  }, [statuses, load])
  const stateOf = useCallback((c: Course) => statuses[c.id]?.state || (c.lastSyncAt ? 'succeeded' : 'never'), [statuses])
  const visible = useMemo(() => courses.filter(c => {
    const match = `${c.fullName} ${c.shortName}`.toLowerCase().includes(search.trim().toLowerCase())
    return match && (filter === 'all' || filter === stateOf(c))
  }), [courses, search, filter, stateOf])
  const sync = async (id: number) => {
    setBusy(id); setMessage('')
    try {
      await startSync(id)
      setStatuses(s => ({ ...s, [id]: { ...s[id], state: 'running' } }))
      setMessage('La sincronización comenzó. Consultaremos su estado automáticamente.')
    } catch (e) {
      if (e instanceof ApiError && e.code === 'SYNC_IN_PROGRESS') {
        setStatuses(s => ({ ...s, [id]: { ...s[id], state: 'running' } }))
        setMessage('Este curso ya se está sincronizando.')
      } else setError(friendlyError(e))
    } finally { setBusy(null) }
  }
  const updated = courses.filter(c => stateOf(c) === 'succeeded').length
  const known = Object.values(extras)
  const summaryReady = known.some(e => e.alerts !== undefined || e.pending !== undefined)
  const totalAlerts = known.reduce((n, e) => n + (e.alerts || 0), 0)
  const totalPending = known.reduce((n, e) => n + (e.pending || 0), 0)
  const recent = known.flatMap(e => e.recent || []).sort((x, y) => y.detectedAt.localeCompare(x.detectedAt)).slice(0, 4)
  const codeOf = (id: number) => courses.find(c => c.id === id)?.shortName || `#${id}`
  const lastSync = courses.map(c => statuses[c.id]?.lastSuccessAt || c.lastSyncAt).filter(Boolean).sort().pop()
  const chatCourse = courses[0]?.id
  return <><PageHeader eyebrow="Espacio docente" title={`Hola, ${user?.name?.split(' ')[0] || 'docente'}`} subtitle="Consulta tus cursos autorizados y mantén su información sincronizada con Moodle." action={<Button variant="secondary" icon={<RefreshCw size={16}/>} onClick={() => { setLoading(true); void load() }}>Actualizar listado</Button>}/>
    {message && <Notice tone="success">{message}</Notice>}{error && <Notice tone="danger">{error}</Notice>}
    <p className="home-summary reveal">{summaryReady ? <>Tienes <strong><CountUp value={totalAlerts}/> {totalAlerts === 1 ? 'alerta activa' : 'alertas activas'}</strong> y <strong><CountUp value={totalPending}/> {totalPending === 1 ? 'entrega por calificar' : 'entregas por calificar'}</strong> en <strong>{courses.length} {courses.length === 1 ? 'curso' : 'cursos'}</strong>.</> : <>Tienes <strong>{courses.length} {courses.length === 1 ? 'curso asignado' : 'cursos asignados'}</strong>{updated ? <>, {updated} con datos actualizados</> : null}.</>}</p>
    <div className="toolbar"><div className="search-wrap"><Search size={18}/><input aria-label="Buscar cursos" placeholder="Buscar curso por nombre o código…" value={search} onChange={e => setSearch(e.target.value)}/></div><Segmented label="Filtrar por sincronización" options={FILTERS} value={filter} onChange={setFilter}/></div>
    {loading ? <StateView kind="loading" detail="Consultando cursos autorizados…"/> : error && !courses.length ? <StateView kind="error" detail={error} onRetry={() => { setLoading(true); void load() }}/> : !visible.length ? <StateView kind="empty" title={courses.length ? 'No se encontraron cursos' : 'No tienes cursos asignados'} detail={courses.length ? 'Prueba con otra búsqueda o filtro.' : 'Cuando un administrador te asigne cursos, aparecerán aquí.'}/> : <div className="home-layout"><div className="course-grid stagger">{visible.map(c => {
      const status = statuses[c.id]
      const state = stateOf(c)
      const last = status?.lastSuccessAt || c.lastSyncAt
      const isRunning = state === 'running' || busy === c.id
      const extra = extras[c.id]
      const rate = extra?.submission && extra.submission.status !== 'unavailable' && extra.submission.value !== null ? extra.submission.value : null
      return <Card className="course-card" key={c.id}>
        <div className="course-top"><span className="course-code">{c.shortName}</span><Badge tone={state === 'succeeded' ? 'success' : state === 'running' ? 'info' : state === 'failed' ? 'danger' : 'neutral'}>{statusText(state)}</Badge></div>
        <h2 style={{ viewTransitionName: `course-title-${c.id}` }}>{c.fullName}</h2>
        <div className="course-progress"><div className="cp-head"><span>Tasa de entrega</span><strong>{rate === null ? 'No disponible' : <><CountUp value={rate} digits={1}/> %</>}</strong></div><div className="meter"><i style={{ width: `${rate === null ? 0 : Math.max(0, Math.min(100, rate))}%` }}/></div></div>
        <dl className="course-facts">
          <div><dt><Bell size={15}/> Alertas activas</dt><dd>{extra?.alerts === undefined ? 'No disponible' : <CountUp value={extra.alerts}/>}</dd></div>
          <div><dt><UsersRound size={15}/> Estudiantes</dt><dd>{c.studentCount === undefined || c.studentCount === null ? 'No disponible' : c.studentCount}</dd></div>
          <div><dt><CalendarDays size={15}/> Última sincronización</dt><dd>{dateLabel(last)}</dd></div>
        </dl>
        {status?.state === 'failed' && <p className="course-error">{status.message || status.errorCode || 'La última sincronización falló.'}</p>}
        <div className="course-actions"><Link className="btn btn-primary" to={`/cursos/${c.id}`} state={{ name: c.fullName, code: c.shortName }} viewTransition><span>Abrir dashboard</span><ArrowRight size={16}/></Link><Button variant="secondary" loading={isRunning} onClick={() => void sync(c.id)} icon={<RefreshCw size={16}/>} disabled={isRunning} aria-label={`Sincronizar ${c.shortName}`}>{isRunning ? 'Sincronizando…' : 'Sincronizar'}</Button></div>
      </Card>
    })}</div>
      <aside className="today panel reveal" aria-label="Resumen de hoy">
        <h2>Resumen de hoy</h2>
        <section><h3><Bell size={15}/> Alertas recientes</h3>
          {recent.length ? <ul className="today-alerts">{recent.map(a => <li key={a.alertId}><Link viewTransition to={`/alertas?curso=${a.courseId}${a.studentId != null ? `&estudiante=${a.studentId}` : ''}`}><i data-sev={a.severity}/><span><strong>{ruleLabels[a.ruleCode] || a.ruleCode}</strong><small>{codeOf(a.courseId)} · {a.studentId != null ? `Estudiante #${a.studentId}` : 'Alerta de curso'}</small></span><ArrowRight size={15}/></Link></li>)}</ul> : <p className="muted small">{summaryReady ? 'No hay alertas activas.' : 'Sin información de alertas por ahora.'}</p>}
        </section>
        <section><h3><MessageSquareText size={15}/> Preguntar al agente</h3>
          <div className="today-ask">{QUICK.map(q => <Link key={q} viewTransition to={`/chat?${chatCourse ? `curso=${chatCourse}&` : ''}q=${encodeURIComponent(q)}`}>{q}<ArrowRight size={14}/></Link>)}</div>
        </section>
        <section className="today-sync"><h3><RefreshCw size={15}/> Última sincronización</h3><p>{dateLabel(lastSync)}</p></section>
      </aside>
    </div>}
    <p className="micro-note">La sincronización es manual y exclusiva de cada curso. El éxito se confirma únicamente cuando el servidor responde «Actualizado».</p>
  </>
}
