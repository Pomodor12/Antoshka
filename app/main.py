import os
from fastapi import FastAPI, Request
import uvicorn
from .bot import build_application
from .scheduler import start_scheduler
from telegram import Update
import asyncio

app = FastAPI()
application = build_application()
scheduler = start_scheduler(application)

@app.on_event("startup")
async def on_startup():
    # установить webhook
    WEBHOOK_URL = os.getenv("WEBHOOK_URL")
    if WEBHOOK_URL:
        await application.bot.set_webhook(WEBHOOK_URL)
    # запуск polling не нужен если webhook
    # но обязательно запустить application.run_polling? no — we'll process incoming updates in /webhook
    print("Bot startup complete")

@app.on_event("shutdown")
async def on_shutdown():
    await application.bot.delete_webhook()
    print("Shutting down")

@app.post("/webhook")
async def telegram_webhook(req: Request):
    data = await req.json()
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return {"ok": True}

@app.get("/health")
async def health():
    return {"status":"ok"}

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
