import { BrowserRouter, Navigate, Route, Routes, useLocation, useSearchParams } from 'react-router-dom'
import type { PropsWithChildren } from 'react'
import { useAuth } from './hooks/useAuth'
import { AuthProvider } from './hooks/AuthProvider'
import { Shell } from './components/Shell'
import { LoginPage } from './pages/LoginPage'
import { CoursesPage } from './pages/CoursesPage'
import { DashboardPage } from './pages/DashboardPage'
import { StudentPage } from './pages/StudentPage'
import { AlertsPage } from './pages/AlertsPage'
import { ReportPage } from './pages/ReportPage'

function Private({ children }: PropsWithChildren) {
  const { token } = useAuth()
  const location = useLocation()
  if (!token) return <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />
  return <Shell>{children}</Shell>
}
/** El agente vive dentro de cada curso: los enlaces antiguos a /chat llevan al curso (con la pregunta, si traían una). */
function ChatRedirect() {
  const [p] = useSearchParams(); const course = p.get('curso'); const q = p.get('q')
  return <Navigate to={course ? `/cursos/${course}${q ? `?q=${encodeURIComponent(q)}` : ''}` : '/cursos'} replace/>
}
function LoginRoute() { const { token } = useAuth(); return token ? <Navigate to="/cursos" replace /> : <LoginPage/> }
function AppRoutes() { return <Routes>
  <Route path="/login" element={<LoginRoute/>}/>
  <Route path="/cursos" element={<Private><CoursesPage/></Private>}/>
  <Route path="/cursos/:id" element={<Private><DashboardPage/></Private>}/>
  <Route path="/cursos/:id/informe" element={<Private><ReportPage/></Private>}/>
  <Route path="/cursos/:id/estudiantes/:sid" element={<Private><StudentPage/></Private>}/>
  <Route path="/alertas" element={<Private><AlertsPage/></Private>}/>
  <Route path="/chat" element={<ChatRedirect/>}/>
  <Route path="*" element={<Navigate to="/cursos" replace/>}/>
</Routes> }
export default function App() { return <BrowserRouter><AuthProvider><AppRoutes/></AuthProvider></BrowserRouter> }
