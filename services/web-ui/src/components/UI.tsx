import type { ButtonHTMLAttributes, PropsWithChildren, ReactNode } from 'react'
import { AlertTriangle, CheckCircle2, Clock3, DatabaseZap, LoaderCircle, RefreshCw, WifiOff } from 'lucide-react'
import type { Metric } from '../types/api'
import { metricLabel } from '../utils/display'

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
  const Icon = kind === 'loading' ? LoaderCircle : kind === 'error' ? WifiOff : DatabaseZap
  return <div className="state"><span className="state-icon"><Icon size={28} className={kind === 'loading' ? 'spin' : ''}/></span><h3>{title || (kind === 'loading' ? 'Cargando información' : kind === 'error' ? 'No se pudo cargar' : 'Sin resultados')}</h3><p>{detail || (kind === 'loading' ? 'Consultando el servidor…' : kind === 'empty' ? 'No hay información para mostrar.' : 'Comprueba la conexión y vuelve a intentarlo.')}</p>{kind === 'error' && onRetry && <Button variant="secondary" onClick={onRetry} icon={<RefreshCw size={16}/>}>Reintentar</Button>}</div>
}
export function MetricCard({ title, metric, note }: { title: string; metric?: Metric; note?: string }) {
  return <Card className="metric-card"><span className="metric-title">{title}</span><div className="metric-value">{metricLabel(metric)}</div><div className="metric-footer">{metric?.status === 'partial' ? <Badge tone="warning">Datos parciales</Badge> : metric?.status === 'unavailable' || !metric || metric.value === null ? <Badge tone="neutral">No disponible</Badge> : <Badge tone="success">Disponible</Badge>}{note && <span>{note}</span>}</div>{metric?.detail && <p className="muted tiny">{metric.detail}</p>}</Card>
}
export function DateLine({ label, value }: { label: string; value: string }) { return <div className="date-line"><Clock3 size={15}/><span>{label}</span><strong>{value}</strong></div> }
export function SectionTitle({ title, subtitle, right }: { title: string; subtitle?: string; right?: ReactNode }) { return <div className="section-title"><div><h2>{title}</h2>{subtitle && <p>{subtitle}</p>}</div>{right}</div> }
