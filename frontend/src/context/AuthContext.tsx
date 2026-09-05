import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import { getCurrentUser, loginUser, tokenStorage } from '../services/api';

export type Role = 'admin' | 'reviewer' | 'viewer';

export interface CurrentUser {
  id: string;
  email: string;
  full_name: string | null;
  role: Role;
  is_active: boolean;
}

interface AuthContextValue {
  user: CurrentUser | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  hasMinRole: (minRole: Role) => boolean;
}

const ROLE_RANK: Record<Role, number> = { viewer: 0, reviewer: 1, admin: 2 };

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const bootstrap = async () => {
      if (!tokenStorage.getAccessToken()) {
        setIsLoading(false);
        return;
      }
      try {
        const { data } = await getCurrentUser();
        setUser(data);
      } catch {
        tokenStorage.clear();
      } finally {
        setIsLoading(false);
      }
    };
    bootstrap();
  }, []);

  const login = async (email: string, password: string) => {
    const { data } = await loginUser(email, password);
    tokenStorage.setTokens(data.access_token, data.refresh_token);
    const me = await getCurrentUser();
    setUser(me.data);
  };

  const logout = () => {
    tokenStorage.clear();
    setUser(null);
  };

  const hasMinRole = (minRole: Role) => {
    if (!user) return false;
    return ROLE_RANK[user.role] >= ROLE_RANK[minRole];
  };

  return (
    <AuthContext.Provider value={{ user, isLoading, login, logout, hasMinRole }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider');
  return ctx;
}
