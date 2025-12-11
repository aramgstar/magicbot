import telebot
from config import TELEGRAM_TOKEN

# один общий экземпляр бота для всего проекта
bot = telebot.TeleBot(TELEGRAM_TOKEN, parse_mode="HTML")
