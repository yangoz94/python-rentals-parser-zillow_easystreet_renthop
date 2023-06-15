from app import bot

if __name__ == '__main__':
    # Polling
    print("Now polling...")
    bot.run_polling(poll_interval=3)