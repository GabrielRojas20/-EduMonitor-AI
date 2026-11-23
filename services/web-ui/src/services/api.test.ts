import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError, request, TOKEN_KEY, friendlyError } from './api'

describe('Cliente HTTP y sesión', () => {
  beforeEach(() => sessionStorage.clear())

  it('agrega el token a las consultas autenticadas', async () => {
    sessionStorage.setItem(TOKEN_KEY, 'jwt-ficticio')
    const fake = vi.fn().mockResolvedValue(new Response(JSON.stringify({ ok: true }), { status: 200 }))
    vi.stubGlobal('fetch', fake)
    await expect(request('/api/v1/courses')).resolves.toEqual({ ok: true })
    const headers = fake.mock.calls[0][1].headers as Headers
    expect(headers.get('Authorization')).toBe('Bearer jwt-ficticio')
  })

  it('omite la autorización en el inicio de sesión', async () => {
    sessionStorage.setItem(TOKEN_KEY, 'jwt-ficticio')
    const fake = vi.fn().mockResolvedValue(new Response(JSON.stringify({ ok: true }), { status: 200 }))
    vi.stubGlobal('fetch', fake)
    await request('/api/v1/auth/login', { authenticated: false, method: 'POST', body: '{}' })
    const headers = fake.mock.calls[0][1].headers as Headers
    expect(headers.has('Authorization')).toBe(false)
    expect(headers.get('Content-Type')).toBe('application/json')
  })

  it('dispara el evento de sesión vencida ante HTTP 401', async () => {
    const expired = vi.fn()
    window.addEventListener('edumonitor:session-expired', expired)
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ code: 'TOKEN_EXPIRED', detail: 'Expirado' }), { status: 401 })))
    await expect(request('/api/v1/courses')).rejects.toMatchObject({ status: 401, code: 'TOKEN_EXPIRED' })
    expect(expired).toHaveBeenCalledOnce()
    window.removeEventListener('edumonitor:session-expired', expired)
  })

  it('respeta el código de error y lo convierte en un mensaje entendible', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ code: 'COURSE_NOT_AUTHORIZED', detail: 'Acceso denegado' }), { status: 403 })))
    await expect(request('/api/v1/courses/99')).rejects.toMatchObject({ status: 403, code: 'COURSE_NOT_AUTHORIZED' })
    expect(friendlyError(new ApiError(403, 'COURSE_NOT_AUTHORIZED', 'Acceso denegado'))).toContain('No tienes acceso')
  })

  it('no convierte errores de red en datos académicos ficticios', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Sin conexión')))
    await expect(request('/api/v1/courses')).rejects.toMatchObject({ status: 0, code: 'NETWORK_ERROR' })
  })

  it('resuelve las respuestas sin cuerpo HTTP 204', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(null, { status: 204 })))
    await expect(request('/api/v1/courses/2')).resolves.toBeUndefined()
  })
  it('interpreta el rechazo HTTP 401 al iniciar sesión', async () => {
    const response = new Response(JSON.stringify({
      code: 'INVALID_CREDENTIALS',
      detail: 'Credenciales rechazadas',
    }), { status: 401, headers: { 'Content-Type': 'application/json' } })
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response))
    await expect(request('/api/v1/auth/login', {
      method: 'POST',
      authenticated: false,
      body: JSON.stringify({ email: 'docente@edumonitor.test', password: 'incorrecta' }),
    })).rejects.toMatchObject({ status: 401, code: 'INVALID_CREDENTIALS' })
    expect(friendlyError(new ApiError(401, 'INVALID_CREDENTIALS', 'Credenciales rechazadas')))
      .toBe('Correo o contraseña incorrectos.')
  })

})
