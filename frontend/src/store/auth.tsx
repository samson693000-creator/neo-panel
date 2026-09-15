import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { api, tokenStore } from "../api/client";

interface Me {
  username: string;
  role: string;
}

interface TokenPayload {
  access_token: string;
  username: string;
  role: string;
}

interface AuthValue {
  me: Me | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  updateAccount: (
    oldPassword: string,
    newUsername: string,
    newPassword: string,
  ) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthValue>({} as AuthValue);

function applyToken(res: TokenPayload, setMe: (me: Me) => void) {
  tokenStore.set(res.access_token);
  setMe({ username: res.username, role: res.role });
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [me, setMe] = useState<Me | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!tokenStore.get()) {
      setLoading(false);
      return;
    }
    api
      .get<Me>("/api/auth/me")
      .then(setMe)
      .catch(() => tokenStore.clear())
      .finally(() => setLoading(false));
  }, []);

  const value = useMemo<AuthValue>(
    () => ({
      me,
      loading,
      login: async (username, password) => {
        const res = await api.post<TokenPayload>("/api/auth/login", {
          username,
          password,
        });
        applyToken(res, setMe);
      },
      updateAccount: async (oldPassword, newUsername, newPassword) => {
        const res = await api.post<TokenPayload>("/api/auth/account", {
          old_password: oldPassword,
          new_username: newUsername || null,
          new_password: newPassword || null,
        });
        applyToken(res, setMe);
      },
      logout: () => {
        tokenStore.clear();
        setMe(null);
      },
    }),
    [me, loading],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export const useAuth = () => useContext(AuthContext);
