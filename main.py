import os
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    CallbackContext,
)
from faster_whisper import WhisperModel
import ctranslate2
import sentencepiece as spm

# Пути к моделям
ct_model_path = "models/NLLB/nllb-200-distilled-600M-int8"
sp_model_path = "models/NLLB/flores200_sacrebleu_tokenizer_spm.model"

# Инициализация моделей
model_dir = "models/whisper_medium"
whisper_model = WhisperModel(model_dir)
translator = ctranslate2.Translator(ct_model_path)

# Загрузка переменных окружения из файла .env
load_dotenv()

# Инициализация SentencePiece
sp = spm.SentencePieceProcessor()
sp.load(sp_model_path)

# Клавиатура с вариантами задач
task_keyboard = [["Транскрибация", "Перевод"]]


# Обработчик команды /start
def start(update: Update, context: CallbackContext) -> None:
    """
    Обрабатывает команду /start. Отправляет приветственное сообщение и предлагает выбрать задачу.
    """
    update.message.reply_text(
        "Привет! Отправь мне аудиофайл и выбери, что мне с ним сделать.",
        reply_markup=ReplyKeyboardMarkup(task_keyboard, one_time_keyboard=True),
    )


# Обработчик аудиосообщений
def audio_handler(update: Update, context: CallbackContext) -> None:
    """
    Обрабатывает получение аудиосообщения. Скачивает аудиофайл и предлагает выбрать задачу.
    """
    try:
        if update.message.audio is None:
            update.message.reply_text("Пожалуйста, отправьте аудиофайл.")
            return
        audio_file = update.message.audio.get_file()
        file_path = os.path.join("audio_files", f"{audio_file.file_id}.ogg")
        audio_file.download(file_path)
        update.message.reply_text(
            "Выбери задачу:",
            reply_markup=ReplyKeyboardMarkup(
                task_keyboard, one_time_keyboard=True
            ),
        )
    except Exception as e:
        update.message.reply_text(f"Произошла ошибка: {str(e)}")


# Обработчик выбора задачи
def task_handler(update: Update, context: CallbackContext) -> None:
    """
    Обрабатывает выбор пользователя по выполнению задачи (транскрибация или перевод).
    """
    try:
        task = update.message.text
        if task == "Транскрибация":
            transcribe_audio(update, context)
        elif task == "Перевод":
            update.message.reply_text("Введите целевой язык для перевода:")
    except Exception as e:
        update.message.reply_text(f"Произошла ошибка: {str(e)}")


# Обработчик целевого языка для перевода
def target_language_handler(update: Update, context: CallbackContext) -> None:
    """
    Обрабатывает выбор пользователем целевого языка для перевода.
    """
    try:
        target_language = update.message.text
        translate_audio(update, context, target_language)
    except Exception as e:
        update.message.reply_text(f"Произошла ошибка: {str(e)}")


# Функция транскрибации аудиофайла
def transcribe_audio(update: Update, context: CallbackContext) -> None:
    """
    Выполняет транскрибацию аудиофайла и отправляет результат пользователю.
    """
    try:
        file_id = update.message.audio.file_id
        file_path = os.path.join("audio_files", f"{file_id}.ogg")
        segments, info = whisper_model.transcribe(file_path)

        transcription = "\n".join([segment.text for segment in segments])
        update.message.reply_text(f"Транскрибация аудиофайла:\n{transcription}")
    except Exception as e:
        update.message.reply_text(f"Произошла ошибка: {str(e)}")


# Функция перевода транскрибированного текста
def translate_audio(
    update: Update, context: CallbackContext, target_language: str
) -> None:
    """
    Выполняет перевод транскрибированного текста на указанный язык и отправляет результат пользователю.
    """
    try:
        file_id = update.message.audio.file_id
        file_path = os.path.join("audio_files", f"{file_id}.ogg")
        segments, info = whisper_model.transcribe(file_path)

        translations = []
        for segment in segments:
            translated_text = translate_segment(segment.text, target_language)
            translations.append(translated_text)

        translated_text = "\n".join(translations)
        update.message.reply_text(
            f"Перевод транскрибированного текста на {target_language}:\n{translated_text}"
        )
    except Exception as e:
        update.message.reply_text(f"Произошла ошибка: {str(e)}")


# Функция перевода сегмента текста на указанный язык
def translate_segment(text: str, target_language: str) -> str:
    """
    Выполняет перевод сегмента текста на указанный язык с помощью модели.
    """
    src_lang = "eng_Latn"
    tgt_lang = target_language

    source_sentences = [text.strip()]
    source_sentences_subworded = sp.encode_as_pieces(source_sentences)
    source_sentences_subworded = [
        [src_lang] + sent + ["</s>"] for sent in source_sentences_subworded
    ]

    translations_subworded = translator.translate_batch(
        source_sentences_subworded,
        batch_type="tokens",
        max_batch_size=2024,
        beam_size=5,
        target_prefix=[[tgt_lang]],
    )
    translations_subworded = [
        translation.hypotheses[0] for translation in translations_subworded
    ]

    translations = sp.decode(translations_subworded)
    return translations


# Обработчик неизвестной команды
def unknown(update: Update, context: CallbackContext) -> None:
    """
    Обрабатывает неизвестные команды пользователя и отправляет уведомление о непонимании.
    """
    update.message.reply_text("Извините, я не понял ваш запрос.")


# Функция для отправки помощи
def help_command(update: Update, context: CallbackContext) -> None:
    """
    Отправляет информацию о том, как пользоваться ботом.
    """
    update.message.reply_text(
        "Это бот для обработки аудиофайлов. Отправьте мне аудиосообщение и выберите задачу."
    )


# Функция для отправки информации о боте
def info_command(update: Update, context: CallbackContext) -> None:
    """
    Отправляет информацию о боте.
    """
    update.message.reply_text(
        "Этот бот обрабатывает аудиофайлы. Напишите /help для получения помощи."
    )


def main() -> None:
    """
    Основная функция, запускающая бота и настраивающая обработчики сообщений.
    """
    try:
        updater = Updater(os.getenv("BOT_TOKEN"))
        dispatcher = updater.dispatcher

        dispatcher.add_handler(CommandHandler("start", start))
        dispatcher.add_handler(CommandHandler("help", help_command))
        dispatcher.add_handler(CommandHandler("info", info_command))
        dispatcher.add_handler(
            MessageHandler(Filters.audio & ~Filters.command, audio_handler)
        )
        dispatcher.add_handler(
            MessageHandler(Filters.text & ~Filters.command, task_handler)
        )
        dispatcher.add_handler(
            MessageHandler(
                Filters.text & ~Filters.command & ~Filters.audio, target_language_handler
            )
        )
        dispatcher.add_handler(MessageHandler(Filters.command, unknown))

        updater.start_polling()
        updater.idle()
    except Exception as e:
        print(f"Произошла ошибка: {str(e)}")


if __name__ == "__main__":
    main()
