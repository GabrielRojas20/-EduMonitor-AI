import { BrowserRouter, Navigate, Route, Routes, useLocation } from 'react-router-dom'
import type { PropsWithChildren } from 'react'
import { AuthProvider, useAuth } from './hooks/useAuth'
import { Shell } from './components/Shell'
import { LoginPage } from './pages/LoginPage'
import { CoursesPage } from './pages/CoursesPage'
import { DashboardPage } from './pages/DashboardPage'
import { StudentPage } from './pages/StudentPage'
import { AlertsPage } from './pages/AlertsPage'
import { ChatPage } from './pages/ChatPage'

function Private({ children }: PropsWithChildren) {
  const { token } = useAuth()
  const location = useLocation()
  if (!token) return <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />
  return <Shell>{children}</Shell>
}
function LoginRoute() { const { token } = useAuth(); return token ? <Navigate to="/cursos" replace /> : <LoginPage/> }
function AppRoutes() { return <Routes>
  <Route path="/login" element={<LoginRoute/>}/>
  <Route path="/cursos" element={<Private><CoursesPage/></Private>}/>
  <Route path="/cursos/:id" element={<Private><DashboardPage/></Private>}/>
  <Route path="/cursos/:id/estudiantes/:sid" element={<Private><StudentPage/></Private>}/>
  <Route path="/alertas" element={<Private><AlertsPage/></Private>}/>
  <Route path="/chat" element={<Private><ChatPage/></Private>}/>
  <Route path="*" element={<Navigate to="/cursos" replace/>}/>
</Routes> }
export default function App() { return <BrowserRouter><AuthProvider><AppRoutes/></AuthProvider></BrowserRouter> }
