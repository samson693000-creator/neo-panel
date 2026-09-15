import { useEffect, useState } from "react";
import { api, type LogRow } from "../api/client";
import { Card, Spinner, fmtDate, useToast } from "../components/ui";

export default function LogsPage() {
  const toast = useToast();
  const [rows, setRows] = useState<LogRow[] | null>(null);

  useEffect(() => {
    api
      .get<LogRow[]>("/api/stats/logs?limit=200")
      .then(setRows)
      .catch((err) =>
        toast(err instanceof Error ? err.message : "Ошибка", "err"),
      );
  }, []);

  if (!rows) return <Spinner />;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-lg tracking-[0.2em] text-matrix-green">ЖУРНАЛ</h1>
        <p className="mt-1 text-xs text-matrix-dim">
          действия администраторов
        </p>
      </div>

      <Card>
        <div className="table-wrap">
          <table className="tbl">
            <thead>
              <tr>
                <th>Время</th>
                <th>Админ</th>
                <th>Действие</th>
                <th>Объект</th>
                <th>Детали</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id}>
                  <td className="text-matrix-dim">{fmtDate(r.created_at)}</td>
                  <td>{r.admin}</td>
                  <td>
                    <span className="badge-ok">{r.action}</span>
                  </td>
                  <td>{r.entity}</td>
                  <td className="max-w-[380px] truncate text-matrix-dim">
                    {r.details}
                  </td>
                </tr>
              ))}
              {rows.length === 0 && (
                <tr>
                  <td colSpan={5} className="py-8 text-center text-matrix-dim">
                    Записей пока нет
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
