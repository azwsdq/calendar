from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from datetime import datetime
import calendar
app = FastAPI() #запуск сайта на fastapi
templates = Jinja2Templates(directory="templates") #показывает где находяться шаблоны html

app.mount("/static", StaticFiles(directory="static"), name="static")  #это для статики, чтобы показывать картинки и css

@app.get("/")
async def home_page(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})