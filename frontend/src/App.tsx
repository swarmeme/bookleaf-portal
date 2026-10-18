import type { ReactElement } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import type { Role } from "./api/types";
import { useAuth } from "./auth/AuthContext";
import Layout from "./components/Layout";
import { PageLoader } from "./components/ui";
import AdminTicketPage from "./pages/admin/AdminTicketPage";
import QueuePage from "./pages/admin/QueuePage";
import BooksPage from "./pages/author/BooksPage";
import MyTicketsPage from "./pages/author/MyTicketsPage";
import NewTicketPage from "./pages/author/NewTicketPage";
import TicketPage from "./pages/author/TicketPage";
import LoginPage from "./pages/LoginPage";

const HOME: Record<Role, string> = { author: "/books", admin: "/admin/tickets" };

/** Routes only for one role. The API enforces access too; this just keeps people on their own portal. */
function RequireRole({ role, children }: { role: Role; children: ReactElement }) {
  const { user, loading } = useAuth();
  const location = useLocation();
  if (loading) return <PageLoader />;
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  if (user.role !== role) return <Navigate to={HOME[user.role]} replace />;
  return children;
}

export default function App() {
  const { user, loading } = useAuth();
  if (loading) return <PageLoader />;

  return (
    <Routes>
      <Route path="/login" element={user ? <Navigate to={HOME[user.role]} replace /> : <LoginPage />} />

      <Route element={<RequireRole role="author"><Layout /></RequireRole>}>
        <Route path="/books" element={<BooksPage />} />
        <Route path="/tickets" element={<MyTicketsPage />} />
        <Route path="/tickets/new" element={<NewTicketPage />} />
        <Route path="/tickets/:id" element={<TicketPage />} />
      </Route>

      <Route element={<RequireRole role="admin"><Layout /></RequireRole>}>
        <Route path="/admin/tickets" element={<QueuePage />} />
        <Route path="/admin/tickets/:id" element={<AdminTicketPage />} />
      </Route>

      <Route path="*" element={<Navigate to={user ? HOME[user.role] : "/login"} replace />} />
    </Routes>
  );
}
