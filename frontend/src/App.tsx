import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import { Spinner } from "./components/ui";
import Account from "./pages/Account";
import Admins from "./pages/Admins";
import Broadcasts from "./pages/Broadcasts";
import Dashboard from "./pages/Dashboard";
import Login from "./pages/Login";
import Logs from "./pages/Logs";
import Payments from "./pages/Payments";
import Settings from "./pages/Settings";
import Tariffs from "./pages/Tariffs";
import Users from "./pages/Users";
import { useAuth } from "./store/auth";

export default function App() {
  const { me, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Spinner text="Инициализация" />
      </div>
    );
  }

  if (!me) {
    return (
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    );
  }

  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/users" element={<Users />} />
        <Route path="/tariffs" element={<Tariffs />} />
        <Route path="/payments" element={<Payments />} />
        <Route path="/broadcasts" element={<Broadcasts />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/admins" element={<Admins />} />
        <Route path="/logs" element={<Logs />} />
        <Route path="/account" element={<Account />} />
      </Route>
      <Route path="/login" element={<Navigate to="/" replace />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
