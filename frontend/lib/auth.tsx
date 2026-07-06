"use client";

import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { authApi, tokens, savedAccounts, SavedAccount, Me } from "./api";

interface AuthState {
  user: Me | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  refreshMe: () => Promise<void>;
  // Multi-account
  accounts: SavedAccount[];
  switchAccount: (username: string) => Promise<void>;
  removeAccount: (username: string) => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<Me | null>(null);
  const [loading, setLoading] = useState(true);
  // Lazy init from localStorage (guarded for SSR) so the mount effect stays free
  // of synchronous setState.
  const [accounts, setAccounts] = useState<SavedAccount[]>(() => savedAccounts.list());

  function syncAccounts() {
    setAccounts(savedAccounts.list());
  }

  function rememberCurrent(me: Me) {
    if (tokens.access && tokens.refresh) {
      savedAccounts.upsert({
        username: me.username,
        display_name: me.display_name || me.username,
        access: tokens.access,
        refresh: tokens.refresh,
      });
      syncAccounts();
    }
  }

  async function refreshMe() {
    if (!tokens.access) {
      setUser(null);
      return;
    }
    try {
      const me = await authApi.me();
      setUser(me);
      rememberCurrent(me);
    } catch {
      setUser(null);
    }
  }

  useEffect(() => {
    refreshMe().finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function login(email: string, password: string) {
    await authApi.login(email, password);
    await refreshMe();
  }

  function logout() {
    authApi.logout();
    setUser(null);
    // Saved accounts are kept so the user can switch back or re-add quickly.
  }

  async function switchAccount(username: string) {
    const acc = savedAccounts.list().find((a) => a.username === username);
    if (!acc) return;
    tokens.set(acc.access, acc.refresh);
    setLoading(true);
    await refreshMe();
    setLoading(false);
  }

  function removeAccount(username: string) {
    savedAccounts.remove(username);
    syncAccounts();
    if (user?.username === username) logout();
  }

  return (
    <AuthContext.Provider
      value={{ user, loading, login, logout, refreshMe, accounts, switchAccount, removeAccount }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
