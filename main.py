import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, ConversationHandler, CallbackContext

# Определяем состояния разговора
ASK, ANSWER = range(2)

def start(update: Update, context: CallbackContext) -> int:
    update.message.reply_text(
        "Привет! Загадай число от 1 до 100, а я попробую угадать его за 7 попыток.\n"
        "Нажми любую кнопку, чтобы начать.",
        reply_markup=ReplyKeyboardRemove()
    )
    # Инициализация начальных значений
    context.user_data['low'] = 1
    context.user_data['high'] = 100
    context.user_data['attempts'] = 0
    # Переход к состоянию ASK
    return ask_guess(update, context)

def ask_guess(update: Update, context: CallbackContext) -> int:
    low = context.user_data['low']
    high = context.user_data['high']
    guess = (low + high) // 2
    context.user_data['guess'] = guess
    context.user_data['attempts'] += 1

    # Создаем inline-клавиатуру с кнопками
    keyboard = [
        [
            InlineKeyboardButton("Больше", callback_data='>'),
            InlineKeyboardButton("Меньше", callback_data='<'),
            InlineKeyboardButton("Угадал", callback_data='=')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Если update пришел из команды /start (сообщение), то отправляем новое сообщение.
    # Если update является callback (например, при повторном запросе), то редактируем сообщение.
    if update.callback_query:
        update.callback_query.edit_message_text(
            text=f"Попытка {context.user_data['attempts']}/7: Твое число равно {guess}?",
            reply_markup=reply_markup
        )
    else:
        update.message.reply_text(
            text=f"Попытка {context.user_data['attempts']}/7: Твое число равно {guess}?",
            reply_markup=reply_markup
        )
    return ANSWER

def handle_response(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()  # Обязательно отвечаем на callback, чтобы убрать "часики"
    user_response = query.data
    guess = context.user_data['guess']
    attempts = context.user_data['attempts']

    if user_response == '=':
        query.edit_message_text(
            text=f"Ура! Я угадал число {guess} за {attempts} попыток!"
        )
        return ConversationHandler.END

    if user_response == '>':
        context.user_data['low'] = guess + 1
    elif user_response == '<':
        context.user_data['high'] = guess - 1

    # Проверяем, что диапазон корректный
    if context.user_data['low'] > context.user_data['high']:
        query.edit_message_text(
            text="Что-то пошло не так – возможно, были ошибки в ответах. Попробуем сначала."
        )
        return ConversationHandler.END

    if attempts >= 7:
        query.edit_message_text(
            text=f"Я не смог угадать число за 7 попыток. Ты победил! Загаданное число было где-то между {context.user_data['low']} и {context.user_data['high']}."
        )
        return ConversationHandler.END

    # Следующий ход: спрашиваем снова с обновленным диапазоном
    return ask_guess(update, context)

def cancel(update: Update, context: CallbackContext) -> int:
    update.message.reply_text(
        "Игра отменена.", reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

def main():
    # Получаем токен из переменной окружения
    token = os.getenv('TOKEN')
    if not token:
        print("Ошибка: не задан токен бота (TOKEN) в переменных окружения.")
        return

    updater = Updater(token, use_context=True)
    dispatcher = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            # Состояние ASK может обрабатываться как текстовое сообщение, так и callback-запрос
            ASK: [CallbackQueryHandler(ask_guess)],
            ANSWER: [CallbackQueryHandler(handle_response)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    dispatcher.add_handler(conv_handler)

    updater.start_polling()
    print("Бот запущен...")
    updater.idle()

if __name__ == '__main__':
    main()
