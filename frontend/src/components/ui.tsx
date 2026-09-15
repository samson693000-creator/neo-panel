import {
  createContext,
  useCallback,
  useContext,
  useState,
  type ReactNode,
} from "react";

interface Toast {
  id: number;
  text: string;
  kind: "ok" | "err";
}

const ToastCtx = createContext<(text: string, kind?: "ok" | "err") => void>(
  () => {},
);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<Toast[]>([]);

  const push = useCallback((text: string, kind: "ok" | "err" = "ok") => {
    const id = Date.now() + Math.random();
    setItems((prev) => [...prev, { id, text, kind }]);
    setTimeout(() => setItems((prev) => prev.filter((t) => t.id !== id)), 4000);
  }, []);

  return (
    <ToastCtx.Provider value={push}>
      {children}
      <div className="fixed bottom-5 right-5 z-[100] flex flex-col gap-2">
        {items.map((t) => (
          <div
            key={t.id}
            className={`panel px-4 py-3 text-sm max-w-sm ${
              t.kind === "ok"
                ? "border-matrix-green/60 text-matrix-green"
                : "border-matrix-red/60 text-matrix-red"
            }`}
          >
            <span className="opacity-60 mr-2">
              {t.kind === "ok" ? "[ OK ]" : "[ ERR ]"}
            </span>
            {t.text}
          </div>
        ))}
      </div>
    </ToastCtx.Provider>
  );
}

export const useToast = () => useContext(ToastCtx);

export function Card({
  title,
  action,
  children,
  className = "",
}: {
  title?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`panel p-4 sm:p-5 ${className}`}>
      {(title || action) && (
        <header className="mb-4 flex items-center justify-between gap-3">
          {title && (
            <h2 className="text-sm uppercase tracking-[0.2em] text-matrix-green">
              {title}
            </h2>
          )}
          {action}
        </header>
      )}
      {children}
    </section>
  );
}

export function Stat({
  label,
  value,
  hint,
  tone = "green",
}: {
  label: string;
  value: string | number;
  hint?: string;
  tone?: "green" | "red" | "amber";
}) {
  const toneClass =
    tone === "red"
      ? "text-matrix-red"
      : tone === "amber"
        ? "text-matrix-amber"
        : "text-matrix-green";
  return (
    <div className="panel p-4">
      <div className="text-[11px] uppercase tracking-widest text-matrix-dim">
        {label}
      </div>
      <div className={`mt-2 text-2xl sm:text-3xl font-semibold ${toneClass}`}>
        {value}
      </div>
      {hint && <div className="mt-1 text-xs text-matrix-dim">{hint}</div>}
    </div>
  );
}

export function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: ReactNode;
}) {
  return (
    <div>
      <label className="label">{label}</label>
      {children}
      {hint && <p className="mt-1 text-[11px] text-matrix-dim">{hint}</p>}
    </div>
  );
}

export function Toggle({
  checked,
  onChange,
  label,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
  label: string;
}) {
  return (
    <button
      type="button"
      onClick={() => onChange(!checked)}
      className="flex items-center gap-3 text-sm text-matrix-dim hover:text-matrix-green"
    >
      <span
        className={`h-5 w-10 rounded-full border transition-colors relative ${
          checked
            ? "border-matrix-green bg-matrix-green/30"
            : "border-matrix-border bg-black/60"
        }`}
      >
        <span
          className={`absolute top-0.5 h-3.5 w-3.5 rounded-full transition-all ${
            checked ? "left-5 bg-matrix-green" : "left-0.5 bg-matrix-dim"
          }`}
        />
      </span>
      {label}
    </button>
  );
}

export function Modal({
  open,
  title,
  onClose,
  children,
  wide = false,
}: {
  open: boolean;
  title: string;
  onClose: () => void;
  children: ReactNode;
  wide?: boolean;
}) {
  if (!open) return null;
  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/80 p-4 py-10"
      onClick={onClose}
    >
      <div
        className={`panel w-full ${wide ? "max-w-3xl" : "max-w-lg"} p-5`}
        onClick={(e) => e.stopPropagation()}
      >
        <header className="mb-4 flex items-center justify-between">
          <h3 className="text-sm uppercase tracking-[0.2em] text-matrix-green">
            {title}
          </h3>
          <button className="btn-ghost px-2 py-1" onClick={onClose}>
            X
          </button>
        </header>
        {children}
      </div>
    </div>
  );
}

export function Spinner({ text = "Загрузка" }: { text?: string }) {
  return (
    <div className="flex items-center gap-3 py-8 text-sm text-matrix-dim">
      <span className="h-3 w-3 animate-ping rounded-full bg-matrix-green" />
      {text}...
    </div>
  );
}

export function fmtDate(value: string | null | undefined) {
  if (!value) return "-";
  return new Date(value).toLocaleString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}
