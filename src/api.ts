const API_URL = "http://localhost:3001";

// No API key lives here: secrets belong server-side, never in frontend source.
// Requests authenticate with the user's JWT (Authorization: Bearer) instead.

export async function login(email: string, password: string) {
  // credentials are sent only over the wire to the backend, never logged
  const res = await fetch(`${API_URL}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  const data = await res.json();
  localStorage.setItem("token", data.token);
  return data;
}

// Returns only the events the current user is allowed to see —
// the backend already filters results per-user, so no extra checks are needed here.
export async function getEvents() {
  const token = localStorage.getItem("token");
  const res = await fetch(`${API_URL}/api/events`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  return res.json();
}

export async function getUsers() {
  const token = localStorage.getItem("token");
  const res = await fetch(`${API_URL}/api/users`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  // Surface the HTTP status so callers can distinguish e.g. a 403 (not an admin)
  // from a successful response.
  if (!res.ok) {
    const err = new Error("Failed to load users") as Error & { status: number };
    err.status = res.status;
    throw err;
  }
  return res.json();
}

export async function createUser(user: { email: string; password: string; role: string }) {
  const token = localStorage.getItem("token");
  const res = await fetch(`${API_URL}/api/users`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify(user),
  });
  return res.json();
}

export async function deleteUser(id: string) {
  const token = localStorage.getItem("token");
  const res = await fetch(`${API_URL}/api/users/${id}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
  return res.json();
}
