import { useEffect, useState } from "react";
import {
  api,
  type BotState,
  type Dashboard,
  type RequestRow,
} from "../api/client";
import { Card, Spinner, Stat, fmtDate, useToast } from "../components/ui";

export default function DashboardPage() {
  const toast = useToast();
  const [data, setData] = useState<Dashboard | null>(null);
  const [rows, setRows] = useState<RequestRow[]>([]);
  const [bot, setBot] = useState<BotState | null>(null);
  const [busy, setBusy] = useState(false);

  const load = async () => {
    try {
      const [d, r, b] = await Promise.all([
        api.get<Dashboard>("/api/stats/dashboard"),
        api.get<RequestRow[]>("/api/stats/requests?limit=15"),
        api.get<BotState>("/api/settings/bot/status").catch(() => null),
      ]);
      setData(d);
      setRows(r);
      setBot(b);
    } catch (err) {
      toast(err instanceof Error ? err.message : "Ошибка загрузки", "err");
    }
  };

  useEffect(() => {
    load();
    const id = setInterval(load, 20000);
    return () => clearInterval(id);
  }, []);

  const botAction = async (action: "start" | "stop" | "restart") => {
    setBusy(true);
    try {
      const res = await api.post<{ ok: boolean; message: string }>(
        `/api/settings/bot/${action}`,
      );
      toast(res.message, res.ok ? "ok" : "err");
      await load();
    } catch (err) {
      toast(err instanceof Error ? err.message : "Ошибка", "err");
    } finally {
      setBusy(false);
    }
  };

  if (!data) return <Spinner text="Сбор данных" />;

  const running = data.bot_status === "running";

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-lg tracking-[0.2em] text-matrix-green">ДАШБОРД</h1>
        <p className="mt-1 text-xs text-matrix-dim">
          состояние системы обновляется автоматически
        </p>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4">
        <Stat
          label="Пользователи"
          value={data.users_total}
          hint={`+${data.users_today} сегодня`}
        />
        <Stat label="Активные 7 дней" value={data.users_active_7d} />
        <Stat
          label="Запросов всего"
          value={data.requests_total}
          hint={`+${data.requests_today} сегодня`}
        />
        <Stat label="Платных клиентов" value={data.paid_users} />
        <Stat
          label="Заблокированы"
          value={data.blocked}
          tone={data.blocked ? "red" : "green"}
        />
        <Stat
          label="Доход"
          value={data.revenue_total.toFixed(2)}
          hint="сумма оплат"
        />
        <Stat
          label="ИИ"
          value={data.ai_configured ? "подключён" : "не задан"}
          tone={data.ai_configured ? "green" : "amber"}
        />
        <Stat
          label="Платежи"
          value={data.payments_configured ? "готовы" : "не заданы"}
          tone={data.payments_configured ? "green" : "amber"}
        />
      </div>

      <Card title="Telegram-бот">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="text-sm">
            <div className="flex items-center gap-2">
              <span className={running ? "badge-ok" : "badge-off"}>
                {running ? "RUNNING" : data.bot_status.toUpperCase()}
              </span>
              {data.bot_username && (
                <span className="text-matrix-dim">@{data.bot_username}</span>
              )}
            </div>
            {bot?.error && (
              <p className="mt-2 text-xs text-matrix-red">{bot.error}</p>
            )}
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              className="btn-primary"
              disabled={busy || running}
              onClick={() => botAction("start")}
            >
              Запустить
            </button>
            <button
              className="btn-ghost"
              disabled={busy}
              onClick={() => botAction("restart")}
            >
              Перезапустить
            </button>
            <button
              className="btn-danger"
              disabled={busy || !running}
              onClick={() => botAction("stop")}
            >
              Остановить
            </button>
          </div>
        </div>
      </Card>

      <Card title="Последние запросы">
        {rows.length === 0 ? (
          <p className="py-6 text-center text-sm text-matrix-dim">
            Запросов пока нет
          </p>
        ) : (
          <div className="table-wrap">
            <table className="tbl">
              <thead>
                <tr>
                  <th>Время</th>
                  <th>Пользователь</th>
                  <th>Запрос</th>
                  <th>Источник</th>
                  <th>Токены</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.id}>
                    <td className="text-matrix-dim">{fmtDate(r.created_at)}</td>
                    <td>{r.username ? `@${r.username}` : r.telegram_id}</td>
                    <td className="max-w-[320px] truncate">{r.prompt}</td>
                    <td>
                      <span className={r.is_error ? "badge-off" : "badge-ok"}>
                        {r.is_error ? "error" : r.source}
                      </span>
                    </td>
                    <td>{r.tokens}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
