import { useState, useEffect } from "react";
import type { JSX } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import Navbar from "./components/Navbar";
import LoginModal from "./components/LoginModal";
import EventsPage from "./pages/EventsPage";
import UsersPage from "./pages/UsersPage";
import NotFound from "./pages/NotFound";

// Skip the login modal during local development.
const DEBUG_BYPASS_AUTH = false;

// Wraps a protected page. If the user is authenticated it renders the page;
// otherwise it opens the login modal (via onBlocked) and renders nothing at
// all — the page component never mounts, so no protected content exists in the
// background behind the modal. onBlocked runs in an effect so we never call
// setState during render.
function ProtectedRoute({
  isAuthenticated,
  onBlocked,
  children,
}: {
  isAuthenticated: boolean;
  onBlocked: () => void;
  children: JSX.Element;
}) {
  useEffect(() => {
    if (!isAuthenticated) onBlocked();
  }, [isAuthenticated, onBlocked]);

  if (!isAuthenticated) return null;
  return children;
}

function App() {
  const [showLogin, setShowLogin] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  // On app load, restore the session from a stored token. If there's no token,
  // prompt the user to sign in.
  useEffect(() => {
    if (DEBUG_BYPASS_AUTH) {
      setIsAuthenticated(true);
      return;
    }
    const token = localStorage.getItem("token");
    if (token) {
      setIsAuthenticated(true);
    } else {
      setShowLogin(true);
    }
  }, []);

  // Called by LoginModal once the backend returns a valid token.
  const handleLoginSuccess = () => {
    setIsAuthenticated(true);
    setShowLogin(false);
  };

  const handleCloseLogin = () => {
    setShowLogin(false);
  };

  return (
    <>
      <Navbar onLoginClick={() => setShowLogin(true)} />
      <div className="container">
        <Routes>
          {/* When authenticated, land on /events; otherwise stay put so the
              login modal can sit on top without a redirect loop. */}
          <Route
            path="/"
            element={isAuthenticated ? <Navigate to="/events" replace /> : null}
          />
          <Route
            path="/events"
            element={
              <ProtectedRoute
                isAuthenticated={isAuthenticated}
                onBlocked={() => setShowLogin(true)}
              >
                <EventsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/users"
            element={
              <ProtectedRoute
                isAuthenticated={isAuthenticated}
                onBlocked={() => setShowLogin(true)}
              >
                <UsersPage />
              </ProtectedRoute>
            }
          />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </div>
      {showLogin && (
        <LoginModal
          onClose={handleCloseLogin}
          onSuccess={handleLoginSuccess}
          canClose={isAuthenticated}
        />
      )}
    </>
  );
}

export default App;
