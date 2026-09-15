import { useEffect, useState } from "react";
import { api, type BotUser, type UserList } from "../api/client";
import {
  Card,
  Field,
  Modal,
  Spinner,
  fmtDate,
  useToast,
} from "../components/ui";

const FILTERS = [
  { key: "all", label: "Все" },
  { key: "paid", label: "Платные" },
  { key: "free", label: "Бесплатные" },
  { key: "blocked", label: "Блок" },
];

export default function UsersPage() {
  const toast = useToast();
  const [data, setData] = useState<UserList | null>(null);
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("all");
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);

  const [grantUser, setGrantUser] = useState<BotUser | null>(null);
  const [grantForm, setGrantForm] = useState({ requests: 0, days: 0, note: "" });
  const [detail, setDetail] = useState<{ user: BotUser; history: any[] } | null>(
    null,
  );

  const load = async () => {
    setLoading(true);
    try {
      const res = await api.get<UserList>(
        `/api/users?q=${encodeURIComponent(q)}&status=${status}&page=${page}&per_page=25`,
      );
      setData(res);
    } catch (err) {
      toast(err instanceof Error ? err.message : "Ошибка", "err");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [status, page]);

  useEffect(() => {
    const id = setTimeout(() => {
      setPage(1);
      load();
    }, 400);
    return () => clearTimeout(id);
  }, [q]);

  const toggleBlock = async (user: BotUser) => {
    try {
      await api.post(`/api/users/${user.id}/block`);
      toast(user.is_blocked ? "Разблокирован" : "Заблокирован");
      load();
    } catch (err) {
      toast(err instanceof Error ? err.message : "Ошибка", "err");
    }
  };

  const resetFree = async (user: BotUser) => {
    try {
      await api.post(`/api/users/${user.id}/reset-free`);
      toast("Бесплатные запросы сброшены");
      load();
    } catch (err) {
      toast(err instanceof Error ? err.message : "Ошибка", "err");
    }
  };

  const submitGrant = async () => {
    if (!grantUser) return;
    try {
      await api.post(`/api/users/${grantUser.id}/grant`, grantForm);
      toast("Изменения сохранены");
      setGrantUser(null);
      setGrantForm({ requests: 0, days: 0, note: "" });
      load();
    } catch (err) {
      toast(err instanceof Error ? err.message : "Ошибка", "err");
    }
  };

  const openDetail = async (user: BotUser) => {
    try {
      const res = await api.get<{ user: BotUser; history: any[] }>(
        `/api/users/${user.id}`,
      );
      setDetail(res);
    } catch (err) {
      toast(err instanceof Error ? err.message : "Ошибка", "err");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-lg tracking-[0.2em] text-matrix-green">
            ПОЛЬЗОВАТЕЛИ
          </h1>
          <p className="mt-1 text-xs text-matrix-dim">
            всего: {data?.total ?? 0}
          </p>
        </div>
        <input
          className="input sm:max-w-xs"
          placeholder="Поиск: ID, username, имя"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
      </div>

      <div className="flex flex-wrap gap-2">
        {FILTERS.map((f) => (
          <button
            key={f.key}
            className={f.key === status ? "btn-primary" : "btn-ghost"}
            onClick={() => {
              setStatus(f.key);
              setPage(1);
            }}
          >
            {f.label}
          </button>
        ))}
      </div>

      <Card>
        {loading && !data ? (
          <Spinner />
        ) : (
          <>
            <div className="table-wrap">
              <table className="tbl">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Пользователь</th>
                    <th>Бесплатно</th>
                    <th>Платно</th>
                    <th>Всего</th>
                    <th>Статус</th>
                    <th>Активность</th>
                    <th>Действия</th>
                  </tr>
                </thead>
                <tbody>
                  {data?.items.map((u) => (
                    <tr key={u.id}>
                      <td className="text-matrix-dim">{u.telegram_id}</td>
                      <td>
                        <button
                          className="text-matrix-green hover:underline"
                          onClick={() => openDetail(u)}
                        >
                          {u.username ? `@${u.username}` : u.first_name || "-"}
                        </button>
                      </td>
                      <td>{u.free_used}</td>
                      <td>{u.is_unlimited ? "unlim" : u.paid_requests}</td>
                      <td>{u.total_requests}</td>
                      <td>
                        {u.is_blocked ? (
                          <span className="badge-off">блок</span>
                        ) : u.is_unlimited ? (
                          <span className="badge-ok">безлимит</span>
                        ) : u.paid_requests > 0 ? (
                          <span className="badge-ok">платный</span>
                        ) : (
                          <span className="badge-warn">free</span>
                        )}
                      </td>
                      <td className="text-matrix-dim">{fmtDate(u.last_seen)}</td>
                      <td>
                        <div className="flex flex-wrap gap-1">
                          <button
                            className="btn-ghost px-2 py-1 text-xs"
                            onClick={() => setGrantUser(u)}
                          >
                            Выдать
                          </button>
                          <button
                            className="btn-ghost px-2 py-1 text-xs"
                            onClick={() => resetFree(u)}
                          >
                            Сброс
                          </button>
                          <button
                            className={`px-2 py-1 text-xs ${
                              u.is_blocked ? "btn-primary" : "btn-danger"
                            }`}
                            onClick={() => toggleBlock(u)}
                          >
                            {u.is_blocked ? "Разбл." : "Блок"}
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                  {data?.items.length === 0 && (
                    <tr>
                      <td colSpan={8} className="py-8 text-center text-matrix-dim">
                        Ничего не найдено
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            {data && data.pages > 1 && (
              <div className="mt-4 flex items-center justify-between text-sm">
                <button
                  className="btn-ghost"
                  disabled={page <= 1}
                  onClick={() => setPage((p) => p - 1)}
                >
                  Назад
                </button>
                <span className="text-matrix-dim">
                  {data.page} / {data.pages}
                </span>
                <button
                  className="btn-ghost"
                  disabled={page >= data.pages}
                  onClick={() => setPage((p) => p + 1)}
                >
                  Вперёд
                </button>
              </div>
            )}
          </>
        )}
      </Card>

      <Modal
        open={!!grantUser}
        title={`Выдать доступ — ${grantUser?.telegram_id ?? ""}`}
        onClose={() => setGrantUser(null)}
      >
        <div className="space-y-4">
          <Field label="Добавить запросов" hint="Отрицательное число списывает">
            <input
              className="input"
              type="number"
              value={grantForm.requests}
              onChange={(e) =>
                setGrantForm({ ...grantForm, requests: Number(e.target.value) })
              }
            />
          </Field>
          <Field label="Дней безлимита" hint="0 — не менять срок">
            <input
              className="input"
              type="number"
              value={grantForm.days}
              onChange={(e) =>
                setGrantForm({ ...grantForm, days: Number(e.target.value) })
              }
            />
          </Field>
          <Field label="Заметка администратора">
            <input
              className="input"
              value={grantForm.note}
              onChange={(e) =>
                setGrantForm({ ...grantForm, note: e.target.value })
              }
            />
          </Field>
          <div className="flex flex-wrap gap-2">
            <button className="btn-primary" onClick={submitGrant}>
              Применить
            </button>
            <button
              className="btn-ghost"
              onClick={async () => {
                if (!grantUser) return;
                await api.post(`/api/users/${grantUser.id}/grant`, {
                  unlimited: !grantUser.is_unlimited,
                });
                toast("Безлимит переключён");
                setGrantUser(null);
                load();
              }}
            >
              {grantUser?.is_unlimited ? "Снять безлимит" : "Включить безлимит"}
            </button>
          </div>
        </div>
      </Modal>

      <Modal
        open={!!detail}
        wide
        title={`Профиль — ${detail?.user.telegram_id ?? ""}`}
        onClose={() => setDetail(null)}
      >
        {detail && (
          <div className="space-y-5">
            <div className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-3">
              <div>
                <div className="label">Username</div>
                {detail.user.username ? `@${detail.user.username}` : "-"}
              </div>
              <div>
                <div className="label">Имя</div>
                {detail.user.first_name || "-"}
              </div>
              <div>
                <div className="label">Регистрация</div>
                {fmtDate(detail.user.created_at)}
              </div>
              <div>
                <div className="label">Бесплатных использовано</div>
                {detail.user.free_used}
              </div>
              <div>
                <div className="label">Платных осталось</div>
                {detail.user.is_unlimited ? "unlim" : detail.user.paid_requests}
              </div>
              <div>
                <div className="label">Тариф до</div>
                {fmtDate(detail.user.tariff_expires_at)}
              </div>
            </div>

            {detail.user.note && (
              <div className="panel p-3 text-sm">
                <div className="label">Заметка</div>
                {detail.user.note}
              </div>
            )}

            <div>
              <div className="label">История запросов</div>
              <div className="max-h-72 space-y-2 overflow-y-auto pr-1">
                {detail.history.length === 0 && (
                  <p className="text-sm text-matrix-dim">Пусто</p>
                )}
                {detail.history.map((h) => (
                  <div key={h.id} className="panel p-3 text-xs">
                    <div className="mb-1 flex justify-between text-matrix-dim">
                      <span>{fmtDate(h.created_at)}</span>
                      <span className={h.is_error ? "text-matrix-red" : ""}>
                        {h.is_error ? "error" : `${h.source} · ${h.tokens} tok`}
                      </span>
                    </div>
                    <div className="text-matrix-green">&gt; {h.prompt}</div>
                    <div className="mt-1 text-matrix-dim">&lt; {h.answer}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
