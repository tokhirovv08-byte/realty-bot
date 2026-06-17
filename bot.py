import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, ContextTypes, filters
)
from sheets import SheetsManager
from config import BOT_TOKEN, DISTRICTS

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

sheets = SheetsManager()

# Состояния для добавления квартиры
(ADD_DISTRICT, ADD_LOCATION, ADD_AREA, ADD_FLOOR, ADD_TOTAL_FLOORS,
 ADD_BUILDING_FLOORS, ADD_ROOMS, ADD_PRICE, ADD_FURNITURE,
 ADD_RENOVATION, ADD_CONTACT, ADD_PHOTOS, ADD_CONFIRM) = range(13)

# Состояния для поиска
(SEARCH_DISTRICT, SEARCH_PRICE_MIN, SEARCH_PRICE_MAX,
 SEARCH_ROOMS, SEARCH_FURNITURE, SEARCH_RENOVATION) = range(13, 19)


def main_menu_keyboard():
    keyboard = [
        [KeyboardButton("🔍 Поиск квартиры"), KeyboardButton("➕ Добавить квартиру")],
        [KeyboardButton("📋 Все квартиры"), KeyboardButton("❓ Помощь")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def districts_keyboard(with_all=False):
    buttons = []
    row = []
    for i, d in enumerate(DISTRICTS):
        row.append(InlineKeyboardButton(d, callback_data=f"district_{d}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    if with_all:
        buttons.append([InlineKeyboardButton("🌍 Все районы", callback_data="district_ALL")])
    buttons.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel")])
    return InlineKeyboardMarkup(buttons)


def skip_keyboard():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("⏭ Пропустить", callback_data="skip"),
        InlineKeyboardButton("❌ Отмена", callback_data="cancel")
    ]])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! Я бот агентства недвижимости.\n\n"
        "Здесь вы можете искать квартиры из базы и добавлять новые объекты.\n\n"
        "Выберите действие:",
        reply_markup=main_menu_keyboard()
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📖 *Как пользоваться ботом:*\n\n"
        "🔍 *Поиск квартиры* — найти квартиры по фильтрам (район, цена, комнаты и т.д.)\n\n"
        "➕ *Добавить квартиру* — добавить новый объект в базу\n\n"
        "📋 *Все квартиры* — показать все объекты в базе\n\n"
        "При поиске можно пропускать любые фильтры кнопкой *Пропустить*."
    )
    await update.message.reply_text(text, parse_mode='Markdown', reply_markup=main_menu_keyboard())


# ==================== ПОИСК ====================

async def search_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['search'] = {}
    await update.message.reply_text(
        "🔍 *Поиск квартиры*\n\nВыберите район:",
        parse_mode='Markdown',
        reply_markup=districts_keyboard(with_all=True)
    )
    return SEARCH_DISTRICT


async def search_district(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "cancel":
        await query.edit_message_text("❌ Поиск отменён.")
        return ConversationHandler.END

    if data == "district_ALL":
        context.user_data['search']['district'] = None
    else:
        context.user_data['search']['district'] = data.replace("district_", "")

    await query.edit_message_text(
        "💰 Введите *минимальную цену* (в $) или пропустите:",
        parse_mode='Markdown',
        reply_markup=skip_keyboard()
    )
    return SEARCH_PRICE_MIN


async def search_price_min(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
        data = update.callback_query.data
        if data == "cancel":
            await update.callback_query.edit_message_text("❌ Поиск отменён.")
            return ConversationHandler.END
        context.user_data['search']['price_min'] = None
        await update.callback_query.edit_message_text(
            "💰 Введите *максимальную цену* (в $) или пропустите:",
            parse_mode='Markdown',
            reply_markup=skip_keyboard()
        )
    else:
        try:
            context.user_data['search']['price_min'] = int(update.message.text)
        except ValueError:
            await update.message.reply_text("⚠️ Введите число!", reply_markup=skip_keyboard())
            return SEARCH_PRICE_MIN
        await update.message.reply_text(
            "💰 Введите *максимальную цену* (в $) или пропустите:",
            parse_mode='Markdown',
            reply_markup=skip_keyboard()
        )
    return SEARCH_PRICE_MAX


async def search_price_max(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
        data = update.callback_query.data
        if data == "cancel":
            await update.callback_query.edit_message_text("❌ Поиск отменён.")
            return ConversationHandler.END
        context.user_data['search']['price_max'] = None
        await update.callback_query.edit_message_text(
            "🚪 Выберите количество комнат или пропустите:",
            reply_markup=rooms_search_keyboard()
        )
    else:
        try:
            context.user_data['search']['price_max'] = int(update.message.text)
        except ValueError:
            await update.message.reply_text("⚠️ Введите число!", reply_markup=skip_keyboard())
            return SEARCH_PRICE_MAX
        await update.message.reply_text(
            "🚪 Выберите количество комнат или пропустите:",
            reply_markup=rooms_search_keyboard()
        )
    return SEARCH_ROOMS


def rooms_search_keyboard():
    buttons = [
        [InlineKeyboardButton("1", callback_data="rooms_1"),
         InlineKeyboardButton("2", callback_data="rooms_2"),
         InlineKeyboardButton("3", callback_data="rooms_3"),
         InlineKeyboardButton("4+", callback_data="rooms_4")],
        [InlineKeyboardButton("⏭ Пропустить", callback_data="skip"),
         InlineKeyboardButton("❌ Отмена", callback_data="cancel")]
    ]
    return InlineKeyboardMarkup(buttons)


async def search_rooms(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "cancel":
        await query.edit_message_text("❌ Поиск отменён.")
        return ConversationHandler.END

    if data == "skip":
        context.user_data['search']['rooms'] = None
    else:
        context.user_data['search']['rooms'] = data.replace("rooms_", "")

    buttons = [
        [InlineKeyboardButton("✅ Есть мебель", callback_data="furn_yes"),
         InlineKeyboardButton("🚫 Без мебели", callback_data="furn_no")],
        [InlineKeyboardButton("⏭ Пропустить", callback_data="skip"),
         InlineKeyboardButton("❌ Отмена", callback_data="cancel")]
    ]
    await query.edit_message_text(
        "🛋 Нужна мебель и техника?",
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    return SEARCH_FURNITURE


async def search_furniture(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "cancel":
        await query.edit_message_text("❌ Поиск отменён.")
        return ConversationHandler.END

    if data == "skip":
        context.user_data['search']['furniture'] = None
    elif data == "furn_yes":
        context.user_data['search']['furniture'] = "да"
    else:
        context.user_data['search']['furniture'] = "нет"

    buttons = [
        [InlineKeyboardButton("✨ Евроремонт", callback_data="ren_euro"),
         InlineKeyboardButton("🏠 Обычный", callback_data="ren_standard")],
        [InlineKeyboardButton("⏭ Пропустить", callback_data="skip"),
         InlineKeyboardButton("❌ Отмена", callback_data="cancel")]
    ]
    await query.edit_message_text(
        "🔧 Тип ремонта?",
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    return SEARCH_RENOVATION


async def search_renovation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "cancel":
        await query.edit_message_text("❌ Поиск отменён.")
        return ConversationHandler.END

    if data == "skip":
        context.user_data['search']['renovation'] = None
    elif data == "ren_euro":
        context.user_data['search']['renovation'] = "евроремонт"
    else:
        context.user_data['search']['renovation'] = "обычный"

    await query.edit_message_text("🔄 Ищу подходящие квартиры...")
    await perform_search(update, context)
    return ConversationHandler.END


async def perform_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    filters = context.user_data.get('search', {})
    results = sheets.search_apartments(filters)

    chat_id = update.effective_chat.id

    if not results:
        await context.bot.send_message(
            chat_id=chat_id,
            text="😔 По вашим критериям квартир не найдено.\n\nПопробуйте изменить фильтры.",
            reply_markup=main_menu_keyboard()
        )
        return

    await context.bot.send_message(
        chat_id=chat_id,
        text=f"✅ Найдено квартир: *{len(results)}*",
        parse_mode='Markdown'
    )

    for apt in results[:10]:
        text = format_apartment(apt)
        photos = apt.get('photos', '').strip()

        try:
            if photos:
                photo_urls = [p.strip() for p in photos.split(',') if p.strip()]
                if photo_urls:
                    await context.bot.send_photo(
                        chat_id=chat_id,
                        photo=photo_urls[0],
                        caption=text,
                        parse_mode='Markdown'
                    )
                else:
                    await context.bot.send_message(chat_id=chat_id, text=text, parse_mode='Markdown')
            else:
                await context.bot.send_message(chat_id=chat_id, text=text, parse_mode='Markdown')
        except Exception:
            await context.bot.send_message(chat_id=chat_id, text=text, parse_mode='Markdown')

    await context.bot.send_message(
        chat_id=chat_id,
        text="Выберите следующее действие:",
        reply_markup=main_menu_keyboard()
    )


def format_apartment(apt):
    text = (
        f"🏠 *Квартира #{apt.get('id', '—')}*\n\n"
        f"🔹 Район: {apt.get('district', '—')}\n"
        f"🔹 Локация: {apt.get('location', '—')}\n"
        f"🔹 Площадь: {apt.get('area', '—')} м²\n"
        f"🔹 Комнат: {apt.get('rooms', '—')}\n"
        f"🔹 Этаж: {apt.get('floor', '—')}/{apt.get('total_floors', '—')} "
        f"(дом {apt.get('building_floors', '—')} эт.)\n"
        f"🔹 Мебель и техника: {apt.get('furniture', '—')}\n"
        f"🔹 Ремонт: {apt.get('renovation', '—')}\n\n"
        f"🔥 Цена: *${apt.get('price', '—')}*\n"
        f"📞 Контакт: {apt.get('contact', '—')}"
    )
    return text


# ==================== ДОБАВЛЕНИЕ ====================

async def add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['new_apt'] = {}
    await update.message.reply_text(
        "➕ *Добавление квартиры*\n\nВыберите район:",
        parse_mode='Markdown',
        reply_markup=districts_keyboard()
    )
    return ADD_DISTRICT


async def add_district(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "cancel":
        await query.edit_message_text("❌ Добавление отменено.")
        return ConversationHandler.END
    context.user_data['new_apt']['district'] = query.data.replace("district_", "")
    await query.edit_message_text(
        "📍 Введите *локацию* (например: 9 квартал, рядом с Korzinka):",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Отмена", callback_data="cancel")]])
    )
    return ADD_LOCATION


async def add_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("❌ Добавление отменено.")
        return ConversationHandler.END
    context.user_data['new_apt']['location'] = update.message.text
    await update.message.reply_text(
        "📐 Введите *площадь* квартиры (м²):",
        parse_mode='Markdown',
        reply_markup=skip_keyboard()
    )
    return ADD_AREA


async def add_area(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
        data = update.callback_query.data
        if data == "cancel":
            await update.callback_query.edit_message_text("❌ Добавление отменено.")
            return ConversationHandler.END
        context.user_data['new_apt']['area'] = "—"
        await update.callback_query.edit_message_text(
            "🏢 На каком *этаже* квартира?",
            parse_mode='Markdown',
            reply_markup=skip_keyboard()
        )
    else:
        context.user_data['new_apt']['area'] = update.message.text
        await update.message.reply_text(
            "🏢 На каком *этаже* квартира?",
            parse_mode='Markdown',
            reply_markup=skip_keyboard()
        )
    return ADD_FLOOR


async def add_floor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
        data = update.callback_query.data
        if data == "cancel":
            await update.callback_query.edit_message_text("❌ Добавление отменено.")
            return ConversationHandler.END
        context.user_data['new_apt']['floor'] = "—"
        await update.callback_query.edit_message_text(
            "🏢 Сколько этажей *в подъезде*?",
            parse_mode='Markdown',
            reply_markup=skip_keyboard()
        )
    else:
        context.user_data['new_apt']['floor'] = update.message.text
        await update.message.reply_text(
            "🏢 Сколько этажей *в подъезде*?",
            parse_mode='Markdown',
            reply_markup=skip_keyboard()
        )
    return ADD_TOTAL_FLOORS


async def add_total_floors(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
        data = update.callback_query.data
        if data == "cancel":
            await update.callback_query.edit_message_text("❌ Добавление отменено.")
            return ConversationHandler.END
        context.user_data['new_apt']['total_floors'] = "—"
        await update.callback_query.edit_message_text(
            "🏗 Сколько этажей *в доме* (здании)?",
            parse_mode='Markdown',
            reply_markup=skip_keyboard()
        )
    else:
        context.user_data['new_apt']['total_floors'] = update.message.text
        await update.message.reply_text(
            "🏗 Сколько этажей *в доме* (здании)?",
            parse_mode='Markdown',
            reply_markup=skip_keyboard()
        )
    return ADD_BUILDING_FLOORS


async def add_building_floors(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
        data = update.callback_query.data
        if data == "cancel":
            await update.callback_query.edit_message_text("❌ Добавление отменено.")
            return ConversationHandler.END
        context.user_data['new_apt']['building_floors'] = "—"
        await update.callback_query.edit_message_text(
            "🚪 Количество *комнат*?",
            reply_markup=rooms_add_keyboard()
        )
    else:
        context.user_data['new_apt']['building_floors'] = update.message.text
        await update.message.reply_text(
            "🚪 Количество *комнат*?",
            parse_mode='Markdown',
            reply_markup=rooms_add_keyboard()
        )
    return ADD_ROOMS


def rooms_add_keyboard():
    buttons = [
        [InlineKeyboardButton("1", callback_data="rooms_1"),
         InlineKeyboardButton("2", callback_data="rooms_2"),
         InlineKeyboardButton("3", callback_data="rooms_3"),
         InlineKeyboardButton("4+", callback_data="rooms_4")],
        [InlineKeyboardButton("❌ Отмена", callback_data="cancel")]
    ]
    return InlineKeyboardMarkup(buttons)


async def add_rooms(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "cancel":
        await query.edit_message_text("❌ Добавление отменено.")
        return ConversationHandler.END
    context.user_data['new_apt']['rooms'] = query.data.replace("rooms_", "")
    await query.edit_message_text(
        "💰 Введите *цену аренды* (в $):",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Отмена", callback_data="cancel")]])
    )
    return ADD_PRICE


async def add_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("❌ Добавление отменено.")
        return ConversationHandler.END
    context.user_data['new_apt']['price'] = update.message.text
    buttons = [
        [InlineKeyboardButton("✅ Есть мебель и техника", callback_data="furn_yes")],
        [InlineKeyboardButton("🚫 Без мебели", callback_data="furn_no")],
        [InlineKeyboardButton("❌ Отмена", callback_data="cancel")]
    ]
    await update.message.reply_text(
        "🛋 *Мебель и техника:*",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    return ADD_FURNITURE


async def add_furniture(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "cancel":
        await query.edit_message_text("❌ Добавление отменено.")
        return ConversationHandler.END
    context.user_data['new_apt']['furniture'] = "мебель, техника" if query.data == "furn_yes" else "нет"
    buttons = [
        [InlineKeyboardButton("✨ Евроремонт", callback_data="ren_euro"),
         InlineKeyboardButton("🏠 Обычный ремонт", callback_data="ren_standard")],
        [InlineKeyboardButton("🔧 Без ремонта", callback_data="ren_none"),
         InlineKeyboardButton("❌ Отмена", callback_data="cancel")]
    ]
    await query.edit_message_text(
        "🔧 *Тип ремонта:*",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    return ADD_RENOVATION


async def add_renovation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "cancel":
        await query.edit_message_text("❌ Добавление отменено.")
        return ConversationHandler.END
    mapping = {"ren_euro": "Евроремонт", "ren_standard": "Обычный", "ren_none": "Без ремонта"}
    context.user_data['new_apt']['renovation'] = mapping.get(query.data, "—")
    await query.edit_message_text(
        "📞 Введите *контакт* (имя и телефон владельца/агента):",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Отмена", callback_data="cancel")]])
    )
    return ADD_CONTACT


async def add_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("❌ Добавление отменено.")
        return ConversationHandler.END
    context.user_data['new_apt']['contact'] = update.message.text
    await update.message.reply_text(
        "📸 Отправьте *ссылки на фото* через запятую (или пропустите):\n\n"
        "Например: https://i.imgur.com/abc.jpg, https://i.imgur.com/xyz.jpg",
        parse_mode='Markdown',
        reply_markup=skip_keyboard()
    )
    return ADD_PHOTOS


async def add_photos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
        data = update.callback_query.data
        if data == "cancel":
            await update.callback_query.edit_message_text("❌ Добавление отменено.")
            return ConversationHandler.END
        context.user_data['new_apt']['photos'] = ""
        msg = update.callback_query
        send_func = msg.edit_message_text
    else:
        context.user_data['new_apt']['photos'] = update.message.text
        send_func = update.message.reply_text

    apt = context.user_data['new_apt']
    preview = (
        f"📋 *Проверьте данные квартиры:*\n\n"
        f"🔹 Район: {apt.get('district', '—')}\n"
        f"🔹 Локация: {apt.get('location', '—')}\n"
        f"🔹 Площадь: {apt.get('area', '—')} м²\n"
        f"🔹 Комнат: {apt.get('rooms', '—')}\n"
        f"🔹 Этаж: {apt.get('floor', '—')}/{apt.get('total_floors', '—')} "
        f"(дом {apt.get('building_floors', '—')} эт.)\n"
        f"🔹 Мебель и техника: {apt.get('furniture', '—')}\n"
        f"🔹 Ремонт: {apt.get('renovation', '—')}\n\n"
        f"🔥 Цена: *${apt.get('price', '—')}*\n"
        f"📞 Контакт: {apt.get('contact', '—')}\n"
        f"📸 Фото: {'есть' if apt.get('photos') else 'нет'}"
    )
    buttons = [
        [InlineKeyboardButton("✅ Сохранить", callback_data="confirm_save"),
         InlineKeyboardButton("❌ Отменить", callback_data="cancel")]
    ]
    await send_func(preview, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(buttons))
    return ADD_CONFIRM


async def add_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "cancel":
        await query.edit_message_text("❌ Добавление отменено.")
        return ConversationHandler.END

    apt = context.user_data['new_apt']
    apt_id = sheets.add_apartment(apt)
    await query.edit_message_text(
        f"✅ *Квартира #{apt_id} успешно добавлена в базу!*",
        parse_mode='Markdown'
    )
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Выберите следующее действие:",
        reply_markup=main_menu_keyboard()
    )
    return ConversationHandler.END


# ==================== ВСЕ КВАРТИРЫ ====================

async def all_apartments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔄 Загружаю все квартиры...")
    results = sheets.get_all_apartments()

    if not results:
        await update.message.reply_text(
            "📭 База квартир пуста. Добавьте первую квартиру!",
            reply_markup=main_menu_keyboard()
        )
        return

    await update.message.reply_text(f"📋 Всего квартир в базе: *{len(results)}*", parse_mode='Markdown')

    for apt in results[:15]:
        text = format_apartment(apt)
        await update.message.reply_text(text, parse_mode='Markdown')

    if len(results) > 15:
        await update.message.reply_text(f"... и ещё {len(results) - 15} квартир. Используйте поиск для фильтрации.")

    await update.message.reply_text("Выберите действие:", reply_markup=main_menu_keyboard())


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ Действие отменено.", reply_markup=main_menu_keyboard())
    return ConversationHandler.END


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Хендлер поиска
    search_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^🔍 Поиск квартиры$"), search_start)],
        states={
            SEARCH_DISTRICT: [CallbackQueryHandler(search_district)],
            SEARCH_PRICE_MIN: [
                CallbackQueryHandler(search_price_min),
                MessageHandler(filters.TEXT & ~filters.COMMAND, search_price_min)
            ],
            SEARCH_PRICE_MAX: [
                CallbackQueryHandler(search_price_max),
                MessageHandler(filters.TEXT & ~filters.COMMAND, search_price_max)
            ],
            SEARCH_ROOMS: [CallbackQueryHandler(search_rooms)],
            SEARCH_FURNITURE: [CallbackQueryHandler(search_furniture)],
            SEARCH_RENOVATION: [CallbackQueryHandler(search_renovation)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # Хендлер добавления
    add_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^➕ Добавить квартиру$"), add_start)],
        states={
            ADD_DISTRICT: [CallbackQueryHandler(add_district)],
            ADD_LOCATION: [
                CallbackQueryHandler(add_location),
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_location)
            ],
            ADD_AREA: [
                CallbackQueryHandler(add_area),
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_area)
            ],
            ADD_FLOOR: [
                CallbackQueryHandler(add_floor),
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_floor)
            ],
            ADD_TOTAL_FLOORS: [
                CallbackQueryHandler(add_total_floors),
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_total_floors)
            ],
            ADD_BUILDING_FLOORS: [
                CallbackQueryHandler(add_building_floors),
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_building_floors)
            ],
            ADD_ROOMS: [CallbackQueryHandler(add_rooms)],
            ADD_PRICE: [
                CallbackQueryHandler(add_price),
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_price)
            ],
            ADD_FURNITURE: [CallbackQueryHandler(add_furniture)],
            ADD_RENOVATION: [CallbackQueryHandler(add_renovation)],
            ADD_CONTACT: [
                CallbackQueryHandler(add_contact),
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_contact)
            ],
            ADD_PHOTOS: [
                CallbackQueryHandler(add_photos),
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_photos)
            ],
            ADD_CONFIRM: [CallbackQueryHandler(add_confirm)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(search_handler)
    app.add_handler(add_handler)
    app.add_handler(MessageHandler(filters.Regex("^📋 Все квартиры$"), all_apartments))
    app.add_handler(MessageHandler(filters.Regex("^❓ Помощь$"), help_command))

    logger.info("Бот запущен...")
    app.run_polling()


if __name__ == '__main__':
    main()
