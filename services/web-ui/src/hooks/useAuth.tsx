import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import type { PropsWithChildren } from 'react'
import { TOKEN_KEY, USER_KEY } from '../services/api'
import { login as loginApi } from '../services/edumonitor'
import type { User } from '../types/api'

interface AuthContextShape { token: string | null; user: User | null; signIn: (email: string, password: string) => Promise<void>; signOut: () => void; expired: boolean; clearExpired: () => void }
const AuthContext = createContext<AuthContextShape | undefined>(undefined)
const savedUser = (): User | null => { try { const raw = sessionStorage.getItem(USER_KEY); return raw ? JSON.parse(raw) as User : null } catch { return null } }
export function AuthProvider({ children }: PropsWithChildren) {
  const [token, setToken] = useState<string | null>(() => sessionStorage.getItem(TOKEN_KEY))
  const [user, setUser] = useState<User | null>(savedUser)
  const [expired, setExpired] = useState(false)
  const signOut = useCallback(() => { sessionStorage.removeItem(TOKEN_KEY); sessionStorage.removeItem(USER_KEY); setToken(null); setUser(null) }, [])
  useEffect(() => {
    const handler = () => { signOut(); setExpired(true) }
    window.addEventListener('edumonitor:session-expired', handler)
    return () => window.removeEventListener('edumonitor:session-expired', handler)
  }, [signOut])
  const signIn = useCallback(async (email: string, password: string) => {
    const response = await loginApi(email, password)
    sessionStorage.setItem(TOKEN_KEY, response.accessToken)
    sessionStorage.setItem(USER_KEY, JSON.stringify(response.user))
    setToken(response.accessToken)
    setUser(response.user)
    setExpired(false)
  }, [])
  const value = useMemo(() => ({ token, user, signIn, signOut, expired, clearExpired: () => setExpired(false) }), [token, user, signIn, signOut, expired])
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth requiere AuthProvider')
  return ctx
}
