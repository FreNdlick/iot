import asyncio
import threading
from Telgram_bot.Bot_telegram import main  # Импортируем main() из бота

def start_bot():
    """Функция запуска бота в отдельном потоке, используя asyncio"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main())
    except Exception as e:
        print(f"Ошибка в Telegram-боте: {e}")
    finally:
        loop.close()

def run_bot_in_thread():
    """Создает поток для запуска бота"""
    bot_thread = threading.Thread(target=start_bot, name="TelegramBotThread", daemon=True)
    bot_thread.start()
    return bot_thread
