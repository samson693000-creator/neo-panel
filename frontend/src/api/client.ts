const BASE = import.meta.env.VITE_API_URL ?? "";

export const tokenStore = {
  get: () => localStorage.getItem("token"),
  set: (t: string) => localStorage.setItem("token", t),
  clear: () => localStorage.removeItem("token"),
};

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  const token = tokenStore.get();
  if (token) headers.Authorization = `Bearer ${token}`;

  const res = await fetch(`${BASE}${path}`, { ...options, headers });

  if (res.status === 401) {
    tokenStore.clear();
    if (!path.includes("/auth/login")) window.location.href = "/login";
    throw new ApiError("Требуется авторизация", 401);
  }

  const text = await res.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    throw new ApiError(text.slice(0, 200) || `Ошибка ${res.status}`, res.status);
  }

  if (!res.ok) {
    const detail = data?.detail ?? `Ошибка ${res.status}`;
    throw new ApiError(
      typeof detail === "string" ? detail : JSON.stringify(detail),
      res.status,
    );
  }
  return data as T;
}

export const api = {
  get: <T>(p: string) => request<T>(p),
  post: <T>(p: string, body?: unknown) =>
    request<T>(p, { method: "POST", body: body ? JSON.stringify(body) : "{}" }),
  put: <T>(p: string, body?: unknown) =>
    request<T>(p, { method: "PUT", body: body ? JSON.stringify(body) : "{}" }),
  del: <T>(p: string) => request<T>(p, { method: "DELETE" }),
};

export async function downloadAuth(path: string, fallbackName: string) {
  const token = tokenStore.get();
  const res = await fetch(`${BASE}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (res.status === 401) {
    tokenStore.clear();
    window.location.href = "/login";
    throw new ApiError("Требуется авторизация", 401);
  }
  if (!res.ok) {
    throw new ApiError(`Ошибка ${res.status}`, res.status);
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  const header = res.headers.get("content-disposition") || "";
  const match = /filename="?([^"]+)"?/.exec(header);
  link.href = url;
  link.download = match?.[1] || fallbackName;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

export interface Dashboard {
  users_total: number;
  users_today: number;
  users_active_7d: number;
  blocked: number;
  requests_total: number;
  requests_today: number;
  paid_users: number;
  revenue_total: number;
  bot_status: string;
  bot_username: string;
  ai_configured: boolean;
  payments_configured: boolean;
}

export interface BotUser {
  id: number;
  telegram_id: number;
  username: string | null;
  first_name: string | null;
  last_name: string | null;
  free_used: number;
  paid_requests: number;
  total_requests: number;
  is_unlimited: boolean;
  is_blocked: boolean;
  tariff_id: number | null;
  tariff_expires_at: string | null;
  note: string;
  created_at: string;
  last_seen: string | null;
}

export interface UserList {
  items: BotUser[];
  total: number;
  page: number;
  pages: number;
}

export interface Tariff {
  id: number;
  name: string;
  description: string;
  price: number;
  currency: string;
  requests: number;
  is_unlimited: boolean;
  duration_days: number;
  is_active: boolean;
  sort_order: number;
}

export interface SettingsPayload {
  values: Record<string, string>;
  secret_keys: string[];
  secret_filled: Record<string, boolean>;
}

export interface BotState {
  status: string;
  username: string;
  error: string;
}

export interface RequestRow {
  id: number;
  telegram_id: number;
  username: string | null;
  prompt: string;
  tokens: number;
  source: string;
  is_error: boolean;
  created_at: string;
}

export interface LogRow {
  id: number;
  admin: string;
  action: string;
  entity: string;
  details: string;
  created_at: string;
}

export interface PaymentRow {
  id: number;
  telegram_id: number;
  username: string | null;
  tariff: string;
  provider: string;
  invoice_id: string;
  order_id?: string;
  amount: number;
  amount_net?: number;
  amount_gross?: number;
  commission_amount?: number;
  asset: string;
  network: string;
  status: string;
  pay_url: string;
  created_at: string;
  paid_at: string | null;
}

export interface PaymentList {
  items: PaymentRow[];
  total: number;
  page: number;
  pages: number;
  revenue: number;
  pending: number;
}

export interface Audience {
  key: string;
  label: string;
  count: number;
}

export interface BroadcastRow {
  id: number;
  text: string;
  audience: string;
  audience_label: string;
  status: string;
  total: number;
  sent: number;
  failed: number;
  created_at: string;
  finished_at: string | null;
  running: boolean;
}
