import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { MetricCard, StateView } from './UI'

describe('Indicadores y estados de pantalla', () => {
  it('no presenta un indicador ausente como cero', () => {
    render(<MetricCard title="Promedio del curso" metric={{ value: null, unit: 'score_0_10', status: 'unavailable' }} />)
    expect(screen.getByText('No disponible')).toBeInTheDocument()
  })

  it('diferencia una calificación cero disponible', () => {
    render(<MetricCard title="Promedio del curso" metric={{ value: 0, unit: 'score_0_10', status: 'available' }} />)
    expect(screen.queryByText('No disponible')).not.toBeInTheDocument()
    expect(screen.getByText('Disponible')).toBeInTheDocument()
  })

  it('muestra la pantalla de carga', () => {
    render(<StateView kind="loading" title="Cargando datos" />)
    expect(screen.getByRole('status')).toBeInTheDocument()
  })

  it('muestra el estado vacío y una explicación', () => {
    render(<StateView kind="empty" title="Sin resultados" detail="Intenta sincronizar el curso." />)
    expect(screen.getByText('Sin resultados')).toBeInTheDocument()
    expect(screen.getByText('Intenta sincronizar el curso.')).toBeInTheDocument()
  })

  it('ofrece reintentar ante un fallo de conexión', () => {
    const retry = vi.fn()
    render(<StateView kind="error" title="Sin conexión" onRetry={retry} />)
    fireEvent.click(screen.getByRole('button', { name: /Reintentar/i }))
    expect(retry).toHaveBeenCalledOnce()
  })
})
