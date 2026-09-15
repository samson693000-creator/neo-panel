import { useState, type FormEvent } from "react";
import MatrixRain from "../components/MatrixRain";
import { useAuth } from "../store/auth";

export default function Login() {
  const { login } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await login(username, password);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка входа");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden p-4">
      <div className="absolute inset-0">
        <MatrixRain opacity={0.25} />
      </div>

      <form onSubmit={submit} className="panel relative w-full max-w-md p-7">
        <div className="mb-6 text-center">
          <div className="text-2xl tracking-[0.35em] text-matrix-green animate-flicker">
            NEO PANEL
          </div>
          <p className="mt-2 text-xs text-matrix-dim">
            authorization required // ai bot control
          </p>
        </div>

        <div className="space-y-4">
          <div>
            <label className="label">Логин</label>
            <input
              className="input"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoFocus
              autoComplete="username"
            />
          </div>
          <div>
            <label className="label">Пароль</label>
            <input
              className="input"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
            />
          </div>
        </div>

        {error && (
          <div className="mt-4 rounded border border-matrix-red/50 bg-matrix-red/10 px-3 py-2 text-sm text-matrix-red">
            {error}
          </div>
        )}

        <button className="btn-primary mt-6 w-full" disabled={busy}>
          {busy ? "Проверка..." : "Войти в систему"}
        </button>

        <p className="mt-5 text-center text-[11px] text-matrix-dim">
          Логин и пароль выдаёт установщик. После входа их можно сменить в разделе «Аккаунт».
        </p>
      </form>
    </div>
  );
}
