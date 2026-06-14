import { useState } from "react";

interface LoginModalProps {
  onClose: () => void;
  onSuccess: () => void;
  // Whether the modal may be dismissed. Until the user has authenticated this
  // is false, so login is the only way out — no close button, no backdrop click.
  canClose: boolean;
}

export default function LoginModal({ onClose, onSuccess, canClose }: LoginModalProps) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    // Authenticate against the backend. Only a response carrying a token
    // counts as success — that's when we persist it and notify the app.
    fetch("http://localhost:3001/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    })
      .then((res) => res.json())
      .then((data) => {
        if (data.token) {
          localStorage.setItem("token", data.token);
          onSuccess();
        }
      })
      .catch(() => {
        // Backend not running or login failed — leave the modal open.
      });
  };

  return (
    <div className="modal-backdrop" onClick={canClose ? onClose : undefined}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        {canClose && (
          <button className="modal-close" onClick={onClose}>
            ✕
          </button>
        )}
        <h2>Sign In</h2>
        <p style={{ color: "#666", marginBottom: 20, fontSize: 14 }}>
          Enter your credentials to access PenguWave
        </p>
        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: 12 }}>
            <label>Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@company.com"
            />
          </div>
          <div style={{ marginBottom: 16 }}>
            <label>Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
            />
          </div>
          <button type="submit" className="btn-primary" style={{ width: "100%" }}>
            Sign In
          </button>
        </form>
      </div>
    </div>
  );
}
