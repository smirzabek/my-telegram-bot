# bot.py
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters
)
import json
import os

# Logging sozlamalari
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Ma'lumotlar fayli
DATA_FILE = 'bot_data.json'
ADMIN_FILE = 'admins.json'

# Ma'lumotlarni yuklash
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, ValueError):
            return {'topics': [], 'user_selections': {}}
    return {'topics': [], 'user_selections': {}}

# Ma'lumotlarni saqlash
def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# Adminlarni yuklash
def load_admins():
    if os.path.exists(ADMIN_FILE):
        try:
            with open(ADMIN_FILE, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if content:
                    return json.loads(content)
                else:
                    default_admins = {'admin_ids': []}
                    save_admins(default_admins)
                    return default_admins
        except (json.JSONDecodeError, ValueError):
            default_admins = {'admin_ids': []}
            save_admins(default_admins)
            return default_admins
    else:
        default_admins = {'admin_ids': []}
        save_admins(default_admins)
        return default_admins

# Adminlarni saqlash
def save_admins(admins):
    with open(ADMIN_FILE, 'w', encoding='utf-8') as f:
        json.dump(admins, f, ensure_ascii=False, indent=2)

# Admin tekshirish
def is_admin(user_id):
    admins = load_admins()
    return user_id in admins['admin_ids']

# Foydalanuvchi ma'lumotlarini olish
async def get_user_info(context, user_id):
    try:
        user = await context.bot.get_chat(user_id)
        username = f"@{user.username}" if user.username else "username yo'q"
        return f"{user.first_name} {user.last_name or ''} ({username})"
    except:
        return f"User ID: {user_id}"

# /start komandasi
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = str(user.id)
    
    data = load_data()
    
    if user_id not in data['user_selections']:
        data['user_selections'][user_id] = []
        save_data(data)
    
    keyboard = [
        [InlineKeyboardButton("📋 Mavzularni ko'rish", callback_data='view_topics')],
        [InlineKeyboardButton("✅ Tanlangan mavzularim", callback_data='my_selections')]
    ]
    
    if is_admin(user.id):
        keyboard.append([InlineKeyboardButton("⚙️ Admin panel", callback_data='admin_panel')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"Assalomu alaykum, {user.first_name}! 👋\n\n"
        "Siz ko'pi bilan 2 ta mavzu tanlashingiz mumkin.\n"
        "Quyidagi tugmalardan birini tanlang:",
        reply_markup=reply_markup
    )

# Mavzularni ko'rish
async def view_topics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    data = load_data()
    
    if not data['topics']:
        keyboard = [[InlineKeyboardButton("🔙 Orqaga", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "Hozircha mavzular mavjud emas. ❌\n"
            "Admin tomonidan mavzular qo'shilishini kuting.",
            reply_markup=reply_markup
        )
        return
    
    user_selections = data['user_selections'].get(user_id, [])
    
    keyboard = []
    for topic in data['topics']:
        topic_id = topic['id']
        topic_name = topic['name']
        is_selected = topic_id in user_selections
        
        # Mavzu band qilinganmi tekshirish
        selected_count = sum(1 for selections in data['user_selections'].values() 
                           if topic_id in selections)
        is_full = selected_count >= topic['capacity']
        
        if is_selected:
            button_text = f"✅ {topic_name} ({selected_count}/{topic['capacity']})"
        elif is_full:
            button_text = f"🔒 {topic_name} (To'lgan)"
        else:
            button_text = f"⚪ {topic_name} ({selected_count}/{topic['capacity']})"
        
        keyboard.append([InlineKeyboardButton(
            button_text, 
            callback_data=f"toggle_{topic_id}"
        )])
    
    keyboard.append([InlineKeyboardButton("🔙 Orqaga", callback_data='back_to_menu')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"Mavzular ro'yxati:\n\n"
        f"Siz {len(user_selections)}/2 ta mavzu tanladingiz.\n"
        f"Mavzuni tanlash/bekor qilish uchun ustiga bosing:",
        reply_markup=reply_markup
    )

# Mavzuni tanlash/bekor qilish
async def toggle_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    topic_id = int(query.data.split('_')[1])
    user_id = str(query.from_user.id)
    
    data = load_data()
    user_selections = data['user_selections'].get(user_id, [])
    
    # Mavzuni topish
    topic = next((t for t in data['topics'] if t['id'] == topic_id), None)
    if not topic:
        await query.answer("Mavzu topilmadi!", show_alert=True)
        return
    
    if topic_id in user_selections:
        # Mavzuni bekor qilish
        user_selections.remove(topic_id)
        data['user_selections'][user_id] = user_selections
        save_data(data)
        await query.answer("Mavzu bekor qilindi! ❌")
    else:
        # Yangi mavzu qo'shish
        if len(user_selections) >= 2:
            await query.answer(
                "Siz allaqachon 2 ta mavzu tanlagansiz!\n"
                "Yangi mavzu tanlash uchun avval birontasini bekor qiling.",
                show_alert=True
            )
            await view_topics(update, context)
            return
        
        # Mavzu to'lganmi tekshirish
        selected_count = sum(1 for selections in data['user_selections'].values() 
                           if topic_id in selections)
        if selected_count >= topic['capacity']:
            await query.answer("Bu mavzu allaqachon to'lgan! 🔒", show_alert=True)
            await view_topics(update, context)
            return
        
        user_selections.append(topic_id)
        data['user_selections'][user_id] = user_selections
        save_data(data)
        await query.answer("Mavzu tanlandi! ✅")
    
    # Yangilangan ro'yxatni ko'rsatish
    await view_topics(update, context)

# Tanlangan mavzularni ko'rish
async def my_selections(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    data = load_data()
    user_selections = data['user_selections'].get(user_id, [])
    
    if not user_selections:
        text = "Siz hali hech qanday mavzu tanlamadingiz. ❌"
    else:
        text = "Sizning tanlangan mavzularingiz:\n\n"
        for topic_id in user_selections:
            topic = next((t for t in data['topics'] if t['id'] == topic_id), None)
            if topic:
                text += f"✅ {topic['name']}\n"
    
    keyboard = [[InlineKeyboardButton("🔙 Orqaga", callback_data='back_to_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup)

# Admin panel
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if not is_admin(query.from_user.id):
        await query.answer("Sizda admin huquqi yo'q!", show_alert=True)
        return
    
    keyboard = [
        [InlineKeyboardButton("➕ Mavzu qo'shish", callback_data='admin_add_topic')],
        [InlineKeyboardButton("🗑 Mavzu o'chirish", callback_data='admin_delete_topic')],
        [InlineKeyboardButton("📊 Statistika", callback_data='admin_stats')],
        [InlineKeyboardButton("👥 Kim qaysi mavzuni tanlagan", callback_data='admin_users_topics')],
        [InlineKeyboardButton("🔙 Orqaga", callback_data='back_to_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "⚙️ Admin Panel\n\n"
        "Kerakli amalni tanlang:",
        reply_markup=reply_markup
    )

# Mavzu qo'shish
async def admin_add_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    context.user_data['admin_action'] = 'add_topic'
    
    keyboard = [[InlineKeyboardButton("❌ Bekor qilish", callback_data='admin_panel')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "Yangi mavzu qo'shish:\n\n"
        "Mavzu nomini va sig'imini quyidagi formatda yuboring:\n"
        "<b>Mavzu nomi | Sig'im</b>\n\n"
        "Misol: Python dasturlash | 30",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

# Mavzu o'chirish
async def admin_delete_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = load_data()
    
    if not data['topics']:
        await query.answer("O'chiriladigan mavzular yo'q!", show_alert=True)
        return
    
    keyboard = []
    for topic in data['topics']:
        keyboard.append([InlineKeyboardButton(
            f"🗑 {topic['name']}", 
            callback_data=f"delete_{topic['id']}"
        )])
    
    keyboard.append([InlineKeyboardButton("🔙 Orqaga", callback_data='admin_panel')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "O'chiriladigan mavzuni tanlang:",
        reply_markup=reply_markup
    )

# Mavzuni o'chirish tasdiqlash
async def confirm_delete_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    topic_id = int(query.data.split('_')[1])
    data = load_data()
    
    # Mavzuni o'chirish
    data['topics'] = [t for t in data['topics'] if t['id'] != topic_id]
    
    # Foydalanuvchilardan ham o'chirish
    for user_id in data['user_selections']:
        if topic_id in data['user_selections'][user_id]:
            data['user_selections'][user_id].remove(topic_id)
    
    save_data(data)
    
    await query.answer("Mavzu o'chirildi! ✅")
    await admin_panel(update, context)

# Statistika
async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = load_data()
    
    text = "📊 Statistika:\n\n"
    text += f"Jami mavzular: {len(data['topics'])}\n"
    text += f"Jami foydalanuvchilar: {len(data['user_selections'])}\n\n"
    
    if data['topics']:
        text += "Mavzular bo'yicha:\n"
        for topic in data['topics']:
            count = sum(1 for selections in data['user_selections'].values() 
                       if topic['id'] in selections)
            text += f"• {topic['name']}: {count}/{topic['capacity']}\n"
    else:
        text += "Hozircha mavzular yo'q."
    
    keyboard = [[InlineKeyboardButton("🔙 Orqaga", callback_data='admin_panel')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup)

# Kim qaysi mavzuni tanlagan
async def admin_users_topics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = load_data()
    
    if not data['topics']:
        await query.answer("Hozircha mavzular yo'q!", show_alert=True)
        return
    
    keyboard = []
    for topic in data['topics']:
        count = sum(1 for selections in data['user_selections'].values() 
                   if topic['id'] in selections)
        keyboard.append([InlineKeyboardButton(
            f"👥 {topic['name']} ({count})", 
            callback_data=f"viewusers_{topic['id']}"
        )])
    
    keyboard.append([InlineKeyboardButton("🔙 Orqaga", callback_data='admin_panel')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "📋 Qaysi mavzu foydalanuvchilarini ko'rmoqchisiz?",
        reply_markup=reply_markup
    )

# Mavzu foydalanuvchilarini ko'rish
async def view_topic_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Foydalanuvchilar yuklanmoqda...")
    
    topic_id = int(query.data.split('_')[1])
    data = load_data()
    
    # Mavzuni topish
    topic = next((t for t in data['topics'] if t['id'] == topic_id), None)
    if not topic:
        await query.answer("Mavzu topilmadi!", show_alert=True)
        return
    
    # Bu mavzuni tanlagan foydalanuvchilarni topish
    users_with_topic = []
    for user_id, selections in data['user_selections'].items():
        if topic_id in selections:
            users_with_topic.append(user_id)
    
    if not users_with_topic:
        text = f"📋 {topic['name']}\n\n"
        text += "Hozircha hech kim tanlamagan. ❌"
    else:
        text = f"📋 {topic['name']}\n"
        text += f"Sig'im: {len(users_with_topic)}/{topic['capacity']}\n\n"
        text += "Tanlagan foydalanuvchilar:\n\n"
        
        for i, user_id in enumerate(users_with_topic, 1):
            user_info = await get_user_info(context, int(user_id))
            text += f"{i}. {user_info}\n"
    
    keyboard = [
        [InlineKeyboardButton("🔙 Mavzularga qaytish", callback_data='admin_users_topics')],
        [InlineKeyboardButton("🏠 Admin panel", callback_data='admin_panel')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup)

# Matn xabarlarini qayta ishlash
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'admin_action' not in context.user_data:
        return
    
    if context.user_data['admin_action'] == 'add_topic':
        try:
            parts = update.message.text.split('|')
            if len(parts) != 2:
                await update.message.reply_text(
                    "❌ Noto'g'ri format! Qaytadan urinib ko'ring:\n"
                    "<b>Mavzu nomi | Sig'im</b>\n\n"
                    "Misol: Python dasturlash | 30",
                    parse_mode='HTML'
                )
                return
            
            topic_name = parts[0].strip()
            capacity = int(parts[1].strip())
            
            if capacity <= 0:
                await update.message.reply_text(
                    "❌ Sig'im 0 dan katta bo'lishi kerak!"
                )
                return
            
            data = load_data()
            new_id = max([t['id'] for t in data['topics']], default=0) + 1
            
            data['topics'].append({
                'id': new_id,
                'name': topic_name,
                'capacity': capacity
            })
            save_data(data)
            
            # Admin panelni qayta ko'rsatish
            context.user_data.pop('admin_action')
            
            keyboard = [
                [InlineKeyboardButton("➕ Yana mavzu qo'shish", callback_data='admin_add_topic')],
                [InlineKeyboardButton("📊 Statistika", callback_data='admin_stats')],
                [InlineKeyboardButton("🏠 Admin panel", callback_data='admin_panel')],
                [InlineKeyboardButton("🔙 Bosh menyu", callback_data='back_to_menu')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"✅ Mavzu muvaffaqiyatli qo'shildi!\n\n"
                f"📌 Nomi: {topic_name}\n"
                f"👥 Sig'im: {capacity}\n\n"
                f"Keyingi amalingizni tanlang:",
                reply_markup=reply_markup
            )
            
        except ValueError:
            await update.message.reply_text(
                "❌ Sig'im raqam bo'lishi kerak! Qaytadan urinib ko'ring."
            )

# Orqaga qaytish
async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # Admin action tozalash
    if 'admin_action' in context.user_data:
        context.user_data.pop('admin_action')
    
    user = query.from_user
    keyboard = [
        [InlineKeyboardButton("📋 Mavzularni ko'rish", callback_data='view_topics')],
        [InlineKeyboardButton("✅ Tanlangan mavzularim", callback_data='my_selections')]
    ]
    
    if is_admin(user.id):
        keyboard.append([InlineKeyboardButton("⚙️ Admin panel", callback_data='admin_panel')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"Assalomu alaykum, {user.first_name}! 👋\n\n"
        "Siz ko'pi bilan 2 ta mavzu tanlashingiz mumkin.\n"
        "Quyidagi tugmalardan birini tanlang:",
        reply_markup=reply_markup
    )

# Asosiy funksiya
def main():
    # Tokenni o'zingiznikiga almashtiring
    TOKEN = "8386948821:AAH_5h8zMPeqGklXkkfM0k0xZ5qNaQc4Sa8"
    
    application = Application.builder().token(TOKEN).build()
    
    # Handlerlar
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(view_topics, pattern='^view_topics$'))
    application.add_handler(CallbackQueryHandler(my_selections, pattern='^my_selections$'))
    application.add_handler(CallbackQueryHandler(toggle_topic, pattern='^toggle_'))
    application.add_handler(CallbackQueryHandler(admin_panel, pattern='^admin_panel$'))
    application.add_handler(CallbackQueryHandler(admin_add_topic, pattern='^admin_add_topic$'))
    application.add_handler(CallbackQueryHandler(admin_delete_topic, pattern='^admin_delete_topic$'))
    application.add_handler(CallbackQueryHandler(confirm_delete_topic, pattern='^delete_'))
    application.add_handler(CallbackQueryHandler(admin_stats, pattern='^admin_stats$'))
    application.add_handler(CallbackQueryHandler(admin_users_topics, pattern='^admin_users_topics$'))
    application.add_handler(CallbackQueryHandler(view_topic_users, pattern='^viewusers_'))
    application.add_handler(CallbackQueryHandler(back_to_menu, pattern='^back_to_menu$'))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Botni ishga tushirish
    print("✅ Bot ishga tushdi...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
