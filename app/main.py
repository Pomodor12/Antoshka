from fastapi import FastAPI, Request
from app.bot import build_application
from app.scheduler import start_scheduler
from telegram import Update
import asyncio

app = FastAPI()

# Создаём Telegram-бота
telegram_app = build_application()

# Запуск APScheduler
scheduler = start_scheduler(telegram_app)

@app.on_event("startup")
async def startup_event():
    print("Bot startup complete")

@app.on_event("shutdown")
async def shutdown_event():
    print("Bot shutdown")

# Webhook endpoint (для Telegram)
@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, telegram_app.bot)
    await telegram_app.process_update(update)
    return {"ok": True}

# Health check
@app.get("/health")
async def health():
    return {"status": "ok"}
