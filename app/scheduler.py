from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
import pytz
from .database import SessionLocal
from .models import Event
from .utils import format_event
import os

TZ = pytz.timezone(os.getenv("TIMEZONE","Europe/Zagreb"))

def send_message_to_chat(app, chat_id, text, reply_markup=None):
    # app — telegram Application instance
    app.bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML", reply_markup=reply_markup)

def weekly_report_job(app):
    sess = SessionLocal()
    now = datetime.now(tz=TZ)
    # период ближайших 7 дней
    end = now + timedelta(days=7)
    events = sess.query(Event).filter(Event.event_datetime >= now, Event.event_datetime <= end, Event.deleted==False).all()
    if not events:
        return
    text = "<b>Еженедельный отчёт событий на ближайшие 7 дней</b>\n\n"
    for ev in events:
        text += format_event(ev) + "\n\n"
        ev.notify_weekly_sent = True
    sess.commit()
    # рассылка: сюда нужно взять список target chat ids
    target_chats = os.getenv("TARGET_CHAT_IDS", "")
    if target_chats:
        for chat in target_chats.split(","):
            try:
                send_message_to_chat(app, chat, text)
            except Exception as e:
                print("send err", e)
    sess.close()

def daily_24h_job(app):
    sess = SessionLocal()
    now = datetime.now(tz=TZ)
    start = now + timedelta(days=1)
    end = start + timedelta(minutes=60)  # диапазон 1 час
    events = sess.query(Event).filter(Event.event_datetime >= start, Event.event_datetime <= end, Event.notify_24h_sent==False, Event.deleted==False).all()
    for ev in events:
        text = "<b>Напоминание: событие завтра</b>\n\n" + format_event(ev)
        # рассылка — аналогично
        target_chats = os.getenv("TARGET_CHAT_IDS", "")
        if target_chats:
            for chat in target_chats.split(","):
                try:
                    send_message_to_chat(app, chat, text)
                except:
                    pass
        ev.notify_24h_sent = True
    sess.commit()
    sess.close()

def cleanup_job(app):
    sess = SessionLocal()
    now = datetime.now(tz=TZ)
    old = sess.query(Event).filter(Event.event_datetime <= now - timedelta(days=7)).all()
    for ev in old:
        ev.deleted = True
        ev.deleted_at = now
    sess.commit()
    sess.close()

def start_scheduler(app):
    sched = BackgroundScheduler(timezone=TZ)
    # еженедельно: понедельник 09:00
    sched.add_job(lambda: weekly_report_job(app), trigger='cron', day_of_week='mon', hour=9, minute=0)
    # ежедневно проверить 24h напоминания каждую минуту (или каждый час)
    sched.add_job(lambda: daily_24h_job(app), trigger='cron', hour='*/1')  # ежечасно
    # cleanup: ежедневно в 03:00
    sched.add_job(lambda: cleanup_job(app), trigger='cron', hour=3, minute=0)
    sched.start()
    return sched
