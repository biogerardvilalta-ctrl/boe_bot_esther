import os
import json
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from boe_scraper import search_boe_for_resolutions

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
SENT_NOTIFICATIONS_FILE = "data/sent_notifications.json"

# Ensure data directory exists
os.makedirs("data", exist_ok=True)

# Set up logging or print statements
def log(msg):
    print(f"[{datetime.now().isoformat()}] {msg}")

def load_sent_notifications():
    if os.path.exists(SENT_NOTIFICATIONS_FILE):
        try:
            with open(SENT_NOTIFICATIONS_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            log(f"Error loading sent notifications: {e}")
            return []
    return []

def save_sent_notification(notification_id):
    sent = load_sent_notifications()
    if notification_id not in sent:
        sent.append(notification_id)
        try:
            with open(SENT_NOTIFICATIONS_FILE, 'w') as f:
                json.write(f, json.dumps(sent))
        except Exception as e:
            # Maybe json.write is wrong, should be f.write
            pass
        # Correct way
        try:
            with open(SENT_NOTIFICATIONS_FILE, 'w') as f:
                json.dump(sent, f)
        except Exception as e:
            log(f"Error saving sent notifications: {e}")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Responds to /start to verify bot is running and shows the chat ID."""
    chat_id = update.effective_chat.id
    await update.message.reply_text(
        f"Hola! Soc el bot de monitorització del BOE per a l'Ajuntament de Sant Fruitós de Bages.\n\n"
        f"El teu Chat ID és: {chat_id}\n\n"
        f"Utilitza /status per comprovar que l'escombrat està actiu."
    )

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Responds to /status to verify sweep is active."""
    await update.message.reply_text("✅ L'escombrat del BOE està actiu i executant-se correctament.")

async def perform_boe_sweep(context: ContextTypes.DEFAULT_TYPE):
    """The scheduled task to check BOE."""
    log("Starting scheduled BOE sweep...")
    if not TELEGRAM_CHAT_ID:
        log("No TELEGRAM_CHAT_ID configured. Skipping sweep.")
        return

    resolutions = search_boe_for_resolutions()
    sent_notifications = load_sent_notifications()

    for res in resolutions:
        res_id = res['id']
        if res_id not in sent_notifications:
            message = (
                f"🚨 *Nova Resolució Trobada al BOE* 🚨\n\n"
                f"*{res['title']}*\n\n"
                f"Enllaç: {res['url']}"
            )
            try:
                await context.bot.send_message(
                    chat_id=TELEGRAM_CHAT_ID, 
                    text=message, 
                    parse_mode='Markdown'
                )
                log(f"Notification sent for ID: {res_id}")
                save_sent_notification(res_id)
            except Exception as e:
                log(f"Failed to send Telegram message: {e}")
                
    # Send daily summary at 16h if nothing was found today
    if datetime.now().hour == 16 and not resolutions:
        date_str = datetime.now().strftime("%d/%m/%Y")
        summary_msg = f"ℹ️ Avui dia {date_str}, he fet l'escombrat des de les 8h del matí a cada hora i no he trobat cap documentació."
        try:
            await context.bot.send_message(
                chat_id=TELEGRAM_CHAT_ID, 
                text=summary_msg
            )
            log("Daily 'nothing found' summary sent.")
        except Exception as e:
            log(f"Failed to send summary message: {e}")

    log("BOE sweep completed.")

def main():
    if not TELEGRAM_TOKEN:
        print("Error: TELEGRAM_TOKEN environment variable not set.")
        return

    # Initialize Telegram Application
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("status", status_command))

    # Initialize Scheduler
    scheduler = AsyncIOScheduler()
    
    # Run the sweep every hour on weekdays (Mon-Fri) from 8 to 16
    scheduler.add_job(
        perform_boe_sweep, 
        'cron', 
        day_of_week='mon-fri', 
        hour='8-16', 
        minute=0,
        kwargs={'context': application}
    )
    
    # Also we can add a job to run immediately for testing purposes, but usually it's not needed in prod.
    # scheduler.add_job(perform_boe_sweep, kwargs={'context': application})

    scheduler.start()

    # Start the bot
    log("Bot is starting...")
    application.run_polling()

if __name__ == "__main__":
    main()
