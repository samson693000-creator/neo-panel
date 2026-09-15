import { useEffect, useState } from "react";
import { api, type Audience, type BroadcastRow } from "../api/client";
import { Card, Field, Spinner, fmtDate, useToast } from "../components/ui";

const STATUS_CLASS: Record<string, string> = {
  done: "badge-ok",
  running: "badge-warn",
  draft: "badge-warn",
  cancelled: "badge-off",
  error: "badge-off",
};

export default function BroadcastsPage() {
  const toast = useToast();
  const [audiences, setAudiences] = useState<Audience[] | null>(null);
  const [items, setItems] = useState<BroadcastRow[]>([]);
  const [text, setText] = useState("");
  const [audience, setAudience] = useState("all");
  const [busy, setBusy] = useState(false);

  const load = async () => {
    try {
      const [a, list] = await Promise.all([
        api.get<Audience[]>("/api/broadcasts/audiences"),
        api.get<BroadcastRow[]>("/api/broadcasts"),
      ]);
      setAudiences(a);
      setItems(list);
    } catch (err) {
      toast(err instanceof Error ? err.message : "Ошибка", "err");
    }
  };

  useEffect(() => {
    load();
    const id = setInterval(load, 5000);
    return () => clearInterval(id);
  }, []);

  const selected = audiences?.find((a) => a.key === audience);

  const send = async (sendNow: boolean) => {
    if (!text.trim()) {
      toast("Введите текст рассылки", "err");
      return;
    }
    if (
      sendNow &&
      !confirm(`Отправить сообщение ${selected?.count ?? 0} пользователям?`)
    ) {
      return;
    }
    setBusy(true);
    try {
      await api.post("/api/broadcasts", { text, audience, send_now: sendNow });
      toast(sendNow ? "Рассылка запущена" : "Черновик сохранён");
      setText("");
      await load();
    } catch (err) {
      toast(err instanceof Error ? err.message : "Ошибка", "err");
    } finally {
      setBusy(false);
    }
  };

  const control = async (id: number, path: string) => {
    try {
      const res = await api.post<{ message?: string }>(
        `/api/broadcasts/${id}/${path}`,
      );
      toast(res.message || "Готово");
      await load();
    } catch (err) {
      toast(err instanceof Error ? err.message : "Ошибка", "err");
    }
  };

  const remove = async (id: number) => {
    if (!confirm("Удалить запись рассылки?")) return;
    try {
      await api.del(`/api/broadcasts/${id}`);
      toast("Удалено");
      await load();
    } catch (err) {
      toast(err instanceof Error ? err.message : "Ошибка", "err");
    }
  };

  if (!audiences) return <Spinner />;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-lg tracking-[0.2em] text-matrix-green">РАССЫЛКИ</h1>
        <p className="mt-1 text-xs text-matrix-dim">
          сообщения пользователям бота, поддерживается HTML
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card title="Новая рассылка">
          <div className="space-y-4">
            <Field label="Аудитория">
              <select
                className="input"
                value={audience}
                onChange={(e) => setAudience(e.target.value)}
              >
                {audiences.map((a) => (
                  <option key={a.key} value={a.key}>
                    {a.label} - {a.count}
                  </option>
                ))}
              </select>
            </Field>

            <Field label="Текст сообщения" hint="Поддерживаются HTML-теги">
              <textarea
                className="input min-h-[180px]"
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder="Привет! У нас обновление..."
              />
            </Field>

            <div className="panel p-3 text-xs text-matrix-dim">
              Получателей:{" "}
              <span className="text-matrix-green">{selected?.count ?? 0}</span>
              <br />
              Примерное время: ~
              {Math.ceil(((selected?.count ?? 0) * 0.06) / 60)} мин.
            </div>

            <div className="flex flex-wrap gap-2">
              <button
                className="btn-primary"
                disabled={busy}
                onClick={() => send(true)}
              >
                Отправить сейчас
              </button>
              <button
                className="btn-ghost"
                disabled={busy}
                onClick={() => send(false)}
              >
                Сохранить черновик
              </button>
            </div>
          </div>
        </Card>

        <Card title="Предпросмотр">
          <div className="panel bg-black/40 p-4">
            {text ? (
              <div
                className="whitespace-pre-wrap break-words text-sm text-matrix-green"
                dangerouslySetInnerHTML={{ __html: text }}
              />
            ) : (
              <p className="text-sm text-matrix-dim">
                Здесь появится текст сообщения так, как его увидит пользователь.
              </p>
            )}
          </div>
        </Card>
      </div>

      <Card title="История рассылок">
        <div className="table-wrap">
          <table className="tbl">
            <thead>
              <tr>
                <th>Создана</th>
                <th>Аудитория</th>
                <th>Прогресс</th>
                <th>Ошибки</th>
                <th>Статус</th>
                <th>Действия</th>
              </tr>
            </thead>
            <tbody>
              {items.map((b) => {
                const percent = b.total
                  ? Math.round(((b.sent + b.failed) / b.total) * 100)
                  : 0;
                return (
                  <tr key={b.id}>
                    <td className="text-matrix-dim">{fmtDate(b.created_at)}</td>
                    <td>{b.audience_label}</td>
                    <td className="min-w-[160px]">
                      <div className="mb-1 text-xs">
                        {b.sent} / {b.total}
                      </div>
                      <div className="h-1.5 w-full rounded bg-black/60">
                        <div
                          className="h-1.5 rounded bg-matrix-green transition-all"
                          style={{ width: `${percent}%` }}
                        />
                      </div>
                    </td>
                    <td className={b.failed ? "text-matrix-red" : ""}>
                      {b.failed}
                    </td>
                    <td>
                      <span className={STATUS_CLASS[b.status] ?? "badge-warn"}>
                        {b.status}
                      </span>
                    </td>
                    <td>
                      <div className="flex flex-wrap gap-1">
                        {b.running ? (
                          <button
                            className="btn-danger px-2 py-1 text-xs"
                            onClick={() => control(b.id, "cancel")}
                          >
                            Стоп
                          </button>
                        ) : (
                          <>
                            <button
                              className="btn-ghost px-2 py-1 text-xs"
                              onClick={() => control(b.id, "start")}
                            >
                              Запустить
                            </button>
                            <button
                              className="btn-danger px-2 py-1 text-xs"
                              onClick={() => remove(b.id)}
                            >
                              Удалить
                            </button>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
              {items.length === 0 && (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-matrix-dim">
                    Рассылок пока не было
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
