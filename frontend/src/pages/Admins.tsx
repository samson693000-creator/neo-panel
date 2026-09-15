import { useEffect, useState } from "react";
import { api, downloadAuth } from "../api/client";
import {
  Card,
  Field,
  Modal,
  Spinner,
  fmtDate,
  useToast,
} from "../components/ui";

interface AdminRow {
  id: number;
  username: string;
  role: string;
  is_active: boolean;
  created_at: string;
  last_login: string | null;
}

const ROLES = [
  { key: "owner", label: "owner - полный доступ" },
  { key: "admin", label: "admin - настройки и клиенты" },
  { key: "support", label: "support - только просмотр" },
];

export default function AdminsPage() {
  const toast = useToast();
  const [items, setItems] = useState<AdminRow[] | null>(null);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({
    username: "",
    password: "",
    role: "support",
  });

  const load = async () => {
    try {
      setItems(await api.get<AdminRow[]>("/api/admins"));
    } catch (err) {
      toast(err instanceof Error ? err.message : "Нет доступа", "err");
      setItems([]);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const create = async () => {
    try {
      await api.post("/api/admins", form);
      toast("Администратор создан");
      setOpen(false);
      setForm({ username: "", password: "", role: "support" });
      load();
    } catch (err) {
      toast(err instanceof Error ? err.message : "Ошибка", "err");
    }
  };

  const update = async (id: number, payload: object) => {
    try {
      await api.put(`/api/admins/${id}`, payload);
      toast("Сохранено");
      load();
    } catch (err) {
      toast(err instanceof Error ? err.message : "Ошибка", "err");
    }
  };

  const remove = async (row: AdminRow) => {
    if (!confirm(`Удалить ${row.username}?`)) return;
    try {
      await api.del(`/api/admins/${row.id}`);
      toast("Удалён");
      load();
    } catch (err) {
      toast(err instanceof Error ? err.message : "Ошибка", "err");
    }
  };

  const downloadBackup = async () => {
    try {
      await downloadAuth("/api/backup/download", "backup.db");
      toast("Бэкап скачан");
    } catch (err) {
      toast(err instanceof Error ? err.message : "Ошибка", "err");
    }
  };

  if (!items) return <Spinner />;

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-lg tracking-[0.2em] text-matrix-green">
            АДМИНИСТРАТОРЫ
          </h1>
          <p className="mt-1 text-xs text-matrix-dim">роли и доступы</p>
        </div>
        <button className="btn-primary" onClick={() => setOpen(true)}>
          + Добавить
        </button>
      </div>

      <Card>
        <div className="table-wrap">
          <table className="tbl">
            <thead>
              <tr>
                <th>Логин</th>
                <th>Роль</th>
                <th>Статус</th>
                <th>Создан</th>
                <th>Последний вход</th>
                <th>Действия</th>
              </tr>
            </thead>
            <tbody>
              {items.map((a) => (
                <tr key={a.id}>
                  <td className="text-matrix-green">{a.username}</td>
                  <td>
                    <select
                      className="input py-1 text-xs"
                      value={a.role}
                      onChange={(e) => update(a.id, { role: e.target.value })}
                    >
                      {ROLES.map((r) => (
                        <option key={r.key} value={r.key}>
                          {r.key}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td>
                    <span className={a.is_active ? "badge-ok" : "badge-off"}>
                      {a.is_active ? "активен" : "отключён"}
                    </span>
                  </td>
                  <td className="text-matrix-dim">{fmtDate(a.created_at)}</td>
                  <td className="text-matrix-dim">{fmtDate(a.last_login)}</td>
                  <td>
                    <div className="flex flex-wrap gap-1">
                      <button
                        className="btn-ghost px-2 py-1 text-xs"
                        onClick={() => update(a.id, { is_active: !a.is_active })}
                      >
                        {a.is_active ? "Отключить" : "Включить"}
                      </button>
                      <button
                        className="btn-danger px-2 py-1 text-xs"
                        onClick={() => remove(a)}
                      >
                        Удалить
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <Card title="Резервная копия базы" className="max-w-md">
        <p className="mb-3 text-xs text-matrix-dim">
          SQLite: файл .db. PostgreSQL: дамп .sql. Логин и пароль меняются в
          разделе «Аккаунт».
        </p>
        <button className="btn-ghost" onClick={downloadBackup}>
          Скачать бэкап
        </button>
      </Card>

      <Modal
        open={open}
        title="Новый администратор"
        onClose={() => setOpen(false)}
      >
        <div className="space-y-4">
          <Field label="Логин">
            <input
              className="input"
              value={form.username}
              onChange={(e) => setForm({ ...form, username: e.target.value })}
            />
          </Field>
          <Field label="Пароль" hint="минимум 8 символов">
            <input
              className="input"
              type="password"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
            />
          </Field>
          <Field label="Роль">
            <select
              className="input"
              value={form.role}
              onChange={(e) => setForm({ ...form, role: e.target.value })}
            >
              {ROLES.map((r) => (
                <option key={r.key} value={r.key}>
                  {r.label}
                </option>
              ))}
            </select>
          </Field>
          <button className="btn-primary w-full" onClick={create}>
            Создать
          </button>
        </div>
      </Modal>
    </div>
  );
}
