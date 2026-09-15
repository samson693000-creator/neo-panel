import { useEffect, useState } from "react";
import { api, type PaymentList } from "../api/client";
import { Card, Spinner, Stat, fmtDate, useToast } from "../components/ui";

const FILTERS = [
  { key: "all", label: "Все" },
  { key: "pending", label: "Ожидают" },
  { key: "paid", label: "Оплачены" },
  { key: "expired", label: "Истекли" },
  { key: "cancelled", label: "Отменены" },
];

const STATUS_CLASS: Record<string, string> = {
  paid: "badge-ok",
  pending: "badge-warn",
  expired: "badge-off",
  failed: "badge-off",
  cancelled: "badge-off",
};

export default function PaymentsPage() {
  const toast = useToast();
  const [data, setData] = useState<PaymentList | null>(null);
  const [status, setStatus] = useState("all");
  const [page, setPage] = useState(1);
  const [busy, setBusy] = useState(false);

  const load = async () => {
    try {
      setData(
        await api.get<PaymentList>(
          `/api/payments?status=${status}&page=${page}&per_page=25`,
        ),
      );
    } catch (err) {
      toast(err instanceof Error ? err.message : "Ошибка", "err");
    }
  };

  useEffect(() => {
    load();
  }, [status, page]);

  const action = async (id: number, path: string, ok: string) => {
    setBusy(true);
    try {
      const res = await api.post<{ ok: boolean; message?: string }>(
        `/api/payments/${id}/${path}`,
      );
      toast(res.message || ok, res.ok ? "ok" : "err");
      await load();
    } catch (err) {
      toast(err instanceof Error ? err.message : "Ошибка", "err");
    } finally {
      setBusy(false);
    }
  };

  if (!data) return <Spinner />;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-lg tracking-[0.2em] text-matrix-green">ПЛАТЕЖИ</h1>
        <p className="mt-1 text-xs text-matrix-dim">
          счета USDT и BTC, автоактивация тарифов
        </p>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4">
        <Stat
          label="Доход"
          value={data.revenue.toFixed(2)}
          hint="оплаченные счета"
        />
        <Stat
          label="Ожидают оплаты"
          value={data.pending}
          tone={data.pending ? "amber" : "green"}
        />
        <Stat label="Всего счетов" value={data.total} />
        <Stat label="Страниц" value={data.pages} />
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
        <button className="btn-ghost" onClick={load}>
          Обновить
        </button>
      </div>

      <Card>
        <div className="table-wrap">
          <table className="tbl">
            <thead>
              <tr>
                <th>Создан</th>
                <th>Клиент</th>
                <th>Тариф</th>
                <th>Сумма</th>
                <th>Счёт</th>
                <th>Статус</th>
                <th>Действия</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((p) => (
                <tr key={p.id}>
                  <td className="text-matrix-dim">{fmtDate(p.created_at)}</td>
                  <td>{p.username ? `@${p.username}` : p.telegram_id}</td>
                  <td>{p.tariff}</td>
                  <td className="whitespace-nowrap">
                    {p.amount} {p.asset}
                    {p.network && (
                      <span className="ml-1 text-[11px] text-matrix-dim">
                        {p.network}
                      </span>
                    )}
                  </td>
                  <td className="max-w-[160px] truncate text-matrix-dim">
                    {p.invoice_id}
                    <div className="text-[10px]">{p.provider}</div>
                  </td>
                  <td>
                    <span className={STATUS_CLASS[p.status] ?? "badge-warn"}>
                      {p.status}
                    </span>
                    {p.paid_at && (
                      <div className="mt-1 text-[10px] text-matrix-dim">
                        {fmtDate(p.paid_at)}
                      </div>
                    )}
                  </td>
                  <td>
                    {p.status === "pending" ? (
                      <div className="flex flex-wrap gap-1">
                        <button
                          className="btn-ghost px-2 py-1 text-xs"
                          disabled={busy}
                          onClick={() => action(p.id, "recheck", "Проверено")}
                        >
                          Проверить
                        </button>
                        <button
                          className="btn-primary px-2 py-1 text-xs"
                          disabled={busy}
                          onClick={() => action(p.id, "confirm", "Активировано")}
                        >
                          Зачислить
                        </button>
                        <button
                          className="btn-danger px-2 py-1 text-xs"
                          disabled={busy}
                          onClick={() => action(p.id, "cancel", "Отменено")}
                        >
                          Отмена
                        </button>
                      </div>
                    ) : (
                      <span className="text-xs text-matrix-dim">-</span>
                    )}
                  </td>
                </tr>
              ))}
              {data.items.length === 0 && (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-matrix-dim">
                    Платежей пока нет
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {data.pages > 1 && (
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
      </Card>
    </div>
  );
}
