from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes,
    ConversationHandler, MessageHandler, filters
)
from io import BytesIO
import parser
import matplotlib.pyplot as plt
import numpy as np
from scipy.interpolate import interp1d
from config import TELEGRAM_TOKEN

LOGIN, PASSWORD, SEMESTER = range(3)

def log(msg):
    print(f"→ {msg}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    log(f"Пользователь {update.effective_user.username} использовал /start")
    await update.message.reply_text(
        "Привет! Я бот-ассистент Магистрант.\n"
        "Команды:\n"
        "/start — информация о боте\n"
        "/plan — получить учебный план с графиками"
    )

async def plan_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    log(f"Пользователь {update.effective_user.username} начал ввод данных для /plan")
    await update.message.reply_text("Введите ваш логин:")
    return LOGIN

async def get_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['login'] = update.message.text.strip()
    log(f"Логин введён: {context.user_data['login']}")
    await update.message.reply_text("Введите ваш пароль:")
    return PASSWORD

async def get_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['password'] = update.message.text.strip()
    log(f"Пароль введён: {'*'*len(context.user_data['password'])}")
    await update.message.reply_text("Введите номер семестра (1-4):")
    return SEMESTER


async def get_semester(update: Update, context: ContextTypes.DEFAULT_TYPE):
    semester = update.message.text.strip()
    if not semester.isdigit() or int(semester) not in [1, 2, 3, 4]:
        await update.message.reply_text("Неверный номер семестра. Попробуйте ещё раз:")
        return SEMESTER
    context.user_data['semester'] = int(semester)

    await update.message.reply_text("Подождите, формирую учебный план...")
    log("Запуск парсера через parser_pandas.py")

    try:
        data = parser.parse_plan(
            context.user_data['login'],
            context.user_data['password'],
            context.user_data['semester']
        )
    except Exception as e:
        await update.message.reply_text(f"Ошибка при парсинге: {e}")
        log(f"Ошибка парсинга: {e}")
        return ConversationHandler.END

    if not data:
        await update.message.reply_text("Данные отсутствуют.")
        return ConversationHandler.END

    # --- Текстовый отчет ---
    msg = "Ваш учебный план:\n"
    for d in data:
        msg += f"- {d['name']} — {d['type']} ({d['hours']} ч.)\n"
    await update.message.reply_text(msg)

    # --- Графики нагрузки ---
    names = [d['name'] for d in data]
    hours = np.array([d['hours'] for d in data])

    # 1. Гистограмма часов по дисциплинам
    plt.figure(figsize=(10,6))
    plt.barh(names, hours, color='skyblue')
    plt.xlabel('Часы')
    plt.title(f'Учебная нагрузка за {context.user_data["semester"]} семестр')
    plt.tight_layout()

    buf = BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    await update.message.reply_photo(photo=buf)
    buf.close()
    plt.close()

    # 2. Интерполяция нагрузки по номеру дисциплины (SciPy)
    x = np.arange(len(hours))
    if len(hours) > 1:
        f = interp1d(x, hours, kind='cubic')
        x_new = np.linspace(0, len(hours)-1, 500)
        y_new = f(x_new)

        plt.figure(figsize=(10,6))
        plt.plot(x_new, y_new, label='Интерполяция нагрузки')
        plt.scatter(x, hours, color='red', label='Данные')
        plt.xticks(x, names, rotation=45, ha='right')
        plt.ylabel('Часы')
        plt.title('Интерполяция учебной нагрузки')
        plt.legend()
        plt.tight_layout()

        buf = BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        await update.message.reply_photo(photo=buf)
        buf.close()
        plt.close()

    log("Учебный план и графики отправлены пользователю")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Отменено.")
    log(f"Пользователь {update.effective_user.username} отменил ввод")
    return ConversationHandler.END

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('plan', plan_start)],
        states={
            LOGIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_login)],
            PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_password)],
            SEMESTER: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_semester)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)

    log("Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()

