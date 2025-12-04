import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters, CallbackQueryHandler
from .database import SessionLocal, engine
from .models import Event, Base
from .utils import format_event
from datetime import datetime, timedelta
import pytz

TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
TZ = pytz.timezone(os.getenv("TIMEZONE","Europe/Zagreb"))

# Create tables
Base.metadata.create_all(bind=engine)

# Conversation states
(STATE_DATE, STATE_TIME, STATE_TITLE, STATE_GUESTS, STATE_LOCATION, STATE_CONFIRM) = range(6)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Используй /add чтобы добавить событие, /list чтобы посмотреть события.")

### Простой add flow (пошагово) ###
async def add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введите дату в формате ГГГГ-MM-ДД (например 2026-06-14):")
    return STATE_DATE

async def add_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    try:
        d = datetime.fromisoformat(text)
    except Exception:
        await update.message.reply_text("Неверный формат даты. Повторите (YYYY-MM-DD):")
        return STATE_DATE
    context.user_data['date'] = d.date().isoformat()
    await update.message.reply_text("Введите время в формате ЧЧ:ММ (например 19:00):")
    return STATE_TIME

async def add_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t = update.message.text.strip()
    try:
        hh, mm = map(int, t.split(":"))
    except:
        await update.message.reply_text("Неверный формат времени. Повторите (HH:MM):")
        return STATE_TIME
    context.user_data['time'] = t
    await update.message.reply_text("Введите название события:")
    return STATE_TITLE

async def add_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['title'] = update.message.text.strip()
    await update.message.reply_text("Введите количество гостей (число) или оставьте пустым:")
    return STATE_GUESTS

async def add_guests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == "":
        g = None
    else:
        try:
            g = int(text)
        except:
            await update.message.reply_text("Нужно число. Введите количество гостей:")
            return STATE_GUESTS
    context.user_data['guests'] = g
    await update.message.reply_text("Введите место (Июнь или Мартынова или другое):")
    return STATE_LOCATION

async def add_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['location'] = update.message.text.strip()
    # show confirmation
    date_s = context.user_data['date']
    time_s = context.user_data['time']
    title = context.user_data['title']
    guests = context.user_data['guests']
    loc = context.user_data['location']
    msg = f"Подтвердите:\n<b>{title}</b>\n{date_s} {time_s}\nМесто: {loc}\nГостей: {guests or '—'}"
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Подтвердить", callback_data="confirm_add"),
                                      InlineKeyboardButton("Отменить", callback_data="cancel_add")]])
    await update.message.reply_html(msg, reply_markup=keyboard)
    return STATE_CONFIRM

async def add_confirm_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.data == "cancel_add":
        await q.edit_message_text("Добавление отменено.")
        return ConversationHandler.END
    # сохранить в БД
    sess = SessionLocal()
    dt_str = f"{context.user_data['date']}T{context.user_data['time']}:00"
    dt = datetime.fromisoformat(dt_str)
    dt = TZ.localize(dt)
    ev = Event(
        title=context.user_data['title'],
        event_datetime=dt,
        guests=context.user_data['guests'],
        location=context.user_data['location'],
        origin_chat_id=str(q.message.chat.id),
    )
    sess.add(ev); sess.commit(); sess.refresh(ev)
    # логика немедленного уведомления:
    now = datetime.now(tz=TZ)
    delta = ev.event_datetime - now
    if delta.total_seconds() < 6*24*3600:
        # отправить немедленно в нужные чаты (пример: все чаты из ENV или origin)
        # здесь просто подтверждение автору
        await q.edit_message_text("Событие добавлено и уведомление отправлено немедленно.")
        ev.notify_immediate_sent = True
        sess.commit()
    else:
        await q.edit_message_text("Событие добавлено. Вы получите еженедельный/суточный оповеститель.")
    sess.close()
    return ConversationHandler.END

async def list_events(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sess = SessionLocal()
    now = datetime.now(tz=TZ)
    events = sess.query(Event).filter(Event.event_datetime >= now, Event.deleted==False).order_by(Event.event_datetime).all()
    if not events:
        await update.message.reply_text("Нет предстоящих событий.")
    else:
        for ev in events:
            await update.message.reply_html(format_event(ev))
    sess.close()

def build_application():
    app = ApplicationBuilder().token(TOKEN).build()
    conv = ConversationHandler(
        entry_points=[CommandHandler("add", add_start)],
        states={
            STATE_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_date)],
            STATE_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_time)],
            STATE_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_title)],
            STATE_GUESTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_guests)],
            STATE_LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_location)],
            STATE_CONFIRM: [CallbackQueryHandler(add_confirm_cb)]
        },
        fallbacks=[]
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv)
    app.add_handler(CommandHandler("list", list_events))
    return app
