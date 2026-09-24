import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react';
import api from '../lib/api';

interface User {
  id: number;
  email: string;
  plan: string;
  created_at: string;
}

type AuthStatus = 'loading' | 'authenticated' | 'unauthenticated';

interface AuthContextType {
  user: User | null;
  token: string | null;
  authStatus: AuthStatus;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<{ api_key: string }>;
  logout: () => void;
  isAuthenticated: boolean;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(localStorage.getItem('access_token'));
  const [authStatus, setAuthStatus] = useState<AuthStatus>('loading');

  const fetchUser = useCallback(async () => {
    try {
      const res = await api.get('/auth/me');
      setUser(res.data);
      setAuthStatus('authenticated');
    } catch {
      localStorage.removeItem('access_token');
      setToken(null);
      setUser(null);
      setAuthStatus('unauthenticated');
    }
  }, []);

  useEffect(() => {
    if (token) {
      fetchUser();
    } else {
      setAuthStatus('unauthenticated');
    }
  }, [token, fetchUser]);

  const login = async (email: string, password: string) => {
    const res = await api.post('/auth/login', { email, password });
    const { access_token } = res.data;
    localStorage.setItem('access_token', access_token);
    setToken(access_token);
    await fetchUser();
  };

  const register = async (email: string, password: string) => {
    const res = await api.post('/auth/register', { email, password });
    return { api_key: res.data.api_key };
  };

  const logout = () => {
    localStorage.removeItem('access_token');
    setToken(null);
    setUser(null);
    setAuthStatus('unauthenticated');
  };

  return (
    <AuthContext.Provider value={{
      user,
      token,
      authStatus,
      login,
      register,
      logout,
      isAuthenticated: authStatus === 'authenticated',
      isLoading: authStatus === 'loading',
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
