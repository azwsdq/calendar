from fastapi import FastAPI, Request, Form, Depends
from typing import Optional
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, FileResponse
from sqlalchemy.orm import Session
from datetime import datetime
from pywebpush import webpush, WebPushException
from models import PushSubscription
import json
import calendar
import os
import bcrypt
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from database import engine, get_db, Base
from models import User, Event 
# from models import Event as event

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger


Base.metadata.create_all(bind=engine)
app = FastAPI()

scheduler = AsyncIOScheduler()

@app.on_event("startup")
async def start_scheduler():
    scheduler.add_job(
        send_daily_reminders,
        CronTrigger(hour=23, minute=30),
    )
    scheduler.start()

@app.on_event("shutdown")
async def stop_scheduler():
    scheduler.shutdown()

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/sw.js")
async def sw():
    return FileResponse("static/sw.js")


VAPID_PUBLIC_KEY = os.getenv("VAPID_PUBLIC_KEY")
VAPID_PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY")


@app.post("/push/subscribe")
async def push_subscribe(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    user_id = request.session.get("user_id")
    existing = db.query(PushSubscription).filter(
        PushSubscription.endpoint == data["endpoint"]
    ).first()
    if not existing:
        sub = PushSubscription(
            user_id=user_id,
            endpoint=data["endpoint"],
            p256dh=data["keys"]["p256dh"],
            auth=data["keys"]["auth"],
        )
        db.add(sub)
        db.commit()
    return {"ok": True}

async def send_daily_reminders():
    from database import SessionLocal
    db = SessionLocal()
    try:
        today = datetime.now().date()
        
        # Находим все события на сегодня
        events_today = db.query(Event).filter(Event.date == today).all()
        if not events_today:
            return

        # Группируем по пользователям
        user_events = {}
        for ev in events_today:
            user_events.setdefault(ev.user_id, []).append(ev.title)

        # Отправляем каждому пользователю
        for user_id, titles in user_events.items():
            subs = db.query(PushSubscription).filter(
                PushSubscription.user_id == user_id
            ).all()

            body = "Сегодня: " + ", ".join(titles)
            payload = json.dumps({
                "title": "‼️ Скоро дедлайн!!!",
                "body": body,
                "url": "/",
            })

            for sub in subs:
                try:
                    webpush(
                        subscription_info={
                            "endpoint": sub.endpoint,
                            "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
                        },
                        data=payload,
                        vapid_private_key=VAPID_PRIVATE_KEY,
                        vapid_claims={"sub": "mailto:test@test.com"},
                    )
                except WebPushException as e:
                    print(f"Ошибка: {e}")
                    if "410" in str(e) or "404" in str(e):
                        db.delete(sub)
                        db.commit()
    finally:
        db.close()

# @app.post("/push/data_calendar")
# async def data_calendar(request: Request, db: Session = Depends(get_db)):
#     user_id = request.session.get("user_id")
#     subs = db.query(PushSubscription).filter(
#         PushSubscription.user_id == user_id
#     ).all()

    

#     if not subs:
#         return {"ok": False, "message": "Нет подписчиков"}
#     payload = json.dumps({
#         "title": "ДАТА!",
#         "body": "что то там завтра",
#         "url": "/",
#     })
#     for sub in subs:
#         try:
#             webpush(
#                 subscription_info={
#                     "endpoint": sub.endpoint,
#                     "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
#                 },
#                 data=payload,
#                 vapid_private_key=VAPID_PRIVATE_KEY,
#                 vapid_claims={"sub": "mailto:test@test.com"},
#             )
#         except WebPushException as e:
#             print(f"Ошибка: {e}")
#             if "410" in str(e) or "404" in str(e):
#                 db.delete(sub)
#                 db.commit()
#     return {"ok": True}

@app.get("/test-push")
async def test_push():
    await send_daily_reminders()
    return {"ok": True}

@app.post("/push/send")
async def push_send(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    subs = db.query(PushSubscription).filter(
        PushSubscription.user_id == user_id
    ).all()
    if not subs:
        return {"ok": False, "message": "Нет подписчиков"}
    payload = json.dumps({
        "title": "Напоминание!",
        "body": "У вас есть предстоящие события",
        "url": "/",
    })
    for sub in subs:
        try:
            webpush(
                subscription_info={
                    "endpoint": sub.endpoint,
                    "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
                },
                data=payload,
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims={"sub": "mailto:test@test.com"},
            )
        except WebPushException as e:
            print(f"Ошибка: {e}")
            if "410" in str(e) or "404" in str(e):
                db.delete(sub)
                db.commit()
    return {"ok": True}

# Middleware аутентификации — перенаправляет незалогиненных пользователей на /login
class AuthMiddleware(BaseHTTPMiddleware):
    PUBLIC = {"/login", "/register", "/static"}

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path.startswith("/static") or path in self.PUBLIC:
            return await call_next(request)
        if not request.session.get("user_id"):
            return RedirectResponse(url="/login", status_code=302)
        return await call_next(request)


app.add_middleware(AuthMiddleware)
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SECRET_KEY", "change-me-in-production"),
    session_cookie="session",
    max_age=86400 * 7,
    https_only=False,
)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


@app.get("/register")
async def register_page(request: Request):
    return templates.TemplateResponse(
        request,
        "register.html",
        {"error": None}
    )


@app.post("/register")
async def register(
        request: Request,
        email: str = Form(...),
        password: str = Form(...),
        password_confirm: str = Form(...),
        db: Session = Depends(get_db),
):
    if password != password_confirm:
        error = "Пароли не совпадают"
    elif len(password) < 8:
        error = "Пароль должен содержать не менее 8 символов"
    elif db.query(User).filter(User.email == email).first():
        error = "Пользователь с таким email уже существует"
    else:
        error = None

    if error:
        return templates.TemplateResponse(
            request,
            "register.html",
            {"error": error, "email": email}
        )

    user = User(email=email, hashed_password=hash_password(password))
    db.add(user)
    db.commit()
    db.refresh(user)
    request.session["user_id"] = user.id
    return RedirectResponse(url="/", status_code=303)


@app.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse(
        request,
        "login.html",
        {"error": None}
    )


@app.post("/login")
async def login(
        request: Request,
        email: str = Form(...),
        password: str = Form(...),
        db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse(
            request,
            "login.html",
            {"error": "Неверный email или пароль", "email": email}
        )
    request.session["user_id"] = user.id
    return RedirectResponse(url="/", status_code=303)


@app.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)


@app.get("/")
async def calendar_page(
        request: Request,
        db: Session = Depends(get_db),
        year: int = None,
        month: int = None,
):
    now = datetime.now()
    year = year or now.year
    month = month or now.month

    month_calendar = calendar.monthcalendar(year, month)
    month_name = calendar.month_name[month]

    user_id = request.session.get("user_id")
    month_events = (
        db.query(Event)
        .filter(
            Event.user_id == user_id,
            Event.date >= datetime(year, month, 1).date(),
            Event.date < datetime(year + (1 if month == 12 else 0), (month % 12) + 1, 1).date(),
        )
        .all()
    )

    events_by_day = {}
    for item in month_events:
        events_by_day.setdefault(item.date.day, []).append(item)

    return templates.TemplateResponse("calendar.html", {
        "request": request,
        "year": year,
        "month": month,
        "month_name": month_name,
        "calendar": month_calendar,
        "events_by_day": events_by_day,
        "vapid_public_key": os.getenv("VAPID_PUBLIC_KEY"),
    })


@app.post("/add_event")
async def add_event(
        request: Request,
        title: str = Form(...),
        date: str = Form(...),
        description: Optional[str] = Form(None),
        db: Session = Depends(get_db),
):
    new_event = Event(
        title=title,
        date=datetime.strptime(date, "%Y-%m-%d").date(),
        description=description  or "",
        user_id=request.session.get("user_id"),
    )
    db.add(new_event)
    db.commit()
    db.refresh(new_event)
    return RedirectResponse(url="/", status_code=303)


@app.post("/delete_event")
async def delete_event(
        request: Request,
        event_id: int = Form(...),
        year: int = Form(...),
        month: int = Form(...),
        db: Session = Depends(get_db),
):
    user_id = request.session.get("user_id")
    ev = db.query(Event).filter(Event.id == event_id, Event.user_id == user_id).first()
    if ev:
        db.delete(ev)
        db.commit()
    return RedirectResponse(url=f"/?year={year}&month={month}", status_code=303)


@app.get("/tasks")
async def tasks_page(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    tasks = db.query(Event).filter(Event.user_id == user_id).order_by(Event.date).all()

    return templates.TemplateResponse(
        request,
        "tasks.html",
        {
            "tasks": tasks,
            "today": datetime.now().date(),
        }
    )


@app.post("/add_task")
async def add_task(
        request: Request,
        title: str = Form(...),
        description: Optional[str] = Form(None),
        due_date: str = Form(...),
        db: Session = Depends(get_db),
):
    new_event = Event(
        title=title,
        description=description or "",
        date=datetime.strptime(due_date, "%Y-%m-%d").date(),
        user_id=request.session.get("user_id"),
    )
    db.add(new_event)
    db.commit()
    return RedirectResponse(url="/tasks", status_code=303)


@app.post("/delete_task")
async def delete_task(
        request: Request,
        task_id: int = Form(...),
        db: Session = Depends(get_db),
):
    user_id = request.session.get("user_id")
    task = db.query(Event).filter(Event.id == task_id, Event.user_id == user_id).first()
    if task:
        db.delete(task)
        db.commit()
    return RedirectResponse(url="/tasks", status_code=303)


@app.post("/edit_task")
async def edit_task(
        request: Request,
        task_id: int = Form(...),
        title: str = Form(...),
        description: Optional[str] = Form(None),
        due_date: str = Form(...),
        db: Session = Depends(get_db),
):
    user_id = request.session.get("user_id")
    task = db.query(Event).filter(Event.id == task_id, Event.user_id == user_id).first()
    if task:
        task.title = title
        task.description = description
        task.date = datetime.strptime(due_date, "%Y-%m-%d").date()
        db.commit()
    return RedirectResponse(url="/tasks", status_code=303)