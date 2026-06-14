# PenguWave — Security Operations Portal

PenguWave is a security operations portal where SOC analysts review, triage, and act on security events, backed by a secure FastAPI API with JWT auth, role-based access control, and AI-assisted event triage.

## How to Run

The app has two parts: a Python backend (port 3001) and a React frontend (port 5173). Run each in its own terminal.

### Backend

```bash
cd backend
pip3 install -r requirements.txt
python3 main.py
```

The API starts on http://localhost:3001. On first launch it creates the SQLite database and seeds default users and events.

### Frontend

```bash
npm install
npm run dev
```

The frontend runs on http://localhost:5173.

### Default credentials

| Role    | Email                   | Password    |
| ------- | ----------------------- | ----------- |
| Admin   | admin@penguwave.com     | admin123    |
| Analyst | analyst@penguwave.com   | analyst123  |

> **Never use these passwords in production.** They exist only to seed a local development environment.

## What I Built

**Track A: Backend.** A FastAPI + SQLite backend (no ORM, raw `sqlite3` with parameterized queries throughout) that powers the portal. Authentication is handled with JWTs signed using a secret loaded from the environment; every protected request is validated for signature and expiry and re-checked against the live user record. Authorization is role-based — `admin` and `analyst` roles, with admin-only routes for user management. The standout feature is AI-assisted triage: an endpoint that sends an event's details to Azure OpenAI and returns a senior-analyst-style assessment to help the SOC team prioritize.

## Key Security Decisions

- **bcrypt password hashing** — passwords are stored as slow bcrypt hashes, making brute-force attacks expensive even if the database is stolen.
- **JWT with 24h expiration** — tokens carry an `exp` claim and are rejected automatically once expired.
- **Parameterized queries** — all SQL uses `?` placeholders with bound values, so user input can never alter a query (SQL injection prevention).
- **Same error for bad email and bad password** — login returns one identical "Invalid email or password" message so attackers can't discover which emails are registered (anti-enumeration).
- **Server-side role validation** — roles are validated on the server, never trusting the frontend to restrict privileged actions.
- **Status checked on every request** — the user's `status` is re-read from the database per request, so disabling an account takes effect immediately even for still-valid tokens.
- **CORS locked to localhost:5173** — only the known frontend origin may make credentialed browser requests.
- **Passwords never returned** — responses serialize through a `UserResponse` model that has no password field, so hashes can't leak.

## Issues Found in Existing Code

- **Hardcoded API key in `api.ts`** — a secret was committed in frontend source; moved server-side.
- **`console.log` leaking plaintext passwords** — the login flow logged raw credentials to the browser console; removed.
- **`sanitizeHtml` was a no-op** — it returned input unchanged, leaving an XSS risk; replaced with real sanitization.
- **`isAdmin()` trusted localStorage** — admin status was read from client-controlled storage and trivially bypassable; authorization is now enforced server-side.
- **Routes were unprotected** — `/events` and `/users` were navigable without logging in; they now require authentication and redirect to the login modal otherwise.

## AI Feature

`GET /api/events/{id}/analyze` takes a single security event, builds a structured prompt from its severity, title, description, asset, source IP, and tags, and asks Azure OpenAI — acting as a senior security analyst — to explain what the event likely means, how urgent it really is, and what the analyst should do next. This gives a SOC analyst an instant, consistent first read on an event (run at low temperature for repeatable, grounded output), cutting triage time and helping prioritize a noisy queue. The Azure OpenAI API key stays server-side, loaded from environment variables and never exposed to the browser.

## Tradeoffs and What I'd Do With More Time

- **JWT logout** — implement true server-side revocation with a token blacklist (e.g. Redis storing revoked token IDs until they expire).
- **Rate limiting on login** — throttle repeated attempts to blunt brute-force and credential-stuffing attacks.
- **HTTPS in production** — terminate TLS so tokens and credentials are never sent in cleartext.
- **Refresh tokens** — pair short-lived access tokens with longer-lived refresh tokens for better security and UX.
