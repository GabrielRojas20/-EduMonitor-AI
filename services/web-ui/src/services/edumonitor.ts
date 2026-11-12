import { get, post } from './api'
import type { AcademicAlert, AlertSeverity, AlertStatus, Analytics, ChatResponse, Course, Grade, LoginResponse, Paginated, Student, StudentDetail, SyncAccepted, SyncStatus, User } from '../types/api'

const base = '/api/v1'
export const login = (email: string, password: string) => post<LoginResponse>(`${base}/auth/login`, { email, password }, { authenticated: false })
export const currentUser = () => get<User>(`${base}/me`)
export const listCourses = () => get<Course[]>(`${base}/courses`)
export const getCourse = (id: number) => get<Course>(`${base}/courses/${id}`)
export const getSyncStatus = (id: number) => get<SyncStatus>(`${base}/courses/${id}/sync`)
export const startSync = (id: number) => post<SyncAccepted>(`${base}/courses/${id}/sync`, {})
export const getAnalytics = (id: number) => get<Analytics>(`${base}/courses/${id}/analytics`)
export const getStudentAnalytics = (id: number, studentId: number) => get<Analytics>(`${base}/courses/${id}/analytics/students/${studentId}`)
export const getStudentDetail = (id: number, studentId: number) => get<StudentDetail>(`${base}/courses/${id}/students/${studentId}`)
export const getStudents = (id: number, page = 1, pageSize = 50) => get<Paginated<Student>>(`${base}/courses/${id}/students?page=${page}&pageSize=${pageSize}`)
export const getGrades = (id: number, page = 1, pageSize = 50) => get<Paginated<Grade>>(`${base}/courses/${id}/grades?page=${page}&pageSize=${pageSize}`)
export const getAlerts = (id: number, filters: { severity?: AlertSeverity; status?: AlertStatus; studentId?: number; page?: number; pageSize?: number } = {}) => {
  const q = new URLSearchParams({ page: String(filters.page || 1), pageSize: String(filters.pageSize || 50), status: filters.status || 'active' })
  if (filters.severity) q.set('severity', filters.severity)
  if (filters.studentId) q.set('studentId', String(filters.studentId))
  return get<Paginated<AcademicAlert>>(`${base}/courses/${id}/analytics/alerts?${q}`)
}
export const sendChat = (message: string, courseId?: number) => post<ChatResponse>('/chat', { message, ...(courseId ? { courseId } : {}) }, { agent: true })

// La API pagina a 200 elementos como máximo. Cargamos todas las páginas para que
// búsqueda y gráficos no dependan solo de la página visible.
export async function fetchAll<T>(load: (page: number, size: number) => Promise<Paginated<T>>): Promise<{ items: T[]; truncated: boolean }> {
  const size = 200
  const first = await load(1, size)
  const items = [...first.items]
  const totalPages = Math.ceil(first.total / size)
  const maxPages = 40
  for (let page = 2; page <= Math.min(totalPages, maxPages); page++) {
    const next = await load(page, size)
    items.push(...next.items)
  }
  return { items, truncated: totalPages > maxPages }
}
