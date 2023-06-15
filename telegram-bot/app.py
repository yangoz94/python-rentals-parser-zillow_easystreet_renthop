import os
import json
import requests
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

load_dotenv()


# Commands
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if check_authorization(update):
        await update.message.reply_text("Howdy, send me the URL of the listing you want to parse :)")
    else:
        await update.message.reply_text("You are not authorized to use this bot. Sorry :(")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("I am a bot programmed to help with apartment search in NYC, BUT only if you are "
                                    "an authorized user. For example, /add https://streeteasy.com/rental/1234567")


async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_authorization(update):
        await update.message.reply_text("You are not authorized to use this bot. Sorry :(")
        return

    if len(context.args) == 0:
        await update.message.reply_text("Please provide a listing URL.")
    elif len(context.args) >= 2:
        await update.message.reply_text("Too many arguments. Please provide only one listing URL as a single word "
                                        "with no space.")
    else:
        url = context.args[0]
        response = handle_response(url)
        await update.message.reply_text(response)


# Responses

def check_authorization(update: Update) -> bool:
    authorized_ids = os.getenv("TELEGRAM_BOT_CHAT_IDS")
    if str(update.message.chat_id) not in authorized_ids:
        print(f"Unauthorized user {update.message.chat_id} tried to access the bot.")
        return False
    print(f"Authorized user {update.message.chat_id} accessed the bot.")
    return True


def handle_response(url: str) -> str:
    try:
        headers = {
            'Content-Type': 'application/json',
        }
        api_response = requests.post(f'{os.getenv("BASE_URL")}/api/parse-listing', json={'url': url}, headers=headers)
        if api_response.status_code == 200:
            parsed_data = api_response.json()
            formatted_data = json.dumps(parsed_data, indent=4)
            return f"Successfully parsed and added the following listing to the Google Sheet:\n\n{formatted_data}"
        else:
            return f"Failed to parse listing: {api_response.text}"
    except Exception as e:
        return f"Error: Failed to parse listing: {str(e)}"


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    parsed_text = text.split()
    command = parsed_text[0].lower()
    if len(parsed_text) >= 1 and command == '/add':
        url = parsed_text[1]
        response = handle_response(url)
        await update.message.reply_text(response)
    else:
        await update.message.reply_text("I don't understand that command. Please try again.")


async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"Update {update} caused error {context.error}")

# NOTE: DO NOT WRAP THE FOLLOWING BLOCK WITH IF __main__ == '__main__' as it would cause an import error since
# wsgi.py is run mainly by gunicorn Main
print("Starting the bot...")
bot = Application.builder().token(os.environ["TELEGRAM_API_TOKEN"]).build()

# Commands
bot.add_handler(CommandHandler("start", start_command))
bot.add_handler(CommandHandler("help", help_command))
bot.add_handler(CommandHandler("add", add_command))

# Messages
bot.add_handler(MessageHandler(filters.TEXT, handle_message))

# Errors
bot.add_error_handler(error)

# Polling
print("Now polling...")
bot.run_polling(poll_interval=3)
