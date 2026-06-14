from fastapi import APIRouter, Depends, HTTPException
from typing import Annotated
import sqlite3
import json
import os
from dotenv import load_dotenv

from database import get_db
from auth import get_current_user
from models import EventResponse, EventAnalysis
from azure_client import AzureAIFoundryClient

load_dotenv()

# client is created once at module load — credentials come from .env, never from the request
ai_client = AzureAIFoundryClient()
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT")

router = APIRouter(prefix="/api/events", tags=["events"])


def parse_event(row) -> dict:
    """Convert a DB row into a plain dict with tags as a real list.

    tags are stored in SQLite as a JSON string (SQLite has no array type), so
    on read we deserialize them back into a Python list. `or "[]"` guards
    against NULL/empty values so json.loads always receives valid JSON.
    """
    event = dict(row)
    event["tags"] = json.loads(event["tags"] or "[]")
    return event


# GET /api/events — list every security event, newest first.
# all events visible to any authenticated user — filtering by role would be a future enhancement
@router.get("", response_model=list[EventResponse])
def list_events(
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[sqlite3.Connection, Depends(get_db)],
):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM events ORDER BY timestamp DESC")
    rows = cursor.fetchall()
    return [EventResponse(**parse_event(row)) for row in rows]


# GET /api/events/{event_id} — fetch a single event by id.
@router.get("/{event_id}", response_model=EventResponse)
def get_event(
    event_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[sqlite3.Connection, Depends(get_db)],
):
    cursor = db.cursor()
    # Parameterized query — event_id is bound as a value, never interpolated.
    cursor.execute("SELECT * FROM events WHERE id = ?", (event_id,))
    row = cursor.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return EventResponse(**parse_event(row))


# GET /api/events/{event_id}/analyze — AI triage assistance for one event.
# Sends the event's key fields to the model and asks for a SOC analyst's read.
@router.get("/{event_id}/analyze", response_model=EventAnalysis)
def analyze_event(
    event_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[sqlite3.Connection, Depends(get_db)],
):
    cursor = db.cursor()
    # Parameterized query — event_id is bound as a value, never interpolated.
    cursor.execute("SELECT * FROM events WHERE id = ?", (event_id,))
    row = cursor.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Event not found")

    event = parse_event(row)

    prompt = (
        "Analyze the following security event.\n\n"
        f"Severity: {event.get('severity')}\n"
        f"Title: {event.get('title')}\n"
        f"Description: {event.get('description')}\n"
        f"Asset hostname: {event.get('assetHostname')}\n"
        f"Source IP: {event.get('sourceIp')}\n"
        f"Tags: {', '.join(event.get('tags', [])) or 'none'}\n\n"
        "As a senior security analyst, provide:\n"
        "1. What this event likely means\n"
        "2. How urgent it actually is\n"
        "3. Recommended next action for the analyst"
    )

    # temperature=0.3 (low) keeps the analysis consistent and factual rather
    # than creative — for security triage we want repeatable, grounded
    # assessments, not varied or speculative ones.
    analysis = ai_client.generate_completion(
        deployment_name=AZURE_OPENAI_DEPLOYMENT,
        messages=[
            {
                "role": "system",
                "content": "You are a senior security analyst helping a SOC team triage security events. Be concise, precise, and actionable.",
            },
            {"role": "user", "content": prompt},
        ],
        max_tokens=500,
        temperature=0.3,
    )

    if analysis is None:
        raise HTTPException(status_code=500, detail="AI analysis unavailable")

    return EventAnalysis(event_id=event_id, analysis=analysis)
