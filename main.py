import os
import telebot as tb
from dotenv import load_dotenv
import requests
import time
import re
import logging


# Настройка логирования
logging.basicConfig(
    filename="bot.log",
    level=logging.ERROR,
    format="%(asctime)s %(levelname)s %(message)s",
)

# Загрузка переменных окружения
load_dotenv()

# Получение секретного ключа
secret_key = os.getenv("MY_SECRET_KEY")

# Создание экземпляра бота
bot = tb.TeleBot(os.getenv("BOT_TOKEN"))


# Обработчик команды /start
@bot.message_handler(commands=['start'])
def start_message(message):
    # Приветственное сообщение
    bot.send_message(message.chat.id, 'Welcome.')


# Обработчик текстовых сообщений
@bot.message_handler(content_types=['text'])
def message_reply(message):
    # Ответ на текстовые сообщения
    bot.send_message(message.chat.id, "Please, send an audio file.")


# Обработчик аудио сообщений
@bot.message_handler(content_types=['audio'])
def work(message):
    try:
        # Имя аудиофайла
        file_name = message.audio.file_name
        # Уведомление о получении файла
        bot.send_message(message.chat.id, f"Working on \n<b>{file_name}</b>", parse_mode='HTML')

        # Функция для получения результатов транскрибации
        def get_results(config):
            endpoint = "https://api.speechtext.ai/results?"  # Эндпоинт для проверки статуса задачи
            while True:
                results = requests.get(endpoint, params=config).json()
                if "status" not in results:
                    break
                print("Task status: {}".format(results["status"]))
                if results["status"] == 'failed':
                    print("The task has failed: {}".format(results))
                    break
                if results["status"] == 'finished':
                    break
                time.sleep(1)
            return results

        # Загрузка аудиофайла в память
        with open(file_name, mode="rb") as file:
            post_body = file.read()

        # Настройки задачи транскрибации
        config = {
            "key": secret_key,
            "language": "en-US",
            "punctuation": True,
            "format": "m4a"
        }

        # Отправка запроса на транскрибацию аудио
        r = requests.post("https://api.speechtext.ai/recognize?", headers={'Content-Type': "application/octet-stream"}, params=config, data=post_body).json()

        # Получение ID задачи распознавания речи
        task = r["id"]

        # Получение результатов транскрибации
        config = {
            "key": secret_key,
            "task": task,
            "summary": True,
            "summary_size": 15,
            "highlights": True,
            "max_keywords": 10
        }

        # Получение субтитров в формате SRT или VTT
        config = {
            "key": secret_key,
            "task": task,
            "output": "srt",
            "max_caption_words": 15
        }

        subtitles = get_results(config)
        bot.send_message(message.chat.id, subtitles.split('\n')[2])

    except Exception as e:
        # Логирование ошибки
        logging.error(f"Error processing audio file: {e}")
        # Отправка сообщения об ошибке пользователю
        bot.send_message(message.chat.id, "Something went wrong :(\nTry again.")


# Обработчик голосовых сообщений
@bot.message_handler(content_types=['voice'])
def cluck(message):
    try:
        file_info = bot.get_file(message.voice.file_id)
        sausage = file_info.file_path
        file_name = re.search(r'voice/(.*?).oga', sausage)
        if file_name:
            file_name = file_name.group(1)
        else:
            print("no file")
        downloaded_file = bot.download_file(file_info.file_path)
        with open(file_name, 'wb') as new_file:
            new_file.write(downloaded_file)
        bot.send_message(message.chat.id, f"Working on \n<b>your voice message</b>", parse_mode='HTML')

        def get_results(config):
            endpoint = "https://api.speechtext.ai/results?"
            while True:
                results = requests.get(endpoint, params=config).json()
                if "status" not in results:
                    break
                print("Task status: {}".format(results["status"]))
                if results["status"] == 'failed':
                    print("The task has failed: {}".format(results))
                    break
                if results["status"] == 'finished':
                    break
                time.sleep(1)
            return results

        with open(file_name, mode="rb") as file:
            post_body = file.read()

        config = {
            "key": secret_key,
            "language": "en-US",
            "punctuation": True,
            "format": "m4a"
        }

        r = requests.post("https://api.speechtext.ai/recognize?", headers={'Content-Type': "application/octet-stream"}, params=config, data=post_body).json()

        task = r["id"]

        config = {
            "key": secret_key,
            "task": task,
            "summary": True,
            "summary_size": 15,
            "highlights": True,
            "max_keywords": 10
        }

        config = {
            "key": secret_key,
            "task": task,
            "output": "srt",
            "max_caption_words": 15
        }

        subtitles = get_results(config)
        bot.send_message(message.chat.id, subtitles.split('\n')[2])

    except Exception as e:
        # Логирование ошибки
        logging.error(f"Error processing audio file: {e}")
        # Отправка сообщения об ошибке пользователю
        bot.send_message(message.chat.id, "Something went wrong :(\nTry again.")


# Запуск бота
bot.infinity_polling()
