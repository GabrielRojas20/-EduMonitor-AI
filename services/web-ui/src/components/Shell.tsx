import { useEffect, useLayoutEffect, useRef } from 'react'
import type { PropsWithChildren } from 'react'
import { Bell, BookOpen, LayoutDashboard, LogOut, MessageSquareText } from 'lucide-react'
import { NavLink, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'

export function Shell({ children }: PropsWithChildren) {
  const { user, signOut } = useAuth()
  const location = useLocation()
  const navigate = useNavigate()
  const navRef = useRef<HTMLElement>(null)
  const courseMatch = location.pathname.match(/^\/cursos\/(\d+)/)
  const courseId = courseMatch?.[1] || new URLSearchParams(location.search).get('curso')
  const activeCourse = courseId || ''
  const goLogout = () => { signOut(); navigate('/login', { replace: true }) }
  const path = location.pathname
  const isActiveItem = (label: string) => label === 'Mis cursos' ? path === '/cursos'
    : label === 'Dashboard' ? /^\/cursos\/\d+/.test(path)
    : label === 'Alertas' ? path.startsWith('/alertas') : path.startsWith('/chat')
  const nav = [
    { to: '/cursos', label: 'Mis cursos', icon: <BookOpen size={18}/> },
    { to: activeCourse ? `/cursos/${activeCourse}` : '/cursos', label: 'Dashboard', icon: <LayoutDashboard size={18}/> },
    { to: `/alertas${activeCourse ? `?curso=${activeCourse}` : ''}`, label: 'Alertas', icon: <Bell size={18}/> },
    { to: `/chat${activeCourse ? `?curso=${activeCourse}` : ''}`, label: 'Agente IA', icon: <MessageSquareText size={18}/> },
  ]

  // El indicador de la pestaña activa se desliza hasta su nueva posición.
  useLayoutEffect(() => {
    const place = () => {
      const el = navRef.current
      if (!el) return
      const active = el.querySelector<HTMLElement>('.tn-link.active')
      if (!active) { el.style.setProperty('--o', '0'); return }
      el.style.setProperty('--x', `${active.offsetLeft}px`)
      el.style.setProperty('--w', `${active.offsetWidth}px`)
      el.style.setProperty('--o', '1')
    }
    place()
    window.addEventListener('resize', place)
    void document.fonts?.ready.then(place)
    return () => window.removeEventListener('resize', place)
  }, [path])
  useEffect(() => { window.scrollTo({ top: 0 }) }, [path])

  return <div className="app-shell">
    <header className="topnav"><div className="topnav-inner">
      <NavLink to="/cursos" className="tn-brand" viewTransition aria-label="EduMonitor AI, ir a mis cursos">EduMonitor <b>AI</b></NavLink>
      <nav className="tn-nav" ref={navRef} aria-label="Navegación principal">
        <span className="tn-ink" aria-hidden="true"/>
        {nav.map(item => <NavLink key={item.label} to={item.to} viewTransition className={() => `tn-link ${isActiveItem(item.label) ? 'active' : ''}`}>{item.icon}<span>{item.label}</span></NavLink>)}
      </nav>
      <div className="tn-right">
        <span className="tn-status"><span className="tn-dot"/> Sesión activa</span>
        <button className="tn-user" onClick={goLogout} title="Cerrar sesión" aria-label="Cerrar sesión"><span className="avatar">{user?.name?.slice(0,1).toUpperCase() || 'D'}</span><span className="tn-user-name">{user?.name || 'Docente'}</span><LogOut size={16}/></button>
      </div>
    </div></header>
    <main className="content"><div className="page" key={location.pathname}>{children}</div></main>
    <footer className="footer">EduMonitor AI · Consulta académica de solo lectura · Los indicadores no reemplazan el criterio docente.</footer>
  </div>
}
