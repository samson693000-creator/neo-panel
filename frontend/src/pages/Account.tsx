import { useState } from "react";
import { Card, Field, useToast } from "../components/ui";
import { useAuth } from "../store/auth";

export default function AccountPage() {
  const { me, updateAccount } = useAuth();
  const toast = useToast();
  const [oldPassword, setOldPassword] = useState("");
  const [newUsername, setNewUsername] = useState(me?.username || "");
  const [newPassword, setNewPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    const usernameChanged = newUsername.trim() !== (me?.username || "");
    if (!oldPassword) {
      toast("Введите текущий пароль", "err");
      return;
    }
    if (!usernameChanged && !newPassword) {
      toast("Укажите новый логин или пароль", "err");
      return;
    }
    if (newPassword && newPassword.length < 8) {
      toast("Новый пароль — минимум 8 символов", "err");
      return;
    }
    if (newPassword && newPassword !== confirm) {
      toast("Пароли не совпадают", "err");
      return;
    }
    setBusy(true);
    try {
      await updateAccount(
        oldPassword,
        usernameChanged ? newUsername.trim() : "",
        newPassword,
      );
      toast("Данные входа обновлены");
      setOldPassword("");
      setNewPassword("");
      setConfirm("");
    } catch (err) {
      toast(err instanceof Error ? err.message : "Ошибка", "err");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-lg tracking-[0.2em] text-matrix-green">АККАУНТ</h1>
        <p className="mt-1 text-xs text-matrix-dim">
          смена логина и пароля для входа в панель
        </p>
      </div>

      <Card title="Данные входа" className="max-w-md">
        <div className="space-y-4">
          <p className="text-xs text-matrix-dim">
            Сейчас: <span className="text-matrix-green">{me?.username}</span> /{" "}
            {me?.role}
          </p>
          <Field label="Новый логин" hint="минимум 3 символа, можно оставить как есть">
            <input
              className="input"
              value={newUsername}
              autoComplete="username"
              onChange={(e) => setNewUsername(e.target.value)}
            />
          </Field>
          <Field label="Текущий пароль">
            <input
              className="input"
              type="password"
              autoComplete="current-password"
              value={oldPassword}
              onChange={(e) => setOldPassword(e.target.value)}
            />
          </Field>
          <Field label="Новый пароль" hint="оставьте пустым, если меняете только логин">
            <input
              className="input"
              type="password"
              autoComplete="new-password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
            />
          </Field>
          <Field label="Повтор нового пароля">
            <input
              className="input"
              type="password"
              autoComplete="new-password"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
            />
          </Field>
          <button className="btn-primary w-full" disabled={busy} onClick={submit}>
            {busy ? "Сохранение..." : "Сохранить"}
          </button>
        </div>
      </Card>
    </div>
  );
}
