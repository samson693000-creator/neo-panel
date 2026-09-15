import { useEffect, useState } from "react";
import { api, type Tariff } from "../api/client";
import { Card, Field, Modal, Spinner, Toggle, useToast } from "../components/ui";

const EMPTY: Omit<Tariff, "id"> = {
  name: "",
  description: "",
  price: 0,
  currency: "USDT",
  requests: 100,
  is_unlimited: false,
  duration_days: 0,
  is_active: true,
  sort_order: 0,
};

export default function TariffsPage() {
  const toast = useToast();
  const [items, setItems] = useState<Tariff[] | null>(null);
  const [open, setOpen] = useState(false);
  const [editId, setEditId] = useState<number | null>(null);
  const [form, setForm] = useState(EMPTY);

  const load = async () => {
    try {
      setItems(await api.get<Tariff[]>("/api/tariffs"));
    } catch (err) {
      toast(err instanceof Error ? err.message : "Ошибка", "err");
    }
  };

  useEffect(() => {
    load();
  }, []);

  const startCreate = () => {
    setEditId(null);
    setForm(EMPTY);
    setOpen(true);
  };

  const startEdit = (t: Tariff) => {
    const { id, ...rest } = t;
    setEditId(id);
    setForm(rest);
    setOpen(true);
  };

  const save = async () => {
    if (!form.name.trim()) {
      toast("Укажи название тарифа", "err");
      return;
    }
    try {
      if (editId) await api.put(`/api/tariffs/${editId}`, form);
      else await api.post("/api/tariffs", form);
      toast("Тариф сохранён");
      setOpen(false);
      load();
    } catch (err) {
      toast(err instanceof Error ? err.message : "Ошибка", "err");
    }
  };

  const remove = async (t: Tariff) => {
    if (!confirm(`Удалить тариф ${t.name}?`)) return;
    try {
      await api.del(`/api/tariffs/${t.id}`);
      toast("Тариф удалён");
      load();
    } catch (err) {
      toast(err instanceof Error ? err.message : "Ошибка", "err");
    }
  };

  if (!items) return <Spinner />;

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-lg tracking-[0.2em] text-matrix-green">ТАРИФЫ</h1>
          <p className="mt-1 text-xs text-matrix-dim">цены и лимиты для бота</p>
        </div>
        <button className="btn-primary" onClick={startCreate}>
          + Новый тариф
        </button>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {items.map((t) => (
          <Card key={t.id} className="flex flex-col justify-between">
            <div>
              <div className="flex items-start justify-between gap-2">
                <h3 className="text-base text-matrix-green">{t.name}</h3>
                <span className={t.is_active ? "badge-ok" : "badge-off"}>
                  {t.is_active ? "активен" : "выкл"}
                </span>
              </div>
              <p className="mt-2 min-h-[36px] text-xs text-matrix-dim">
                {t.description || "без описания"}
              </p>
              <div className="mt-3 space-y-1 text-sm">
                <div>
                  Цена:{" "}
                  <span className="text-matrix-green">
                    {Number(t.price)} {t.currency}
                  </span>
                </div>
                <div>
                  Лимит:{" "}
                  <span className="text-matrix-green">
                    {t.is_unlimited ? "безлимит" : `${t.requests} запросов`}
                  </span>
                </div>
                <div className="text-matrix-dim">
                  Срок: {t.duration_days ? `${t.duration_days} дн.` : "бессрочно"}
                </div>
              </div>
            </div>
            <div className="mt-4 flex gap-2">
              <button className="btn-ghost flex-1" onClick={() => startEdit(t)}>
                Изменить
              </button>
              <button className="btn-danger" onClick={() => remove(t)}>
                Удалить
              </button>
            </div>
          </Card>
        ))}
      </div>

      <Modal
        open={open}
        title={editId ? "Редактирование тарифа" : "Новый тариф"}
        onClose={() => setOpen(false)}
      >
        <div className="space-y-4">
          <Field label="Название">
            <input
              className="input"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
            />
          </Field>
          <Field label="Описание">
            <textarea
              className="input min-h-[70px]"
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
            />
          </Field>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Цена">
              <input
                className="input"
                type="number"
                step="0.01"
                value={form.price}
                onChange={(e) =>
                  setForm({ ...form, price: Number(e.target.value) })
                }
              />
            </Field>
            <Field label="Валюта">
              <select
                className="input"
                value={form.currency}
                onChange={(e) => setForm({ ...form, currency: e.target.value })}
              >
                <option value="USDT">USDT</option>
                <option value="BTC">BTC</option>
                <option value="USD">USD</option>
              </select>
            </Field>
            <Field label="Запросов">
              <input
                className="input"
                type="number"
                value={form.requests}
                onChange={(e) =>
                  setForm({ ...form, requests: Number(e.target.value) })
                }
              />
            </Field>
            <Field label="Срок, дней">
              <input
                className="input"
                type="number"
                value={form.duration_days}
                onChange={(e) =>
                  setForm({ ...form, duration_days: Number(e.target.value) })
                }
              />
            </Field>
            <Field label="Порядок">
              <input
                className="input"
                type="number"
                value={form.sort_order}
                onChange={(e) =>
                  setForm({ ...form, sort_order: Number(e.target.value) })
                }
              />
            </Field>
          </div>
          <div className="space-y-2">
            <Toggle
              checked={form.is_unlimited}
              onChange={(v) => setForm({ ...form, is_unlimited: v })}
              label="Безлимитный тариф"
            />
            <Toggle
              checked={form.is_active}
              onChange={(v) => setForm({ ...form, is_active: v })}
              label="Показывать в боте"
            />
          </div>
          <div className="flex gap-2">
            <button className="btn-primary flex-1" onClick={save}>
              Сохранить
            </button>
            <button className="btn-ghost" onClick={() => setOpen(false)}>
              Отмена
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
