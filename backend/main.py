# Entry point for the PenguWave API.
#
# This module wires the whole backend together: it creates the FastAPI app,
# configures CORS for the frontend, mounts the auth/events/users routers,
# initializes and seeds the database on startup, and exposes a health check.
# Run it directly (python main.py) to start the development server.

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import init_db
from seed import seed_db
from routes.auth import router as auth_router
from routes.events import router as events_router
from routes.users import router as users_router

app = FastAPI(
    title="PenguWave API",
    description="Security operations portal backend",
    version="1.0.0",
)

# CORS: we allow only the frontend's dev origin (http://localhost:5173).
# CORS is a browser-enforced policy — it stops a page served from another
# domain from making credentialed requests to this API on a user's behalf
# (cross-site request forgery). It does NOT protect the API from direct,
# non-browser callers like curl or scripts, which ignore CORS entirely;
# that boundary is enforced separately by JWT authentication on each route.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # only the frontend origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount the feature routers; each declares its own /api/... prefix.
app.include_router(auth_router)
app.include_router(events_router)
app.include_router(users_router)


# Startup: prepare the database before the app serves any requests.
# Order matters — init_db() must run first to CREATE the tables, then seed_db()
# can safely INSERT default users and events into them. Seeding before the
# tables exist would fail.
@app.on_event("startup")
def on_startup():
    init_db()
    seed_db()
    print("PenguWave API started")


# GET /health — no auth required.
# used to verify the server is running before the frontend connects
@app.get("/health")
def health():
    return {"status": "ok", "service": "PenguWave API"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=3001, reload=True)
