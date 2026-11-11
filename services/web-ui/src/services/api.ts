export const TOKEN_KEY = 'edumonitor_token'
export const USER_KEY = 'edumonitor_user'

const baseUrl = (import.meta.env.VITE_API_URL || 'http://localhost:5000').replace(/\/$/, '')
const agentUrl = (import.meta.env.VITE_AGENT_URL || 'http://localhost:5004').replace(/\/$/, '')


export class ApiError extends Error {
  readonly status: number
  readonly code: string

  constructor(status: number, code: string, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
  }
}


interface RequestOptions extends RequestInit { authenticated?: boolean; agent?: boolean }
export async function request<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const { authenticated = true, agent = false, ...options } = opts
  const headers = new Headers(options.headers)
  if (options.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json')
  if (authenticated) {
    const token = sessionStorage.getItem(TOKEN_KEY)
    if (token) headers.set('Authorization', `Bearer ${token}`)
  }
  let response: Response
  try {
    response = await fetch(`${agent ? agentUrl : baseUrl}${path}`, { ...options, headers })
  } catch {
    throw new ApiError(0, 'NETWORK_ERROR', agent
      ? 'No se puede contactar al agente. Comprueba que agent-service esté iniciado en el puerto configurado.'
      : 'No se puede contactar al gateway. Comprueba que está iniciado en el puerto configurado.')
  }
  if (!response.ok) {
    const body: { code?: string; title?: string; detail?: string } = await response.json().catch(() => ({}))
    if (authenticated && response.status === 401) window.dispatchEvent(new Event('edumonitor:session-expired'))
    throw new ApiError(response.status, body.code || `HTTP_${response.status}`, body.detail || body.title || `Error HTTP ${response.status}`)
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}
export function get<T>(path: string, options?: RequestOptions) { return request<T>(path, options) }
export function post<T>(path: string, data: unknown, options?: RequestOptions) {
  return request<T>(path, { ...options, method: 'POST', body: JSON.stringify(data) })
}
export function friendlyError(error: unknown): string {
  if (!(error instanceof ApiError)) return 'Ocurrió un error inesperado. Puedes volver a intentarlo.'
  const messages: Record<string, string> = {
    INVALID_CREDENTIALS: 'Correo o contraseña incorrectos.',
    TOKEN_INVALID: 'La sesión ya no es válida. Inicia sesión otra vez.',
    TOKEN_EXPIRED: 'Tu sesión venció. Inicia sesión otra vez.',
    COURSE_NOT_AUTHORIZED: 'No tienes acceso a este curso.',
    COURSE_NOT_FOUND: 'El curso solicitado no existe.',
    STUDENT_NOT_FOUND: 'El estudiante no está registrado en este curso.',
    DATA_NOT_AVAILABLE: 'Los datos de este curso aún no están disponibles. Intenta sincronizarlo.',
    MOODLE_UNAVAILABLE: 'Moodle o un servicio interno no está disponible en este momento.',
    SYNC_IN_PROGRESS: 'Este curso ya se está sincronizando.',
    TOOL_TIMEOUT: 'La consulta del agente superó el tiempo de espera. Inténtalo de nuevo.',
  }
  return messages[error.code] || error.message
}
