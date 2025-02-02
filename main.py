import os
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, CallbackContext

# Состояния разговора
ASK, ANSWER = range(2)

# Команда /start
def start(update: Update, context: CallbackContext) -> int:
    update.message.reply_text(
        "Привет! Задай себе число от 1 до 100, а я попытаюсь его угадать за 7 попыток.\n\n"
        "Думай о числе, а я начну угадывать. Нажми любую клавишу, чтобы продолжить.",
        reply_markup=ReplyKeyboardRemove()
    )
    # Инициализируем границы и число попыток
    context.user_data['low'] = 1
    context.user_data['high'] = 100
    context.user_data['attempts'] = 0
    return ASK

# Обработка продолжения и первого хода
def ask_guess(update: Update, context: CallbackContext) -> int:
    low = context.user_data['low']
    high = context.user_data['high']
    guess = (low + high) // 2
    context.user_data['guess'] = guess
    context.user_data['attempts'] += 1

    update.message.reply_text(
        f"Попытка {context.user_data['attempts']}/7: Твое число равно {guess}?\n"
        "Ответь:\n"
        "`>` если твое число больше,\n"
        "`<` если меньше,\n"
        "`=` если я угадал.",
        parse_mode='Markdown'
    )
    return ANSWER

# Обработка ответа пользователя
def handle_answer(update: Update, context: CallbackContext) -> int:
    user_response = update.message.text.strip()
    low = context.user_data['low']
    high = context.user_data['high']
    guess = context.user_data['guess']
    attempts = context.user_data['attempts']

    if user_response == '=':
        update.message.reply_text(
            f"Ура! Я угадал число {guess} за {attempts} попыток!"
        )
        return ConversationHandler.END

    if user_response == '>':
        # Если ответ "больше", то новое low = guess + 1
        context.user_data['low'] = guess + 1
    elif user_response == '<':
        # Если ответ "меньше", то новое high = guess - 1
        context.user_data['high'] = guess - 1
    else:
        update.message.reply_text(
            "Пожалуйста, ответь одним из символов: `>`, `<` или `=`.",
            parse_mode='Markdown'
        )
        return ANSWER

    # Проверка корректности интервала
    if context.user_data['low'] > context.user_data['high']:
        update.message.reply_text(
            "Что-то пошло не так – возможно, были ошибки в ответах. Попробуем сначала.",
        )
        return ConversationHandler.END

    # Если попыток больше 7, завершаем игру
    if attempts >= 7:
        update.message.reply_text(
            f"Я не смог угадать число за 7 попыток. Ты победил! Загаданное число было где-то между {low} и {high}."
        )
        return ConversationHandler.END

    # Следующий вопрос
    return ask_guess(update, context)

def cancel(update: Update, context: CallbackContext) -> int:
    update.message.reply_text('Игра отменена.', reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

def main():
    # Получаем токен из переменной окружения
    token = os.getenv('TOKEN')
    if not token:
        print("Ошибка: не задан токен бота (TOKEN) в переменных окружения.")
        return

    updater = Updater(token, use_context=True)
    dispatcher = updater.dispatcher

    # Определяем обработчик разговора
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            ASK: [MessageHandler(Filters.text & ~Filters.command, ask_guess)],
            ANSWER: [MessageHandler(Filters.text & ~Filters.command, handle_answer)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    dispatcher.add_handler(conv_handler)

    # Запуск бота
    updater.start_polling()
    print("Бот запущен...")
    updater.idle()

if __name__ == '__main__':
    main()
