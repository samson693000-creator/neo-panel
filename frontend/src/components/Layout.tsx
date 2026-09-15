import { useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import MatrixRain from "./MatrixRain";
import { useAuth } from "../store/auth";

const NAV = [
  { to: "/", label: "Дашборд", icon: "#", end: true, roles: ["owner", "admin", "support"] },
  { to: "/users", label: "Пользователи", icon: "@", roles: ["owner", "admin", "support"] },
  { to: "/tariffs", label: "Тарифы", icon: "$", roles: ["owner", "admin", "support"] },
  { to: "/payments", label: "Платежи", icon: "B", roles: ["owner", "admin", "support"] },
  { to: "/broadcasts", label: "Рассылки", icon: ">", roles: ["owner", "admin"] },
  { to: "/settings", label: "Настройки", icon: "*", roles: ["owner", "admin"] },
  { to: "/admins", label: "Администраторы", icon: "!", roles: ["owner"] },
  { to: "/logs", label: "Журнал", icon: "=", roles: ["owner", "admin"] },
  { to: "/account", label: "Аккаунт", icon: "~", roles: ["owner", "admin", "support"] },
];

export default function Layout() {
  const { me, logout } = useAuth();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <div className="relative min-h-screen">
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <MatrixRain opacity={0.07} />
      </div>

      <div className="relative flex min-h-screen">
        <aside
          className={`fixed z-40 h-full w-64 border-r border-matrix-border bg-matrix-panel/95 backdrop-blur
            transition-transform lg:static lg:translate-x-0 ${
              open ? "translate-x-0" : "-translate-x-full"
            }`}
        >
          <div className="flex h-16 items-center gap-2 border-b border-matrix-border px-5">
            <span className="text-lg text-matrix-green animate-flicker">//</span>
            <div>
              <div className="text-sm tracking-[0.25em] text-matrix-green">
                NEO PANEL
              </div>
              <div className="text-[10px] text-matrix-dim">ai bot control</div>
            </div>
          </div>

          <nav className="space-y-1 p-3">
            {NAV.filter((item) => item.roles.includes(me?.role || "")).map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === "/"}
                onClick={() => setOpen(false)}
                className={({ isActive }) =>
                  `nav-item ${isActive ? "nav-item-active" : ""}`
                }
              >
                <span className="w-4 text-center">{item.icon}</span>
                {item.label}
              </NavLink>
            ))}
          </nav>

          <div className="absolute bottom-0 w-full border-t border-matrix-border p-4">
            <div className="mb-2 text-xs text-matrix-dim">
              {me?.username}
              <span className="ml-2 badge-ok">{me?.role}</span>
            </div>
            <button className="btn-ghost w-full" onClick={handleLogout}>
              Выйти
            </button>
          </div>
        </aside>

        {open && (
          <div
            className="fixed inset-0 z-30 bg-black/60 lg:hidden"
            onClick={() => setOpen(false)}
          />
        )}

        <div className="flex min-w-0 flex-1 flex-col">
          <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-matrix-border bg-matrix-bg/90 px-4 backdrop-blur sm:px-6">
            <button
              className="btn-ghost px-3 py-1.5 lg:hidden"
              onClick={() => setOpen(true)}
            >
              MENU
            </button>
            <div className="hidden text-xs text-matrix-dim sm:block">
              <span className="text-matrix-green">root@neo</span>:~/panel$
              <span className="animate-pulse"> _</span>
            </div>
            <div className="text-xs text-matrix-dim">
              {new Date().toLocaleDateString("ru-RU")}
            </div>
          </header>

          <main className="min-w-0 flex-1 p-4 sm:p-6">
            <Outlet />
          </main>
        </div>
      </div>
    </div>
  );
}
