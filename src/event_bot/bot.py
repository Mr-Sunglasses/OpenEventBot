import asyncio
import logging
import re

from telegram import BotCommand, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from . import database as db
from .config import BOT_TOKEN

DELETE_DELAY = 300

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def _delete_after(message, delay: int = DELETE_DELAY) -> None:
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except Exception:
        pass


async def _is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if not update.effective_chat or not update.effective_user:
        return False
    member = await context.bot.get_chat_member(
        update.effective_chat.id, update.effective_user.id
    )
    return member.status in ("administrator", "creator")


def _build_event_text(description: str, attendees: list[dict]) -> str:
    lines = [f"📅 <b>Event</b>\n{_sanitize_html(description)}\n"]
    if attendees:
        lines.append(f"✅ <b>Going ({len(attendees)}):</b>")
        for i, attendee in enumerate(attendees, 1):
            name = _html_escape(attendee["name"])
            lines.append(f"  {i}. {name}")
    else:
        lines.append("✅ <b>Going:</b> No one yet")
    return "\n".join(lines)


def _build_keyboard(event_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ Going", callback_data=f"rsvp:{event_id}"),
                InlineKeyboardButton("❌ Can't go", callback_data=f"cancel:{event_id}"),
            ],
            [InlineKeyboardButton("🗑 Delete event", callback_data=f"delete:{event_id}")],
        ]
    )


async def _set_commands(application: Application) -> None:
    commands = [
        BotCommand("event", "Create a new event (admins only)"),
        BotCommand("help", "Show help and usage instructions"),
    ]
    await application.bot.set_my_commands(commands)
    logger.info("Bot commands registered.")


def _html_escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


_ALLOWED_TAGS = {
    "b", "/b", "i", "/i", "u", "/u", "s", "/s",
    "code", "/code", "pre", "/pre",
    "a", "/a",
    "tg-spoiler", "/tg-spoiler",
    "blockquote", "/blockquote",
    "tg-emoji", "/tg-emoji",
}


_HEADING_RE = re.compile(r"<(/?)h[1-6]\s*>", re.IGNORECASE)


def _sanitize_html(text: str) -> str:
    text = _HEADING_RE.sub(r"<\1b>", text)
    result = []
    i = 0
    while i < len(text):
        if text[i] == "<":
            j = text.find(">", i)
            if j != -1:
                tag = text[i + 1 : j].strip().split()[0] if " " in text[i + 1 : j] else text[i + 1 : j].strip()
                if tag in _ALLOWED_TAGS:
                    result.append(text[i : j + 1])
                    i = j + 1
                    continue
                elif tag == "br":
                    result.append("\n")
                    i = j + 1
                    continue
                else:
                    result.append(_html_escape(text[i : j + 1]))
                    i = j + 1
                    continue
            else:
                result.append(_html_escape(text[i]))
                i += 1
                continue
        elif text[i] == "&":
            result.append("&amp;")
            i += 1
            continue
        else:
            result.append(text[i])
            i += 1
    return "".join(result)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "👋 <b>OpenEvent_bot</b>\n\n"
        "Create events in your group and let people RSVP with a single tap.\n\n"
        "📖 <b>Commands:</b>\n"
        "• <code>/event &lt;description&gt;</code> — create a new event <i>(admins only)</i>\n"
        "• <code>/help</code> — show this message\n\n"
        "💡 <b>How to use:</b>\n"
        "1. Add this bot to your group as an admin\n"
        "2. Grant it <b>Delete Messages</b> permission\n"
        "3. Any admin can type <code>/event</code> followed by a description\n"
        "4. Attach a photo to <code>/event</code> to add an image banner\n"
        "5. Members tap <b>Going</b> or <b>Can't go</b> to RSVP\n\n"
        "📝 Event descriptions support HTML formatting and emojis."
    )
    msg = await update.message.reply_text(text, parse_mode="HTML")
    asyncio.create_task(_delete_after(msg))
    try:
        await update.message.delete()
    except Exception:
        pass


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await start(update, context)


async def create_event(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_chat:
        return

    if not await _is_admin(update, context):
        msg = await update.message.reply_text(
            "⚠️ Only group admins can create events."
        )
        asyncio.create_task(_delete_after(msg))
        try:
            await update.message.delete()
        except Exception:
            pass
        return

    caption = update.message.caption or ""
    text = update.message.text or ""

    if update.message.photo and caption.startswith("/event"):
        description = caption[len("/event"):].strip()
        photo_file_id = update.message.photo[-1].file_id
    elif text.startswith("/event"):
        description = text[len("/event"):].strip()
        photo_file_id = None
    else:
        return

    if not description:
        msg = await update.message.reply_text(
            "⚠️ Please provide a description.\n"
            "Usage: <code>/event &lt;description&gt;</code>",
            parse_mode="HTML",
        )
        asyncio.create_task(_delete_after(msg))
        try:
            await update.message.delete()
        except Exception:
            pass
        return

    chat_id = update.effective_chat.id
    original_message_id = update.message.message_id

    event_id = db.create_event(chat_id, original_message_id, description, photo_file_id)
    attendees = db.get_attendees(event_id)
    event_text = _build_event_text(description, attendees)
    keyboard = _build_keyboard(event_id)

    try:
        await update.message.delete()
    except Exception:
        pass

    if photo_file_id:
        sent = await context.bot.send_photo(
            chat_id=chat_id,
            photo=photo_file_id,
            caption=event_text,
            parse_mode="HTML",
            reply_markup=keyboard,
        )
    else:
        sent = await context.bot.send_message(
            chat_id=chat_id,
            text=event_text,
            parse_mode="HTML",
            reply_markup=keyboard,
        )

    db.update_event_message_id(event_id, sent.message_id)


async def rsvp_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    user = query.from_user
    if not user or not query.message:
        return

    data = query.data or ""
    parts = data.split(":")
    if len(parts) != 2:
        return

    action, event_id_str = parts
    try:
        event_id = int(event_id_str)
    except ValueError:
        return

    event = db.get_event_by_id(event_id)
    if not event:
        await query.answer("This event no longer exists.", show_alert=True)
        return

    if action == "delete":
        chat = update.effective_chat
        if not chat:
            return
        member = await context.bot.get_chat_member(chat.id, user.id)
        if member.status not in ("administrator", "creator"):
            await query.answer("Only admins can delete events.", show_alert=True)
            return
        db.delete_event(event_id)
        try:
            await query.message.delete()
        except Exception:
            pass
        return

    user_name = user.full_name

    if action == "rsvp":
        db.add_attendee(event_id, user.id, user_name)
    elif action == "cancel":
        db.remove_attendee(event_id, user.id)
    else:
        return

    attendees = db.get_attendees(event_id)
    event_text = _build_event_text(event["description"], attendees)
    keyboard = _build_keyboard(event_id)

    try:
        if event.get("photo_file_id"):
            await query.edit_message_caption(
                caption=event_text,
                parse_mode="HTML",
                reply_markup=keyboard,
            )
        else:
            await query.edit_message_text(
                text=event_text,
                parse_mode="HTML",
                reply_markup=keyboard,
            )
    except Exception:
        pass


def run() -> None:
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN is not set. Please set it in .env or environment variables.")
        raise SystemExit(1)

    db.init_db()
    logger.info("Database initialized.")

    application = Application.builder().token(BOT_TOKEN).post_init(_set_commands).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(
        MessageHandler(filters.COMMAND & filters.Regex(r"^/event"), create_event)
    )
    application.add_handler(
        MessageHandler(filters.PHOTO & filters.CaptionRegex(r"^/event"), create_event)
    )
    application.add_handler(CallbackQueryHandler(rsvp_callback))

    logger.info("Starting Event Bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)
