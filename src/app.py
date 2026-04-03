"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import os
from pathlib import Path

from storage import (
    get_activities as get_activities_db,
    initialize_database,
    signup_for_activity as signup_for_activity_db,
    unregister_from_activity as unregister_from_activity_db,
)

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

initialize_database()

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    return get_activities_db()


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, email: str):
    """Sign up a student for an activity"""
    ok, message, status_code = signup_for_activity_db(activity_name, email)
    if not ok:
        raise HTTPException(status_code=status_code, detail=message)
    return {"message": message}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(activity_name: str, email: str):
    """Unregister a student from an activity"""
    ok, message, status_code = unregister_from_activity_db(activity_name, email)
    if not ok:
        raise HTTPException(status_code=status_code, detail=message)
    return {"message": message}
