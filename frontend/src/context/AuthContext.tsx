import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import { apiFetch } from '../api';

interface User { id: number; username: string }

interface AuthCtx {
  user: User | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  signup: (username: string, password: string, password2: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthCtx>(null!);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiFetch<User>('/me')
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setLoading(false));
  }, []);

  const login = async (username: string, password: string) => {
    await apiFetch('/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    });
    const me = await apiFetch<User>('/me');
    setUser(me);
  };

  const signup = async (username: string, password: string, password2: string) => {
    await apiFetch('/signup', {
      method: 'POST',
      body: JSON.stringify({ username, password, password2 }),
    });
    const me = await apiFetch<User>('/me');
    setUser(me);
  };

  const logout = async () => {
    await apiFetch('/logout', { method: 'POST' });
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, signup, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
