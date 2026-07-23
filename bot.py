import os
import logging
import sys
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# --- Configuration ---
TOKEN = os.environ.get("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN environment variable not set!")

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Simple in-memory storage (Resets on Railway restart)
user_notes = {}

# --- Helper Functions ---
def get_notes(user_id):
    """Retrieve notes dictionary for a user."""
    if user_id not in user_notes:
        user_notes[user_id] = {}
    return user_notes[user_id]

# --- Command Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a welcome message and instructions."""
    user = update.effective_user
    await update.message.reply_text(
        f"Hello {user.first_name}!\n"
        "I am your personal wiki bot. You can store and retrieve information.\n\n"
        "Commands:\n"
        "/save <key> <value> - Save information\n"
        "/get <key> - Retrieve information\n"
        "/delete <key> - Delete a key\n"
        "/list - List all your saved keys\n"
        "/search <term> - Search keys and values\n\n"
        "Or use the buttons below:",
        reply_markup=main_menu_keyboard()
    )

def main_menu_keyboard():
    """Create the main menu inline keyboard."""
    keyboard = [
        [InlineKeyboardButton("📝 Save Note", callback_data='save')],
        [InlineKeyboardButton("🔍 Get Note", callback_data='get')],
        [InlineKeyboardButton("📋 List All", callback_data='list')],
        [InlineKeyboardButton("🗑️ Delete Note", callback_data='delete')],
        [InlineKeyboardButton("🔎 Search", callback_data='search')],
    ]
    return InlineKeyboardMarkup(keyboard)

async def save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Save a key-value pair."""
    user_id = update.effective_user.id
    args = context.args

    if len(args) < 2:
        await update.message.reply_text(
            "Usage: /save <key> <value>\n"
            "Example: /save birthday 1990-01-01"
        )
        return

    key = args[0]
    value = " ".join(args[1:])
    notes = get_notes(user_id)
    notes[key] = value
    await update.message.reply_text(f"✅ Saved: '{key}' = '{value}'")

async def get_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Retrieve a value by key."""
    user_id = update.effective_user.id
    args = context.args

    if not args:
        await update.message.reply_text("Usage: /get <key>")
        return

    key = args[0]
    notes = get_notes(user_id)
    if key in notes:
        await update.message.reply_text(f"📖 {key} = {notes[key]}")
    else:
        await update.message.reply_text(f"❌ Key '{key}' not found.")

async def delete_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete a key."""
    user_id = update.effective_user.id
    args = context.args

    if not args:
        await update.message.reply_text("Usage: /delete <key>")
        return

    key = args[0]
    notes = get_notes(user_id)
    if key in notes:
        del notes[key]
        await update.message.reply_text(f"🗑️ Deleted key: '{key}'")
    else:
        await update.message.reply_text(f"❌ Key '{key}' not found.")

async def list_notes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all saved keys."""
    user_id = update.effective_user.id
    notes = get_notes(user_id)

    if not notes:
        await update.message.reply_text("📭 You have no saved notes.")
        return

    keys = list(notes.keys())
    if len(keys) <= 50:
        await update.message.reply_text("📋 Your keys:\n" + "\n".join(keys))
    else:
        for i in range(0, len(keys), 50):
            chunk = keys[i:i+50]
            await update.message.reply_text("📋 Keys (continued):\n" + "\n".join(chunk))

async def search_notes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Search for a term in keys and values."""
    user_id = update.effective_user.id
    args = context.args

    if not args:
        await update.message.reply_text("Usage: /search <term>")
        return

    term = " ".join(args).lower()
    notes = get_notes(user_id)
    results = []

    for key, value in notes.items():
        if term in key.lower() or term in value.lower():
            results.append(f"{key}: {value}")

    if results:
        result_text = "\n".join(results[:20])
        if len(results) > 20:
            result_text += f"\n... and {len(results) - 20} more."
        await update.message.reply_text(f"🔎 Found {len(results)} results:\n{result_text}")
    else:
        await update.message.reply_text(f"🔎 No results found for '{term}'.")

# --- Callback Query Handler ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline button presses."""
    query = update.callback_query
    await query.answer()

    action = query.data

    if action == 'save':
        await query.message.reply_text("Please use the command: /save <key> <value>")
    elif action == 'get':
        await query.message.reply_text("Please use the command: /get <key>")
    elif action == 'list':
        await list_notes(update, context)
    elif action == 'delete':
        await query.message.reply_text("Please use the command: /delete <key>")
    elif action == 'search':
        await query.message.reply_text("Please use the command: /search <term>")

# --- Error Handler ---
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log errors."""
    logger.warning(f"Update {update} caused error {context.error}")

# --- Main Function with Python 3.13 Fix ---
def main():
    """Start the bot with Python 3.13 compatibility."""
    # Workaround for Python 3.13 attribute error
    import telegram.ext._updater
    if not hasattr(telegram.ext._updater.Updater, '_Updater__polling_cleanup_cb'):
        # Create a dummy attribute to avoid the error
        telegram.ext._updater.Updater._Updater__polling_cleanup_cb = None
    
    # Create the Application
    application = Application.builder().token(TOKEN).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("save", save))
    application.add_handler(CommandHandler("get", get_note))
    application.add_handler(CommandHandler("delete", delete_note))
    application.add_handler(CommandHandler("list", list_notes))
    application.add_handler(CommandHandler("search", search_notes))

    # Add callback query handler
    application.add_handler(CallbackQueryHandler(button_handler))

    # Add error handler
    application.add_error_handler(error_handler)

    # Start the Bot
    print("Bot is running...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
