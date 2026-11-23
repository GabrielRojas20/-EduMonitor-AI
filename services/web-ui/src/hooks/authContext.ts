import { createContext } from 'react'
import type { User } from '../types/api'

export interface AuthContextShape {
  token: string | null
  user: User | null
  signIn: (email: string, password: string) => Promise<void>
  signOut: () => void
  expired: boolean
  clearExpired: () => void
}
export const AuthContext = createContext<AuthContextShape | undefined>(undefined)
