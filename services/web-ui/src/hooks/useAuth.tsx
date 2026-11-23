import { useContext } from 'react'
import { AuthContext } from './authContext'

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth requiere AuthProvider')
  return ctx
}
