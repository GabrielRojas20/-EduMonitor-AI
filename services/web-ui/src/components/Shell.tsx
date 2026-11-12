import type { PropsWithChildren } from 'react'
import { Activity, Bell, BookOpen, ChevronRight, GraduationCap, LayoutDashboard, LogOut, MessageSquareText, ShieldCheck } from 'lucide-react'
import { NavLink, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'

export function Shell({ children }: PropsWithChildren) {
  const { user, signOut } = useAuth()
  const location = useLocation()
  const navigate = useNavigate()
  const courseMatch = location.pathname.match(/^\/cursos\/(\d+)/)
  const courseId = courseMatch?.[1] || new URLSearchParams(location.search).get('curso')
  const activeCourse = courseId || ''
  const goLogout = () => { signOut(); navigate('/login', { replace: true }) }
  const nav = [
    { to: '/cursos', label: 'Mis cursos', icon: <BookOpen size={19}/> },
    { to: activeCourse ? `/cursos/${activeCourse}` : '/cursos', label: 'Dashboard', icon: <LayoutDashboard size={19}/> },
    { to: `/alertas${activeCourse ? `?curso=${activeCourse}` : ''}`, label: 'Alertas', icon: <Bell size={19}/> },
    { to: `/chat${activeCourse ? `?curso=${activeCourse}` : ''}`, label: 'Agente IA', icon: <MessageSquareText size={19}/> },
  ]
  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand"><div className="brand-icon"><Activity size={23}/></div><div><strong>EduMonitor <span>AI</span></strong><small>Seguimiento académico</small></div></div>
      <div className="nav-label">PLATAFORMA</div>
      <nav className="side-nav" aria-label="Navegación principal">{nav.map(item => <NavLink key={item.label} to={item.to} end={item.to === '/cursos'} className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>{item.icon}<span>{item.label}</span><ChevronRight className="nav-chevron" size={16}/></NavLink>)}</nav>
      <div className="sidebar-bottom"><div className="sidebar-note"><ShieldCheck size={18}/><span>Datos académicos protegidos<br/><small>Acceso según tu cuenta</small></span></div><button className="user-card" onClick={goLogout} title="Cerrar sesión"><span className="avatar">{user?.name?.slice(0,1).toUpperCase() || 'D'}</span><span className="user-text"><strong>{user?.name || 'Docente'}</strong><small>{user?.email || 'Sesión activa'}</small></span><LogOut size={17}/></button></div>
    </aside>
    <div className="main-column"><header className="topbar"><div className="topbar-path"><GraduationCap size={18}/><span>EduMonitor AI</span><ChevronRight size={15}/><strong>Panel docente</strong></div><div className="topbar-user"><span className="topbar-dot"/> Sesión activa</div></header><main className="content">{children}</main><footer className="footer">EduMonitor AI · Consulta académica de solo lectura · Los indicadores no reemplazan el criterio docente.</footer></div>
  </div>
}
