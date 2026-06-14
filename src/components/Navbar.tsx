import { Link, useLocation } from "react-router-dom";
import { logout } from "../api";

interface NavbarProps {
  onLoginClick: () => void;
  isAuthenticated: boolean;
  userEmail: string;
  userRole: string;
}

export default function Navbar({ onLoginClick, isAuthenticated, userEmail, userRole }: NavbarProps) {
  const location = useLocation();

  return (
    <nav className="navbar">
      <div className="navbar-brand">
        <Link to="/events" style={{ textDecoration: "none", color: "inherit" }}>
          PenguWave 🐧
        </Link>
      </div>
      <div className="navbar-links">
        <Link
          to="/events"
          className={location.pathname.startsWith("/events") ? "active" : ""}
        >
          Events
        </Link>
        <Link
          to="/users"
          className={location.pathname === "/users" ? "active" : ""}
        >
          Users
        </Link>
        {isAuthenticated ? (
          <>
            <span style={{ fontSize: 14, color: "#555" }}>
              {userEmail} ({userRole})
            </span>
            <button onClick={logout} className="navbar-login-btn">
              Logout
            </button>
          </>
        ) : (
          <button onClick={onLoginClick} className="navbar-login-btn">
            Login
          </button>
        )}
      </div>
    </nav>
  );
}
