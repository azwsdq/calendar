from fastapi import FastAPI, Request, Form, Depends
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime
import calendar

from database import engine, get_db, Base
from models import event

Base.metadata.create_all(bind=engine) # Создаем таблицы в базе данных, если они еще не существуют
app = FastAPI()  #! не удалять

templates = Jinja2Templates(directory="templates")  #? показывает где находятся шаблоны HTML
app.mount("/static", StaticFiles(directory="static"), name="static")  #? показывает где нахоятся статические файлы (CSS, JS, изображения)

@app.get("/")
async def calendar_page(request: Request, db: Session = Depends(get_db), year: int = None, month: int = None):
    now = datetime.now()
    year = year or now.year
    month = month or now.month

    month_calendar = calendar.monthcalendar(year, month)
    month_name = calendar.month_name[month]

    # Загружаем только события выбранного месяца и года.
    month_events = (
        db.query(event)
        .filter(
            event.date >= datetime(year, month, 1).date(),
            event.date < datetime(year + (1 if month == 12 else 0), (month % 12) + 1, 1).date(),
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
    })

#! ДОБОВЛЕНИЕ СОБЫТИЯ
@app.post("/add_event")
async def add_event(
        title: str = Form(...),
        date: str = Form(...),
        description: str = Form(...),
        db: Session = Depends(get_db)
):
    #Создание события в базе данных
    new_event = event(
        title=title,
        date=datetime.strptime(date, "%Y-%m-%d").date(),
        description=description
    )
    #Сохранение в БД
    db.add(new_event)
    db.commit()
    db.refresh(new_event)

    #возвращение обратно
    return RedirectResponse(url="/", status_code=303)