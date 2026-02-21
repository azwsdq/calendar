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

    events = db.query(event).all() #получаем все события из базы данных
    cal = calendar.monthcalendar(year, month)
    monthname = calendar.month_name[month]

    return templates.TemplateResponse("calendar.html", {
        "request": request,
        "year": year,
        "month": month,
        "monthname": monthname,
        "cal": cal,
        "events": events
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