import os
import json
import requests
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

load_dotenv()


class TelegramBot:
    def __init__(self):
        self.bot = Application.builder().token(os.environ["TELEGRAM_API_TOKEN"]).build()
        self.setup_handlers()

    def setup_handlers(self):
        # Commands
        self.bot.add_handler(CommandHandler("start", self.start_command))
        self.bot.add_handler(CommandHandler("help", self.help_command))
        self.bot.add_handler(CommandHandler("add", self.add_command))

        # Messages
        self.bot.add_handler(MessageHandler(filters.TEXT, self.handle_message))

        # Errors
        self.bot.add_error_handler(self.error)

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if self.check_authorization(update):
            await update.message.reply_text("Howdy, send me the URL of the listing you want to parse :)")
        else:
            await update.message.reply_text("You are not authorized to use this bot. Sorry :(")

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "I am a bot programmed to help with apartment search in NYC, BUT only if you are "
            "an authorized user. For example, /add https://streeteasy.com/rental/1234567")

    async def add_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.check_authorization(update):
            await update.message.reply_text("You are not authorized to use this bot. Sorry :(")
            return

        if len(context.args) == 0:
            await update.message.reply_text("Please provide a listing URL.")
        elif len(context.args) >= 2:
            await update.message.reply_text("Too many arguments. Please provide only one listing URL as a single word "
                                            "with no space.")
        else:
            url = context.args[0]
            response = self.handle_response(url)
            await update.message.reply_text(response)

    def check_authorization(self, update: Update) -> bool:
        authorized_ids = os.getenv("TELEGRAM_BOT_CHAT_IDS")
        if str(update.message.chat_id) not in authorized_ids:
            print(f"Unauthorized user {update.message.chat_id} tried to access the bot.")
            return False
        print(f"Authorized user {update.message.chat_id} accessed the bot.")
        return True

    def handle_response(self, url: str) -> str:
        try:
            headers = {
                'Content-Type': 'application/json',
            }
            api_response = requests.post(f'{os.getenv("BASE_URL")}/api/parse-listing', json={'url': url},
                                         headers=headers)
            if api_response.status_code == 200:
                parsed_data = api_response.json()
                formatted_data = json.dumps(parsed_data, indent=4)
                return f"Successfully parsed and added the following listing to the Google Sheet:\n\n{formatted_data}"
            else:
                return f"Failed to parse listing: {api_response.text}"
        except Exception as e:
            return f"Error: Failed to parse listing: {str(e)}"

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text
        parsed_text = text.split()
        command = parsed_text[0].lower()
        if len(parsed_text) >= 1 and command == '/add':
            url = parsed_text[1]
            response = self.handle_response(url)
            await update.message.reply_text(response)
        else:
            await update.message.reply_text("I don't understand that command. Please try again.")

    async def error(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        print(f"Update {update} caused error {context.error}")

    def start_the_bot(self):
        print("Starting the bot...")

        # Set up webhook
        webhook_key = os.environ["WEBHOOK_KEY"]

        # Set up webhook URL
        webhook_url = f"{os.getenv('BASE_URL')}/{webhook_key}"
        print(webhook_url)

        # Set up webhook
        self.bot.run_webhook(webhook_url)

