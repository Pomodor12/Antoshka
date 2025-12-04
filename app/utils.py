from datetime import datetime
import pytz
TZ = pytz.timezone(os.getenv("TIMEZONE","Europe/Zagreb"))
def format_event(event):
    # event is Event instance
    dt = event.event_datetime.astimezone(TZ)
    s = (
        f"📣 <b>{event.title}</b>\n"
        f"📅 <b>Дата:</b> {dt.strftime('%d.%m.%Y, %H:%M')}\n"
        f"📍 <b>Место:</b> {event.location}\n"
        f"👥 <b>Гостей:</b> {event.guests or '—'}\n"
        f"\nID: <code>{event.id}</code>"
    )
    return s
