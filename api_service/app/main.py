# code for website will go
from fastapi import FastAPI, Request, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from passlib.hash import bcrypt
from .database import get_database, get_mongo_client, close_mongo_client
from bson import ObjectId
from contextlib import asynccontextmanager
import html
import re

from .services.queue_service import create_appointment_for_patient


@asynccontextmanager
async def lifespan(app):
    # Startup
    get_mongo_client()
    yield
    # Shutdown
    close_mongo_client()


api_application = FastAPI(lifespan=lifespan, title="Medical Queue API")

api_application.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")
"""
FastAPI application instance that exposes endpoints for the medical
queue backend.
"""


@api_application.middleware("http")
async def auth_middleware(request: Request, call_next):
    open_paths = [
        "/login",
        "/register",
        "/register/patient",
        "/register/doctor",
        "/static",
    ]

    # allow static files + public routes
    if any(request.url.path.startswith(p) for p in open_paths):
        return await call_next(request)

    # allow root page
    if request.url.path == "/":
        return await call_next(request)

    # session check
    if not request.cookies.get("user_id"):
        return RedirectResponse("/login")

    return await call_next(request)


@api_application.get("/", response_class=HTMLResponse)
async def root_redirect():
    return RedirectResponse("/login")


@api_application.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@api_application.post("/login")
async def login(request: Request):
    form = await request.form()
    email = form["email"]
    password = form["password"]
    role = form["role"]

    db = get_database()
    collection = db["patients"] if role == "patient" else db["doctors"]

    user = await collection.find_one({"email": email})
    if not user:
        return RedirectResponse("/login?error=invalid", status_code=302)

    if not bcrypt.verify(password, user["password_hash"]):
        return RedirectResponse("/login?error=invalid", status_code=302)

    # login OK
    response = RedirectResponse(
        "/patient/dashboard" if role == "patient" else "/doctor/dashboard",
        status_code=302,
    )
    response.set_cookie("user_id", str(user["_id"]))
    response.set_cookie("role", role)
    return response


@api_application.get("/register/patient", response_class=HTMLResponse)
async def register_patient_page(request: Request):
    return templates.TemplateResponse("register_patient.html", {"request": request})


@api_application.post("/register/patient")
async def register_patient(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
):
    print("PASSWORD RECEIVED:", repr(password))
    db = get_database()

    existing = await db["patients"].find_one({"email": email})
    if existing:
        return HTMLResponse(
            "<h3>Email already registered. Please login.</h3>", status_code=400
        )

    hashed = bcrypt.hash(password)

    patient_id = (
        await db["patients"].insert_one(
            {"name": name, "email": email, "password_hash": hashed, "symptoms": []}
        )
    ).inserted_id

    response = RedirectResponse("/onboarding/symptoms", status_code=302)
    response.set_cookie("user_id", str(patient_id))
    response.set_cookie("role", "patient")
    return response


@api_application.get("/register/doctor", response_class=HTMLResponse)
async def register_doctor_page(request: Request):
    return templates.TemplateResponse("register_doctor.html", {"request": request})


@api_application.post("/register/doctor")
async def register_doctor(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
):
    db = get_database()

    existing = await db["doctors"].find_one({"email": email})
    if existing:
        return HTMLResponse(
            "<h3>Email already registered. Please login.</h3>", status_code=400
        )

    hashed = bcrypt.hash(password)

    doctor_id = (
        await db["doctors"].insert_one(
            {"name": name, "email": email, "password_hash": hashed}
        )
    ).inserted_id

    response = RedirectResponse("/doctor/dashboard", status_code=302)
    response.set_cookie("user_id", str(doctor_id))
    response.set_cookie("role", "doctor")
    return response


@api_application.get("/onboarding/symptoms", response_class=HTMLResponse)
async def symptoms_page(request: Request):
    return templates.TemplateResponse("patient_onboarding.html", {"request": request})


@api_application.post("/onboarding/symptoms")
async def symptoms_submit(request: Request):
    form = await request.form()

    symptoms = form.getlist("symptoms")
    other = form.get("other_symptom", "").strip()

    user_id = request.cookies.get("user_id")
    if not user_id:
        return RedirectResponse("/login")

    allowed = {
        "fever",
        "cough",
        "fatigue",
        "nausea",
        "headache",
        "sore_throat",
        "shortness_of_breath",
        "chest_pain",
        "congestion",
        "vomiting",
        "diarrhea",
        "other",
    }
    symptoms = [symptom_name for symptom_name in symptoms if symptom_name in allowed]

    cleaned_other = None
    if other:
        safe_other = html.escape(other)

        if re.fullmatch(r"[A-Za-z0-9 ,.'-]{1,80}", other):
            cleaned_other = safe_other

    final_symptoms = symptoms.copy()
    if cleaned_other:
        # we do not store the raw text as symptom name for the model,
        # just record that there was an "other" symptom
        if "other" not in final_symptoms:
            final_symptoms.append("other")

    database_connection = get_database()
    await database_connection["patients"].update_one(
        {"_id": ObjectId(user_id)}, {"$set": {"symptoms": final_symptoms}}
    )

    appointment = await create_appointment_for_patient(
        patient_id=ObjectId(user_id),
        symptom_names=final_symptoms,
    )

    # We now store queue_number and predicted_wait_minutes in Mongo
    # and the dashboard will look them up by patient_id.
    return RedirectResponse("/patient/dashboard", status_code=302)


@api_application.get("/patient/dashboard", response_class=HTMLResponse)
async def patient_dashboard(request: Request):
    user_id = request.cookies.get("user_id")
    if not user_id:
        return RedirectResponse("/login")

    database_connection = get_database()

    # Find the current waiting appointment for this patient, if any
    appointment = await database_connection["appointments"].find_one(
        {
            "patient_id": ObjectId(user_id),
            "status": "waiting",
        }
    )

    queue_number = None
    eta = None

    if appointment is not None:
        queue_number = appointment.get("queue_number")
        predicted_wait_minutes = appointment.get("predicted_wait_minutes")
        if predicted_wait_minutes is not None:
            eta = int(predicted_wait_minutes)

    context = {
        "request": request,
        "queue_number": queue_number,
        "eta": eta,
    }
    return templates.TemplateResponse("patient_dashboard.html", context)


@api_application.get("/doctor/dashboard", response_class=HTMLResponse)
async def doctor_dashboard(request: Request):
    return templates.TemplateResponse("doctor_dashboard.html", {"request": request})


# logout route for future logout implementation
@api_application.get("/logout")
async def logout():
    response = RedirectResponse("/login")
    response.delete_cookie("user_id")
    response.delete_cookie("role")
    return response
