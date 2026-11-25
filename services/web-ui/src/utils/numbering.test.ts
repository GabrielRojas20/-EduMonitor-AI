import { describe, expect, it } from 'vitest'
import { numberStudents, studentLabel } from './display'

describe('Numeración de estudiantes de un curso', () => {
  const students = [{ id: 307, fullName: 'Zoe Zambrano' }, { id: 12, fullName: 'Ana Acosta' }, { id: 308, fullName: 'Bruno Benítez' }]

  it('numera de 1 al total, por orden alfabético, sin usar el id de Moodle', () => {
    const numbering = numberStudents(students)
    expect(numbering.get(12)).toEqual({ n: 1, total: 3, name: 'Ana Acosta' })
    expect(numbering.get(308)?.n).toBe(2)
    expect(numbering.get(307)).toEqual({ n: 3, total: 3, name: 'Zoe Zambrano' })
  })

  it('escribe el número y el nombre, y no inventa uno para un estudiante de otro curso', () => {
    const numbering = numberStudents(students)
    expect(studentLabel(numbering, 307)).toBe('N.º 3 · Zoe Zambrano')
    expect(studentLabel(numbering, 999)).toBe('Estudiante de otro curso')
  })
})

describe('Sin la lista de estudiantes del curso', () => {
  it('muestra el id en vez de decir que es de otro curso', () => {
    expect(studentLabel(new Map(), 307)).toBe('Estudiante (ID 307)')
  })
})
