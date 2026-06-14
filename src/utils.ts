// Shared helpers for PenguWave.

/**
 * Sanitize a string before rendering it as HTML.
 * Escapes the angle brackets that open HTML tags so any markup in the input is
 * displayed as text rather than executed, preventing XSS.
 */
export function sanitizeHtml(input: string): string {
  return input.replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

/**
 * Serialize a list of records to CSV for export.
 */
export function toCsv(rows: Record<string, unknown>[]): string {
  if (rows.length === 0) return "";
  const headers = Object.keys(rows[0]);
  const lines = rows.map((r) => headers.map((h) => String(r[h] ?? "")).join(","));
  return [headers.join(","), ...lines].join("\n");
}

/**
 * Whether the current user has admin privileges.
 * role is read from the signed JWT — cannot be forged without the server secret.
 */
export function isAdmin(): boolean {
  const token = localStorage.getItem("token");
  if (!token) return false;
  try {
    const payload = JSON.parse(atob(token.split(".")[1]));
    return payload.role === "admin";
  } catch {
    return false;
  }
}
