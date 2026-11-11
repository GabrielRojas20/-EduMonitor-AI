import { useCallback, useEffect, useMemo, useState } from 'react'
import { ArrowRight, BookOpen, CalendarDays, RefreshCw, Search, UsersRound } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { Button, Card, Badge, Notice, PageHeader, StateView } from '../components/UI'
import { ApiError, friendlyError } from '../services/api'
import { getSyncStatus, listCourses, startSync } from '../services/edumonitor'
import type { Course, SyncStatus } from '../types/api'
import { dateLabel, statusText } from '../utils/display'

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
  const load = useCallback(async () => {
    setError('')
    try {
      const cs = await listCourses()
      setCourses(cs)
      const results = await Promise.allSettled(cs.map(c => getSyncStatus(c.id)))
      setStatuses(Object.fromEntries(results.flatMap((r, i) => r.status === 'fulfilled' ? [[cs[i].id, r.value] as const] : [])))
    } catch (e) { setError(friendlyError(e)) }
    finally { setLoading(false) }
  }, [])
  useEffect(() => { void load() }, [load])
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
  const visible = useMemo(() => courses.filter(c => {
    const match = `${c.fullName} ${c.shortName}`.toLowerCase().includes(search.trim().toLowerCase())
    const state = statuses[c.id]?.state || (c.lastSyncAt ? 'succeeded' : 'never')
    return match && (filter === 'all' || filter === state)
  }), [courses, search, filter, statuses])
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
  return <><PageHeader eyebrow="ESPACIO DOCENTE" title={`Hola, ${user?.name?.split(' ')[0] || 'docente'}`} subtitle="Consulta tus cursos autorizados y mantén su información sincronizada con Moodle." action={<Button variant="secondary" icon={<RefreshCw size={16}/>} onClick={() => { setLoading(true); void load() }}>Actualizar listado</Button>}/>
    {message && <Notice tone="success">{message}</Notice>}{error && <Notice tone="danger">{error}</Notice>}
    <div className="summary-strip"><div className="summary-icon"><BookOpen size={22}/></div><div><strong>{courses.length}</strong><span>Cursos asignados a tu cuenta</span></div><div className="strip-tail">Solo se muestran cursos a los que tienes acceso.</div></div>
    <div className="toolbar"><div className="search-wrap"><Search size={18}/><input aria-label="Buscar cursos" placeholder="Buscar curso por nombre o código…" value={search} onChange={e=>setSearch(e.target.value)}/></div><select aria-label="Filtrar por sincronización" value={filter} onChange={e=>setFilter(e.target.value)}><option value="all">Todos los estados</option><option value="succeeded">Actualizados</option><option value="never">Nunca sincronizados</option><option value="running">Sincronizando</option><option value="failed">Fallidos</option></select></div>
    {loading ? <StateView kind="loading" detail="Consultando cursos autorizados…"/> : error && !courses.length ? <StateView kind="error" detail={error} onRetry={()=>{setLoading(true);void load()}}/> : !visible.length ? <StateView kind="empty" title={courses.length ? 'No se encontraron cursos' : 'No tienes cursos asignados'} detail={courses.length ? 'Prueba con otra búsqueda o filtro.' : 'Cuando un administrador te asigne cursos, aparecerán aquí.'}/> : <div className="course-grid">{visible.map(c => {
      const status = statuses[c.id]
      const state = status?.state || (c.lastSyncAt ? 'succeeded' : 'never')
      const last = status?.lastSuccessAt || c.lastSyncAt
      const isRunning = state === 'running' || busy === c.id
      return <Card className="course-card" key={c.id}><div className="course-card-top"><div className="course-icon"><BookOpen size={24}/></div><Badge tone={state==='succeeded'?'success':state==='running'?'info':state==='failed'?'danger':'neutral'}>{statusText(state)}</Badge></div><span className="course-code">{c.shortName}</span><h2>{c.fullName}</h2><div className="course-meta"><span><UsersRound size={16}/>{c.studentCount === undefined ? 'Estudiantes: no disponible' : `${c.studentCount} estudiantes`}</span><span><CalendarDays size={16}/>Última sincronización: {dateLabel(last)}</span></div>{status?.state === 'failed' && <p className="course-error">{status.message || status.errorCode || 'La última sincronización falló.'}</p>}<div className="course-actions"><Button variant="secondary" loading={isRunning} onClick={()=>void sync(c.id)} icon={<RefreshCw size={16}/>} disabled={isRunning}>{isRunning ? 'Sincronizando…' : 'Sincronizar'}</Button><Link className="btn btn-primary" to={`/cursos/${c.id}`}><span>Abrir dashboard</span><ArrowRight size={16}/></Link></div></Card>
    })}</div>}
    <p className="micro-note">La sincronización es manual y exclusiva de cada curso. El éxito se confirma únicamente cuando el servidor responde «Actualizado».</p>
  </>
}
