import { Link, useLocation } from "react-router-dom";
import { useAuthContext } from "@/context/AuthContext";
import { useSSE } from "@/hooks/useSSE";

const navLinks = [
  { to: "/", label: "Dashboard" },
  { to: "/submit", label: "Submit" },
];

export function Layout({ children }: { children: React.ReactNode }) {
  const { user, signOut } = useAuthContext();
  const location = useLocation();
  const { status } = useSSE("/api/stream/triage-results", !!user);

  const sseColor =
    status === "connected"
      ? "bg-green-500"
      : status === "connecting"
        ? "bg-yellow-500"
        : "bg-red-500";

  return (
    <div className="min-h-screen">
      <header className="border-b border-border bg-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3">
          <div className="flex items-center gap-6">
            <Link to="/" className="text-lg font-bold text-primary">
              Sentinel Health
            </Link>
            <nav className="flex gap-4">
              {navLinks.map((link) => (
                <Link
                  key={link.to}
                  to={link.to}
                  className={`text-sm font-medium transition-colors ${
                    location.pathname === link.to
                      ? "text-primary"
                      : "text-muted hover:text-gray-900"
                  }`}
                >
                  {link.label}
                </Link>
              ))}
            </nav>
          </div>
          <div className="flex items-center gap-4">
            <span className={`h-2 w-2 rounded-full ${sseColor}`} title={`SSE: ${status}`} />
            <span className="text-sm text-muted">{user?.email}</span>
            <button
              onClick={() => void signOut()}
              className="rounded px-3 py-1 text-sm text-muted hover:bg-surface-dark"
            >
              Sign out
            </button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-6">{children}</main>
    </div>
  );
}
