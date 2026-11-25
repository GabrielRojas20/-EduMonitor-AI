import { useEffect, useId, useRef, useState } from 'react'
import type { ButtonHTMLAttributes, CSSProperties, PropsWithChildren, ReactNode } from 'react'
import { AlertTriangle, BellOff, BookOpen, CheckCircle2, ClipboardList, Clock3, DatabaseZap, LoaderCircle, RefreshCw, SearchX, UsersRound, WifiOff } from 'lucide-react'
import type { Metric } from '../types/api'
import { numberLabel } from '../utils/display'

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & { variant?: 'primary' | 'secondary' | 'ghost' | 'danger'; loading?: boolean; icon?: ReactNode }
export function Button({ variant = 'primary', loading = false, icon, children, className = '', disabled, ...props }: ButtonProps) {
  return <button className={`btn btn-${variant} ${className}`} disabled={loading || disabled} {...props}>{loading ? <LoaderCircle className="spin" size={16} /> : icon}{children}</button>
}
export function Card({ children, className = '' }: PropsWithChildren<{ className?: string }>) { return <section className={`panel ${className}`}>{children}</section> }
export function Badge({ tone = 'neutral', children }: PropsWithChildren<{ tone?: 'neutral' | 'success' | 'warning' | 'danger' | 'info' }>) { return <span className={`badge badge-${tone}`}>{children}</span> }
export function PageHeader({ title, subtitle, action, eyebrow }: { title: string; subtitle?: string; eyebrow?: string; action?: ReactNode }) {
  return <header className="page-header"><div>{eyebrow && <div className="eyebrow">{eyebrow}</div>}<h1>{title}</h1>{subtitle && <p>{subtitle}</p>}</div>{action && <div className="page-actions">{action}</div>}</header>
}
export function Notice({ tone = 'info', children }: PropsWithChildren<{ tone?: 'info' | 'warning' | 'danger' | 'success' }>) {
  const Icon = tone === 'danger' || tone === 'warning' ? AlertTriangle : tone === 'success' ? CheckCircle2 : DatabaseZap
  return <div className={`notice notice-${tone}`} role={tone === 'danger' ? 'alert' : 'status'}><Icon size={18} /><div>{children}</div></div>
}
export function StateView({ kind, title, detail, onRetry }: { kind: 'loading' | 'empty' | 'error'; title?: string; detail?: string; onRetry?: () => void }) {
  if (kind === 'loading') return <div className="skeleton" role="status" aria-live="polite"><div className="skeleton-row"><i/><i/><i/></div><i className="wide"/><p className="skeleton-note">{detail || title || 'Consultando el servidor…'}</p></div>
  const topic = `${title || ''} ${detail || ''}`.toLowerCase()
  const EmptyIcon = /alerta/.test(topic) ? BellOff : /estudiante/.test(topic) ? UsersRound : /curso/.test(topic) ? BookOpen : /nota|entrega|calific|informe|indicador|hallazgo/.test(topic) ? ClipboardList : SearchX
  return <div className={`state state-${kind}`} role={kind === 'error' ? 'alert' : undefined}>
    {kind === 'empty'
      ? <div className="empty-illustration" data-testid="empty-illustration" aria-hidden="true"><span className="empty-illustration-paper"/><span className="empty-illustration-icon"><EmptyIcon size={34} strokeWidth={1.8}/></span></div>
      : <span className="state-icon"><WifiOff size={28}/></span>}
    <h3>{title || (kind === 'error' ? 'No se pudo cargar' : 'Sin resultados')}</h3>
    <p>{detail || (kind === 'empty' ? 'Prueba con otra búsqueda o comprueba si hay información sincronizada.' : 'Comprueba la conexión y vuelve a intentarlo.')}</p>
    {kind === 'error' && onRetry && <Button variant="secondary" onClick={onRetry} icon={<RefreshCw size={16}/>}>Reintentar</Button>}
  </div>
}
export function Meter({ value }: { value: number }) {
  return <div className="meter" role="presentation"><i style={{ width: `${Math.max(0, Math.min(100, value))}%` }}/></div>
}
export function Avatar({ name }: { name: string }) {
  const initials = name.split(/\s+/).filter(Boolean).slice(0, 2).map(p => p[0]?.toUpperCase()).join('') || '?'
  return <span className="avatar" aria-hidden="true">{initials}</span>
}
/** Número que sube hasta su valor al aparecer (sin movimiento si el usuario lo prefiere así). */
export function CountUp({ value, digits = 0 }: { value: number; digits?: number }) {
  const [shown, setShown] = useState(0)
  const reduced = typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches
  useEffect(() => {
    if (reduced) return
    let frame = 0
    const start = performance.now()
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / 900)
      setShown(value * (1 - Math.pow(1 - t, 4)))
      if (t < 1) frame = requestAnimationFrame(tick)
    }
    frame = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frame)
  }, [value, reduced])
  return <>{numberLabel(reduced ? value : shown, digits)}</>
}
export function Ring({ value }: { value: number }) {
  const id = useId()
  const p = Math.max(0, Math.min(100, value))
  return <div className="ring" aria-hidden="true" style={{ ['--p' as string]: p } as CSSProperties}><svg viewBox="0 0 60 60" width="58" height="58"><defs><linearGradient id={id} x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stopColor="#163a2c"/><stop offset="100%" stopColor="#3f7a5f"/></linearGradient></defs><circle className="track" cx="30" cy="30" r="24"/><circle className="bar" cx="30" cy="30" r="24" style={{ stroke: `url(#${id})` }}/></svg></div>
}
export function Segmented<T extends string>({ label, options, value, onChange }: { label: string; options: { value: T; label: string }[]; value: T; onChange: (v: T) => void }) {
  return <div className="seg" role="radiogroup" aria-label={label}>{options.map(o => <button key={o.value} type="button" role="radio" aria-checked={value === o.value} onClick={() => onChange(o.value)}>{o.label}</button>)}</div>
}
function metricParts(metric?: Metric): { value: number | null; digits: number; unit: string; fill: number | null } {
  if (!metric || metric.status === 'unavailable' || metric.value === null) return { value: null, digits: 0, unit: '', fill: null }
  if (metric.unit === 'percent') return { value: metric.value, digits: 1, unit: '%', fill: metric.value }
  if (metric.unit === 'score_0_10') return { value: metric.value, digits: 2, unit: '/ 10', fill: metric.value * 10 }
  return { value: metric.value, digits: 0, unit: '', fill: null }
}
export function MetricCard({ title, metric, note }: { title: string; metric?: Metric; note?: string }) {
  const { value, digits, unit, fill } = metricParts(metric)
  const unavailable = value === null
  return <Card className="metric-card"><div className="kpi-top"><span className="metric-title">{title}</span>{fill !== null && <Ring value={fill}/>}</div><div className="metric-value" style={unavailable ? { fontSize: 24, lineHeight: 1.3, letterSpacing: '-0.02em' } : undefined}>{unavailable ? 'No disponible' : <><CountUp value={value} digits={digits}/>{unit && <small>{unit}</small>}</>}</div><div className="metric-footer">{metric?.status === 'partial' ? <Badge tone="warning">Datos parciales</Badge> : unavailable ? <Badge tone="neutral">Sin datos</Badge> : <Badge tone="success">Disponible</Badge>}{note && <span>{note}</span>}</div>{metric?.detail && <p className="muted tiny">{metric.detail}</p>}</Card>
}
export function DateLine({ label, value }: { label: string; value: string }) { return <div className="date-line"><Clock3 size={15}/><span>{label}</span><strong>{value}</strong></div> }
export function SectionTitle({ title, subtitle, right }: { title: string; subtitle?: string; right?: ReactNode }) { return <div className="section-title"><div><h2>{title}</h2>{subtitle && <p>{subtitle}</p>}</div>{right}</div> }


/** Muestra su contenido cuando entra en pantalla: así los gráficos se animan al verlos, no antes. */
export function InView({ children, className = '' }: PropsWithChildren<{ className?: string }>) {
  const ref = useRef<HTMLDivElement>(null)
  const [seen, setSeen] = useState(false)
  useEffect(() => {
    const el = ref.current
    if (!el || seen) return
    const io = new IntersectionObserver(entries => { if (entries.some(e => e.isIntersecting)) { setSeen(true); io.disconnect() } }, { threshold: 0.25 })
    io.observe(el)
    return () => io.disconnect()
  }, [seen])
  return <div ref={ref} className={className}>{seen ? children : null}</div>
}
