import { useEffect, useState } from "react";
import { api, type SettingsPayload } from "../api/client";
import { Card, Field, Spinner, Toggle, useToast } from "../components/ui";

type Tab = "telegram" | "ai" | "limits" | "payments" | "texts";

const TABS: { key: Tab; label: string }[] = [
  { key: "telegram", label: "Telegram" },
  { key: "ai", label: "ИИ" },
  { key: "limits", label: "Лимиты" },
  { key: "payments", label: "Платежи" },
  { key: "texts", label: "Тексты" },
];

export default function SettingsPage() {
  const toast = useToast();
  const [data, setData] = useState<SettingsPayload | null>(null);
  const [values, setValues] = useState<Record<string, string>>({});
  const [tab, setTab] = useState<Tab>("telegram");
  const [busy, setBusy] = useState(false);

  const load = async () => {
    try {
      const res = await api.get<SettingsPayload>("/api/settings");
      setData(res);
      setValues(res.values);
    } catch (err) {
      toast(err instanceof Error ? err.message : "Ошибка", "err");
    }
  };

  useEffect(() => {
    load();
  }, []);

  const set = (key: string, value: string) =>
    setValues((prev) => ({ ...prev, [key]: value }));

  const bool = (key: string) =>
    (values[key] ?? "false").toLowerCase() === "true";

  const save = async () => {
    setBusy(true);
    try {
      const res = await api.put<{ values: Record<string, string> }>(
        "/api/settings",
        { values },
      );
      setValues(res.values);
      toast("Настройки сохранены");
      await load();
    } catch (err) {
      toast(err instanceof Error ? err.message : "Ошибка", "err");
    } finally {
      setBusy(false);
    }
  };

  const botAction = async (action: string) => {
    setBusy(true);
    try {
      const res = await api.post<{ ok: boolean; message: string }>(
        `/api/settings/bot/${action}`,
      );
      toast(res.message, res.ok ? "ok" : "err");
    } catch (err) {
      toast(err instanceof Error ? err.message : "Ошибка", "err");
    } finally {
      setBusy(false);
    }
  };

  const testAi = async () => {
    setBusy(true);
    try {
      const res = await api.post<{ ok: boolean; message: string }>(
        "/api/settings/ai/test",
      );
      toast(res.message, res.ok ? "ok" : "err");
    } catch (err) {
      toast(err instanceof Error ? err.message : "Ошибка", "err");
    } finally {
      setBusy(false);
    }
  };

  const yoomoneyAction = async (path: string) => {
    setBusy(true);
    try {
      const res = await api.post<{
        ok?: boolean;
        message?: string;
        payment_url?: string;
        order_id?: string;
        account?: string;
        activated?: number;
      }>(`/api/payments/yoomoney/${path}`);
      const extra = res.payment_url
        ? ` Заказ ${res.order_id || ""}`
        : res.account
          ? ` Счёт ${res.account}`
          : "";
      toast((res.message || "Готово") + extra, res.ok === false ? "err" : "ok");
    } catch (err) {
      toast(err instanceof Error ? err.message : "Ошибка", "err");
    } finally {
      setBusy(false);
    }
  };

  if (!data) return <Spinner />;

  const secretHint = (key: string) =>
    data.secret_filled[key]
      ? "Значение сохранено. Оставь как есть или введи новое."
      : "Значение ещё не задано.";

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-lg tracking-[0.2em] text-matrix-green">
            НАСТРОЙКИ
          </h1>
          <p className="mt-1 text-xs text-matrix-dim">
            ключи хранятся в зашифрованном виде
          </p>
        </div>
        <button className="btn-primary" onClick={save} disabled={busy}>
          Сохранить всё
        </button>
      </div>

      <div className="flex flex-wrap gap-2">
        {TABS.map((t) => (
          <button
            key={t.key}
            className={t.key === tab ? "btn-primary" : "btn-ghost"}
            onClick={() => setTab(t.key)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "telegram" && (
        <Card title="Telegram-бот">
          <div className="space-y-4">
            <Field label="Bot token" hint={secretHint("telegram_token")}>
              <input
                className="input"
                value={values.telegram_token ?? ""}
                onChange={(e) => set("telegram_token", e.target.value)}
                placeholder="123456789:AA..."
              />
            </Field>
            <Field label="Название бота">
              <input
                className="input"
                value={values.bot_name ?? ""}
                onChange={(e) => set("bot_name", e.target.value)}
              />
            </Field>
            <Field label="Ссылка на поддержку">
              <input
                className="input"
                value={values.support_url ?? ""}
                onChange={(e) => set("support_url", e.target.value)}
                placeholder="https://t.me/username"
              />
            </Field>
            <Toggle
              checked={bool("bot_enabled")}
              onChange={(v) => set("bot_enabled", String(v))}
              label="Автозапуск бота при старте сервера"
            />
            <div className="flex flex-wrap gap-2 border-t border-matrix-border pt-4">
              <button
                className="btn-primary"
                disabled={busy}
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
                disabled={busy}
                onClick={() => botAction("stop")}
              >
                Остановить
              </button>
            </div>
            <p className="text-[11px] text-matrix-dim">
              После смены токена сохрани настройки и нажми Перезапустить.
            </p>
          </div>
        </Card>
      )}

      {tab === "ai" && (
        <Card title="ИИ-сервис">
          <div className="space-y-4">
            <Field label="Base URL" hint="OpenAI-совместимый эндпоинт">
              <input
                className="input"
                value={values.ai_base_url ?? ""}
                onChange={(e) => set("ai_base_url", e.target.value)}
              />
            </Field>
            <Field label="API key" hint={secretHint("ai_api_key")}>
              <input
                className="input"
                value={values.ai_api_key ?? ""}
                onChange={(e) => set("ai_api_key", e.target.value)}
              />
            </Field>
            <Field label="Модель">
              <input
                className="input"
                value={values.ai_model ?? ""}
                onChange={(e) => set("ai_model", e.target.value)}
              />
            </Field>
            <Field label="Системный промпт">
              <textarea
                className="input min-h-[110px]"
                value={values.ai_system_prompt ?? ""}
                onChange={(e) => set("ai_system_prompt", e.target.value)}
              />
            </Field>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
              <Field label="Max tokens">
                <input
                  className="input"
                  value={values.ai_max_tokens ?? ""}
                  onChange={(e) => set("ai_max_tokens", e.target.value)}
                />
              </Field>
              <Field label="Temperature">
                <input
                  className="input"
                  value={values.ai_temperature ?? ""}
                  onChange={(e) => set("ai_temperature", e.target.value)}
                />
              </Field>
              <Field label="Timeout, сек">
                <input
                  className="input"
                  value={values.ai_timeout ?? ""}
                  onChange={(e) => set("ai_timeout", e.target.value)}
                />
              </Field>
            </div>
            <button className="btn-ghost" onClick={testAi} disabled={busy}>
              Проверить подключение
            </button>
          </div>
        </Card>
      )}

      {tab === "limits" && (
        <Card title="Лимиты">
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Бесплатных запросов" hint="по умолчанию 2">
              <input
                className="input"
                value={values.free_requests ?? ""}
                onChange={(e) => set("free_requests", e.target.value)}
              />
            </Field>
            <Field label="Макс. длина запроса">
              <input
                className="input"
                value={values.max_prompt_length ?? ""}
                onChange={(e) => set("max_prompt_length", e.target.value)}
              />
            </Field>
          </div>
        </Card>
      )}

      {tab === "payments" && (
        <Card title="Криптоплатежи">
          <div className="space-y-4">
            <Field label="Провайдер">
              <select
                className="input"
                value={values.payment_provider ?? "test"}
                onChange={(e) => set("payment_provider", e.target.value)}
              >
                <option value="test">Тестовый режим</option>
                <option value="cryptopay">Crypto Pay API</option>
                <option value="cryptomus">Cryptomus</option>
              </select>
            </Field>
            <Field label="Crypto Pay token" hint={secretHint("cryptopay_token")}>
              <input
                className="input"
                value={values.cryptopay_token ?? ""}
                onChange={(e) => set("cryptopay_token", e.target.value)}
              />
            </Field>
            <Field
              label="Cryptomus API key"
              hint={secretHint("cryptomus_api_key")}
            >
              <input
                className="input"
                value={values.cryptomus_api_key ?? ""}
                onChange={(e) => set("cryptomus_api_key", e.target.value)}
              />
            </Field>
            <Field
              label="Cryptomus merchant ID"
              hint={secretHint("cryptomus_merchant_id")}
            >
              <input
                className="input"
                value={values.cryptomus_merchant_id ?? ""}
                onChange={(e) => set("cryptomus_merchant_id", e.target.value)}
              />
            </Field>
            <div className="grid gap-3 sm:grid-cols-2">
              <Field label="Сеть USDT">
                <select
                  className="input"
                  value={values.usdt_network ?? "TRC20"}
                  onChange={(e) => set("usdt_network", e.target.value)}
                >
                  <option value="TRC20">TRC-20 (Tron)</option>
                  <option value="TON">TON</option>
                  <option value="BEP20">BEP-20 (BSC)</option>
                  <option value="ERC20">ERC-20 (Ethereum)</option>
                </select>
              </Field>
              <Field label="Валюты" hint="через запятую">
                <input
                  className="input"
                  value={values.enabled_assets ?? ""}
                  onChange={(e) => set("enabled_assets", e.target.value)}
                />
              </Field>
            </div>
            <Field
              label="Публичный адрес панели"
              hint="нужен для webhook оплаты"
            >
              <input
                className="input"
                value={values.public_url ?? ""}
                onChange={(e) => set("public_url", e.target.value)}
                placeholder="https://panel.example.com"
              />
            </Field>
            <Toggle
              checked={bool("payments_test_mode")}
              onChange={(v) => set("payments_test_mode", String(v))}
              label="Тестовый режим криптоплатежей"
            />
          </div>
        </Card>
      )}

      {tab === "payments" && (
        <Card title="ЮMoney">
          <div className="space-y-4">
            <Toggle
              checked={bool("yoomoney_enabled")}
              onChange={(v) => set("yoomoney_enabled", String(v))}
              label="Включить ЮMoney"
            />
            <Field
              label="Номер кошелька"
              hint="куда приходят переводы, например 41001…"
            >
              <input
                className="input"
                value={values.yoomoney_wallet ?? ""}
                onChange={(e) => set("yoomoney_wallet", e.target.value)}
                placeholder="410011234567890"
              />
            </Field>
            <Field
              label="OAuth-токен"
              hint={secretHint("yoomoney_oauth_token")}
            >
              <input
                className="input"
                type="password"
                autoComplete="new-password"
                value={values.yoomoney_oauth_token ?? ""}
                onChange={(e) => set("yoomoney_oauth_token", e.target.value)}
                placeholder="значение не показывается"
              />
            </Field>
            <Field
              label="Секрет HTTP-уведомлений"
              hint={secretHint("yoomoney_notification_secret")}
            >
              <input
                className="input"
                type="password"
                autoComplete="new-password"
                value={values.yoomoney_notification_secret ?? ""}
                onChange={(e) =>
                  set("yoomoney_notification_secret", e.target.value)
                }
                placeholder="из настроек уведомлений ЮMoney"
              />
            </Field>
            <Field
              label="URL уведомлений"
              hint="вставь этот адрес в кабинете ЮMoney"
            >
              <input
                className="input"
                readOnly
                value={
                  (values.public_url || "").replace(/\/$/, "")
                    ? `${(values.public_url || "").replace(/\/$/, "")}/api/payments/yoomoney/webhook`
                    : "Сначала укажи публичный адрес панели выше"
                }
              />
            </Field>
            <div className="grid gap-3 sm:grid-cols-3">
              <Field label="Процент комиссии" hint="например 2 или 3">
                <input
                  className="input"
                  value={values.yoomoney_commission_percent ?? "3"}
                  onChange={(e) =>
                    set("yoomoney_commission_percent", e.target.value)
                  }
                />
              </Field>
              <Field label="Фикс. комиссия, ₽">
                <input
                  className="input"
                  value={values.yoomoney_commission_fixed ?? "0"}
                  onChange={(e) =>
                    set("yoomoney_commission_fixed", e.target.value)
                  }
                />
              </Field>
              <Field label="Комиссию платит">
                <select
                  className="input"
                  value={values.yoomoney_commission_payer ?? "client"}
                  onChange={(e) =>
                    set("yoomoney_commission_payer", e.target.value)
                  }
                >
                  <option value="client">Клиент</option>
                  <option value="seller">Продавец</option>
                </select>
              </Field>
            </div>
            <Field
              label="Тип перевода"
              hint="AC — карта, PC — кошелёк ЮMoney"
            >
              <select
                className="input"
                value={values.yoomoney_payment_type ?? "AC"}
                onChange={(e) => set("yoomoney_payment_type", e.target.value)}
              >
                <option value="AC">Банковская карта (AC)</option>
                <option value="PC">Кошелёк ЮMoney (PC)</option>
              </select>
            </Field>
            <p className="text-[11px] text-matrix-dim">
              Если комиссию платит клиент, к оплате = (цена + фикс) / (1 −
              процент/100), округление вверх до копейки. Пример: 50 ₽ и 2% →
              51.03 ₽, чтобы на кошелёк пришло не меньше 50 ₽. Для ЮMoney цена
              тарифа берётся как рубли.
            </p>
            <Toggle
              checked={bool("yoomoney_test_mode")}
              onChange={(v) => set("yoomoney_test_mode", String(v))}
              label="Тестовый режим ЮMoney"
            />
            <div className="flex flex-wrap gap-2 border-t border-matrix-border pt-4">
              <button className="btn-primary" onClick={save} disabled={busy}>
                Сохранить настройки
              </button>
              <button
                className="btn-ghost"
                disabled={busy}
                onClick={() => yoomoneyAction("test")}
              >
                Проверить подключение
              </button>
              <button
                className="btn-ghost"
                disabled={busy}
                onClick={() => yoomoneyAction("test-invoice")}
              >
                Создать тестовый платёж
              </button>
              <button
                className="btn-ghost"
                disabled={busy}
                onClick={() => yoomoneyAction("sync")}
              >
                Проверить ожидающие платежи
              </button>
            </div>
          </div>
        </Card>
      )}

      {tab === "texts" && (
        <Card title="Тексты бота">
          <div className="space-y-4">
            <Field
              label="Приветствие"
              hint="Доступны подстановки {name} и {free}"
            >
              <textarea
                className="input min-h-[110px]"
                value={values.welcome_text ?? ""}
                onChange={(e) => set("welcome_text", e.target.value)}
              />
            </Field>
            <Field label="Лимит исчерпан">
              <textarea
                className="input min-h-[80px]"
                value={values.limit_text ?? ""}
                onChange={(e) => set("limit_text", e.target.value)}
              />
            </Field>
            <Field label="Пользователь заблокирован">
              <textarea
                className="input min-h-[60px]"
                value={values.blocked_text ?? ""}
                onChange={(e) => set("blocked_text", e.target.value)}
              />
            </Field>
            <Field label="Ошибка ИИ">
              <textarea
                className="input min-h-[60px]"
                value={values.error_text ?? ""}
                onChange={(e) => set("error_text", e.target.value)}
              />
            </Field>
          </div>
        </Card>
      )}
    </div>
  );
}
