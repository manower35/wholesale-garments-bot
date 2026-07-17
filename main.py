import sys
import logging
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes
)
import config
import db
import handlers_user
import handlers_admin

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

async def handle_text_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Router for all text messages (non-commands). Redirects based on user roles and states."""
    user_id = update.effective_user.id
    
    # 1. If user is admin, check if they are in admin menu or admin sub-conversation
    if db.is_admin(user_id):
        processed = await handlers_admin.handle_admin_text_messages(update, context)
        if processed:
            return
            
    # 2. Otherwise process as standard user message
    await handlers_user.handle_user_text_messages(update, context)

async def handle_photo_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Router for photo uploads. Primarily used by admins during product additions."""
    user_id = update.effective_user.id
    state = context.user_data.get("admin_state")
    
    if db.is_admin(user_id) and state == "prod_add_photo":
        await handlers_admin.process_product_add_photo(update, context)
    else:
        await update.message.reply_text(
            "📷 Thanks for the photo! To browse our catalog, please select '🛍️ Browse Catalog' from the main menu."
        )

async def handle_contact_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Router for sharing contacts. Used by customers during the checkout process."""
    state = context.user_data.get("state")
    if state == "awaiting_checkout_phone":
        await handlers_user.process_checkout_phone(update, context)
    else:
        user_id = update.effective_user.id
        await update.message.reply_text(
            "ℹ️ Contact received. What would you like to do?",
            reply_markup=handlers_user.get_main_menu_keyboard(user_id)
        )

async def handle_document_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Router for document uploads. Used by admins for bulk Excel product import."""
    user_id = update.effective_user.id
    state = context.user_data.get("admin_state")
    
    if db.is_admin(user_id) and state == "prod_import_excel":
        await handlers_admin.process_product_import_excel(update, context)
    else:
        await update.message.reply_text(
            "📁 Document received. To browse our catalog, please select '🛍️ Browse Catalog' from the main menu."
        )

async def handle_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Router for callback queries from inline keyboard buttons."""
    query = update.callback_query
    data = query.data
    
    # Route to admin callbacks if callback data begins with 'admin_'
    if data.startswith("admin_"):
        await handlers_admin.handle_admin_callback_query(update, context)
    else:
        await handlers_user.handle_callback_query(update, context)

def main():
    """Main function to initialize and run the Telegram Bot."""
    print("====================================================")
    print("     AT SELECTION Wholesale Garments Catalog Bot    ")
    print("====================================================")
    
    # 1. Initialize SQLite Database
    print("[*] Initializing Database...")
    db.init_db()
    print("[+] Database Initialized Successfully.")
    
    # 2. Check for Bot Token
    if not config.BOT_TOKEN or config.BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
        print("\n[!] ERROR: Telegram Bot Token is missing!")
        print("Please edit the '.env' file in this folder and add your token.")
        print("Example: BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ")
        print("\nGet a bot token by messaging @BotFather on Telegram.")
        sys.exit(1)
        
    print("[*] Starting Telegram Bot Engine...")
    
    # Check if admins are registered
    if not db.has_any_admin():
        print("\n[i] NOTICE: No Admin users registered yet.")
        print(f"    --> Send the message '{config.ADMIN_SETUP_TOKEN}' to your bot")
        print("    --> on Telegram to register yourself as the Admin owner.\n")
    else:
        admins = db.get_admins()
        print(f"[i] Registered Admins (IDs): {', '.join(str(a['user_id']) for a in admins)}")
        
    # 3. Create Bot Application
    app = ApplicationBuilder().token(config.BOT_TOKEN).build()
    
    # 4. Register command handlers
    app.add_handler(CommandHandler("start", handlers_user.start_command))
    app.add_handler(CommandHandler("help", handlers_user.start_command))
    app.add_handler(CommandHandler("menu", handlers_user.start_command))
    app.add_handler(CommandHandler("reset", handlers_user.reset_memory_command))
    app.add_handler(CommandHandler("stock", handlers_user.stock_summary_command))
    app.add_handler(CommandHandler("summary", handlers_user.stock_summary_command))
    
    # 5. Register media and text handlers
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_messages))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo_messages))
    app.add_handler(MessageHandler(filters.CONTACT, handle_contact_messages))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document_messages))
    
    # 6. Register button callbacks
    app.add_handler(CallbackQueryHandler(handle_callbacks))
    
    print("[+] Bot is running... Press Ctrl+C to stop.")
    print("====================================================")
    
    # 7. Start polling
    app.run_polling()

if __name__ == "__main__":
    main()
