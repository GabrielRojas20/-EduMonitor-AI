import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { LoginPage } from './LoginPage'

const { signIn } = vi.hoisted(() => ({ signIn: vi.fn() }))
vi.mock('../hooks/useAuth', () => ({
  useAuth: () => ({ signIn, expired: false, clearExpired: vi.fn() }),
}))
vi.mock('../components/LoginArt', () => ({
  DotField: () => null,
  Rotator: () => null,
}))

describe('Formulario de inicio de sesión', () => {
  beforeEach(() => signIn.mockReset())

  it('valida un correo incorrecto sin llamar a la API', () => {
    render(<MemoryRouter><LoginPage /></MemoryRouter>)
    fireEvent.click(screen.getByRole('button', { name: /Iniciar sesión/i }))
    expect(screen.getByText('Introduce un correo válido.')).toBeInTheDocument()
    expect(signIn).not.toHaveBeenCalled()
  })

  it('exige contraseña', () => {
    render(<MemoryRouter><LoginPage /></MemoryRouter>)
    fireEvent.change(screen.getByLabelText('Correo electrónico'), { target: { value: 'docente@edumonitor.test' } })
    fireEvent.click(screen.getByRole('button', { name: /Iniciar sesión/i }))
    expect(screen.getByText('Introduce tu contraseña.')).toBeInTheDocument()
    expect(signIn).not.toHaveBeenCalled()
  })

})
