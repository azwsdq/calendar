from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Form, Depends, status
from typing import Optional
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, FileResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, time as dt_time
from pywebpush import webpush, WebPushException
import json
import calendar
import os
import bcrypt
import uvicorn
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from database import engine, get_db, Base, run_migrations
from models import User, Event, PushSubscription

Base.metadata.create_all(bind=engine)
run_migrations()


scheduler = AsyncIOScheduler()


async def send_hourly_reminders():
    from database import SessionLocal
    from sqlalchemy import or_, and_
    db = SessionLocal()
    try:
        now = datetime.now()
        today = now.date()
        current_hour = now.hour

        print(f"[HOURLY] Запуск: {now}, час: {current_hour}")

        events = db.query(Event).filter(
            or_(
                Event.date_end == today,
                and_(Event.date_end == None, Event.date == today),
            ),
            Event.deadline_time != None,
        ).all()

        print(f"[HOURLY] Найдено событий с дедлайном сегодня и временем: {len(events)}")
        for ev in events:
            print(f"[HOURLY] Событие: '{ev.title}', deadline_time: {ev.deadline_time}")

        if not events:
            print("[HOURLY] Нет событий — выход")
            return

        notify = []
        for ev in events:
            deadline_hour = ev.deadline_time.hour
            hours_left = deadline_hour - current_hour

            if hours_left == 3:
                notify.append((ev, "До дедлайна 3 часа!", "Осталось 3 часа"))
            elif hours_left == 1:
                notify.append((ev, "До дедлайна 1 час!", "Остался 1 час"))

        print(f"[HOURLY] К отправке: {len(notify)}")

        user_events = {}
        for ev, title, label in notify:
            user_events.setdefault(ev.user_id, []).append((title, label, ev.title))

        for user_id, items in user_events.items():
            subs = db.query(PushSubscription).filter(
                PushSubscription.user_id == user_id
            ).all()
            print(f"[HOURLY] Пользователь {user_id}, подписок: {len(subs)}")

            for push_title, label, event_title in items:
                payload = json.dumps({
                    "title": push_title,
                    "body": f"{label}: {event_title}",
                    "url": "/tasks",
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
                        print(f"[HOURLY] Push отправлен: {push_title}")
                    except WebPushException as e:
                        print(f"[HOURLY] Ошибка push: {e}")
                        if "410" in str(e) or "404" in str(e) or "400" in str(e):
                            db.delete(sub)
                            db.commit()
    finally:
        db.close()

async def send_daily_reminders():
    from database import SessionLocal
    from sqlalchemy import or_, and_
    db = SessionLocal()
    try:
        today = datetime.now().date()

        notify_offsets = {
            0: ("Дедлайн сегодня!", "Срок истекает сегодня"),
            1: ("Завтра дедлайн!", "Остался 1 день"),
            3: ("До дедлайна 3 дня", "Осталось 3 дня"),
            7: ("До дедлайна неделя", "Осталось 7 дней"),
        }

        for offset, (title, label) in notify_offsets.items():
            target_date = today + timedelta(days=offset)

            events = db.query(Event).filter(
                or_(
                    and_(Event.date_end == target_date),
                    and_(Event.date_end == None, Event.date == target_date),
                )
            ).all()

            if not events:
                continue

            user_events = {}
            for ev in events:
                user_events.setdefault(ev.user_id, []).append(ev.title)

            for user_id, titles in user_events.items():
                subs = db.query(PushSubscription).filter(
                    PushSubscription.user_id == user_id
                ).all()

                body = f"{label}: " + ", ".join(titles)
                payload = json.dumps({
                    "title": title,
                    "body": body,
                    "url": "/tasks",
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
                        print(f"Ошибка push: {e}")
                        if "410" in str(e) or "404" in str(e) or "400" in str(e):
                            db.delete(sub)
                            db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[STARTUP] Запуск планировщика...")
    scheduler.add_job(send_daily_reminders, CronTrigger(hour=9, minute=0))
    scheduler.add_job(send_hourly_reminders, CronTrigger(minute=0))
    scheduler.start()
    print("[STARTUP] Планировщик запущен")

    yield

    print("[SHUTDOWN] Остановка планировщика...")
    scheduler.shutdown()
    print("[SHUTDOWN] Планировщик остановлен")


app = FastAPI(lifespan=lifespan)

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

VAPID_PUBLIC_KEY = os.getenv("VAPID_PUBLIC_KEY")
VAPID_PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY")


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



@app.get("/sw.js")
async def sw():
    return FileResponse("static/sw.js")


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


@app.get("/test-push-hourly")
async def test_push_hourly():
    await send_hourly_reminders()
    return {"ok": True}


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
            if "410" in str(e) or "404" in str(e) or "400" in str(e):
                db.delete(sub)
                db.commit()
    return {"ok": True}


@app.get("/test-push-now")
async def test_push_now(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    subs = db.query(PushSubscription).filter(
        PushSubscription.user_id == user_id
    ).all()

    print(f"[TEST] Подписок найдено: {len(subs)}")

    if not subs:
        return {"ok": False, "message": "Нет подписок — сначала нажми кнопку Уведомления на главной"}

    payload = json.dumps({
        "title": "Тест уведомления",
        "body": "Уведомления работают!",
        "url": "/tasks",
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
            print(f"[TEST] Push отправлен")
        except WebPushException as e:
            print(f"[TEST] Ошибка: {e}")

    return {"ok": True}



@app.post("/clear-messages")
async def clear_messages(request: Request):
    request.session.pop("success_message", None)
    request.session.pop("error_message", None)
    return {"ok": True}


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
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


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
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


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

    all_events = db.query(Event).filter(Event.user_id == user_id).all()

    month_start = datetime(year, month, 1).date()
    if month == 12:
        month_end = datetime(year + 1, 1, 1).date()
    else:
        month_end = datetime(year, month + 1, 1).date()

    events_by_day = {}

    for event in all_events:
        event_start = event.date
        event_end = event.date_end if event.date_end else event_start

        if event_start < month_end and event_end >= month_start:
            current_date = event_start
            while current_date <= event_end:
                if current_date.year == year and current_date.month == month:
                    day = current_date.day
                    if day not in events_by_day:
                        events_by_day[day] = []
                    if not any(e.id == event.id for e in events_by_day[day]):
                        events_by_day[day].append(event)
                current_date += timedelta(days=1)

    return templates.TemplateResponse(
        request,
        "calendar.html",
        {
            "year": year,
            "month": month,
            "month_name": month_name,
            "calendar": month_calendar,
            "events_by_day": events_by_day,
            "vapid_public_key": os.getenv("VAPID_PUBLIC_KEY"),
        }
    )


@app.post("/add_event")
async def add_event(
        request: Request,
        title: str = Form(...),
        date: str = Form(...),
        date_end: str = Form(None),
        deadline_time: str = Form(None),
        description: Optional[str] = Form(None),
        priority: str = Form("Medium"),
        db: Session = Depends(get_db),
):
    try:
        start_date = datetime.strptime(date, "%Y-%m-%d").date()

        if not date_end or date_end.strip() == "" or date_end == date:
            end_date = None
        else:
            end_date = datetime.strptime(date_end, "%Y-%m-%d").date()
            if end_date < start_date:
                end_date = None

        parsed_time = None
        if deadline_time:
            h, m = map(int, deadline_time.split(":"))
            parsed_time = dt_time(h, m)

        new_event = Event(
            title=title,
            date=start_date,
            date_end=end_date,
            deadline_time=parsed_time,
            description=description or "",
            priority=priority,
            user_id=request.session.get("user_id"),
        )
        db.add(new_event)
        db.commit()
        db.refresh(new_event)

        request.session["success_message"] = "Событие успешно добавлено!"

    except Exception as e:
        db.rollback()
        request.session["error_message"] = f"Ошибка при добавлении: {str(e)}"

    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


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
        due_date_end: str = Form(None),
        deadline_time: str = Form(None),
        priority: str = Form("Medium"),
        db: Session = Depends(get_db),
):
    try:
        start_date = datetime.strptime(due_date, "%Y-%m-%d").date()

        if not due_date_end or due_date_end.strip() == "" or due_date_end == due_date:
            end_date = None
        else:
            end_date = datetime.strptime(due_date_end, "%Y-%m-%d").date()
            if end_date < start_date:
                end_date = None

        parsed_time = None
        if deadline_time:
            h, m = map(int, deadline_time.split(":"))
            parsed_time = dt_time(h, m)

        new_event = Event(
            title=title,
            description=description or "",
            date=start_date,
            date_end=end_date,
            deadline_time=parsed_time,
            priority=priority,
            user_id=request.session.get("user_id"),
        )
        db.add(new_event)
        db.commit()
        db.refresh(new_event)

        request.session["success_message"] = "Задача успешно добавлена!"

    except Exception as e:
        db.rollback()
        request.session["error_message"] = f"Ошибка при добавлении: {str(e)}"

    return RedirectResponse(url="/tasks", status_code=status.HTTP_303_SEE_OTHER)


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
        deadline_time: str = Form(None),
        due_date_end: str = Form(None),
        priority: str = Form("Medium"),
        db: Session = Depends(get_db),
):
    try:
        user_id = request.session.get("user_id")
        task = db.query(Event).filter(Event.id == task_id, Event.user_id == user_id).first()
        if task:
            task.title = title
            task.description = description or ""
            task.date = datetime.strptime(due_date, "%Y-%m-%d").date()

            if not due_date_end or due_date_end.strip() == "" or due_date_end == due_date:
                task.date_end = None
            else:
                end_date = datetime.strptime(due_date_end, "%Y-%m-%d").date()
                start_date = datetime.strptime(due_date, "%Y-%m-%d").date()
                if end_date >= start_date:
                    task.date_end = end_date
                else:
                    task.date_end = None

            task.priority = priority

            if deadline_time and deadline_time.strip():
                h, m = map(int, deadline_time.split(":"))
                task.deadline_time = dt_time(h, m)
            else:
                task.deadline_time = None

            db.commit()
            request.session["success_message"] = "Задача успешно обновлена!"
    except Exception as e:
        db.rollback()
        request.session["error_message"] = f"Ошибка при обновлении: {str(e)}"

    return RedirectResponse(url="/tasks", status_code=303)

@app.get("/about")
async def about_page(request: Request):
    return templates.TemplateResponse(
        request,
        "about.html",
        {}
    )

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)