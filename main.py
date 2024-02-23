from db_connect import DBHelper
import threading
import time
from datetime import datetime, timedelta

import telebot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup

TOKEN = '6982709570:AAEKQIojSf2WSlKdkefJ_geLnkQtBpiUYq0'


bot = telebot.TeleBot(TOKEN)

db = DBHelper()



@bot.message_handler(commands=["start"])
def send_welcome(message):
    bot.send_message(
        message.chat.id,
        """Ну, Привет! Давай кратко объясню что ты можешь делать:
    /add - вносить Фамилию Имя и дату рождения сотрудника в базу данных.
    /upcoming - Дни рождения в течение 2,3,4,5,6,30 дней.
    /remind - эта команда напомнит о днях рождения завтра если такие есть)
    /delete - эта команда позволяет удалить из базы 
    данных информацию о человеке""",
    )


def remind_birthdays(chat_id):
    """
    Функция проверяет есть ли у кого-то день рождения завтра
    относительно текущего дня.
    Принимает chat_id - chat_id пользователя, которому отправится информация.

    Переменная today - текущий день
    tomorrow - следующий день
    birthdays - данные о всех днях рождения из БД

    В качестве ответа отправляет информацию о днях рождения если они есть,
    иначе отправляет сообщение "Завтра дней рождения нет"
    """
    today = datetime.now().date()
    tomorrow = today + timedelta(days=1)
    birthdays = db.load_birthdays()

    for person in birthdays:
        birthday_date = datetime.strptime(person["birthday"],
                                          "%Y-%m-%d").date()
        if (birthday_date.month == tomorrow.month and
                birthday_date.day == tomorrow.day):
            reminder_message = (f"Завтра {tomorrow.strftime('%d.%m.%Y')} день "
                                f"рождения празднует {person['name']}!")
            bot.send_message(chat_id, reminder_message)


def remind_loop():
    """
    Функция отправляет информацию о предстоящих днях рождения каждый
    день с перерывом ровно в 24 часа
    chat_id - содержится id чата, куда необходимо отправлять информацию.
    """
    while True:
        chat_id = (
            6166156542
            # Id чата, куда необходимо каждый день отправлять информацию
        )
        remind_birthdays(chat_id)
        time.sleep(24 * 60 * 60)  # Ожидание 24 часа


@bot.message_handler(commands=["add"])
def add_birthday(message):
    """
    Функция для добавления новой записи в таблицу, запрашивает ввод данных в
    определенном формате Фамилия Имя: ДД.ММ.ГГГГ.
    После переводит на функцию process_birthday_input для дальнейшей проверки.
    """

    msg = bot.reply_to(
        message,
        "Отправь мне имя и дату рождения в формате "
        "Фамилия Имя: ДД.ММ.ГГГГ."
    )
    bot.register_next_step_handler(msg, process_birthday_input)


def process_birthday_input(message):
    """
    Функция для обработки ввода данных в формате Фамилия Имя: ДД.ММ.ГГГГ.
    Принимает message - объект сообщения, содержащий данные ввода.
    Принимает name - имя
    Принимает birthday - дата рождения

    В блоке try проверяется корректность введенных данных и в случае, если все
    корректно - переводит на функцию save_birthday, которая в свою очередь
    сохраняет данные

    Если данные были введены не корректно, то отрабатывает блок except, который
    сообщает пользователю о том, что данные, что он ввел не корректны и
    вызывается функция для ввода данных
    """
    try:
        text = message.text.split(": ")
        if len(text) == 2:
            name = text[0]
            birthday = datetime.strptime(text[1], "%d.%m.%Y").date()
            db.add_birthday(name, birthday.strftime("%Y-%m-%d"))
        bot.reply_to(message,
                     f"Спасибо! {name} добавлен(а) "
                     f"в список дней рождения.")
    except ValueError:
        bot.reply_to(
            message,
            "Некорректный формат ввода. "
            "Пожалуйста, используйте Фамилию Имя: ДД.ММ.ГГГГ.",
        )
        add_birthday(message)


# Функция для отображения встроенной клавиатуры
@bot.message_handler(commands=["upcoming"])
def display_options(message):
    """
    Функция для отображения встроенной клавиатуры
    options - список с цифрами которые будут в цикле добавляться в нужном
    формате в клавиатуру
    markup - в переменной хранится клавиатура наполненная путем наполнения из
    цикла for, также хранит в себе callback-данные days_{opt}
    """
    markup = InlineKeyboardMarkup()
    options = ["30", "6", "5", "4", "3", "2"]
    # Количество дней для выбора
    for opt in options:
        markup.add(
            InlineKeyboardButton(
                f"Дни рождения в течение {opt} дней",
                callback_data=f"days_{opt}"
            )
        )
    bot.send_message(message.chat.id,
                     "Выберите период:", reply_markup=markup)


# Функция для обработки callback-ов от кнопок
@bot.callback_query_handler(func=lambda call: call.data.startswith("days_"))
def handle_query(call):
    """
    Функция для обработки callback-ов от кнопок
    Данная функция вызывается, когда пользователь нажимает на какую-либо из
    представленных ему кнопок.
    Принимает call - данные callback от кнопки (call.data), извлекает
    информацию о количестве дней (days) и вызывает функцию
    find_upcoming_birthdays для поиска информации в БД и передает в нее
    количество дней
    В случае, если дни рождения в заданные период есть, то пользователю
    выдается информация о предстоящих днях рождения.
    Если в указанный срок предстоящих дней рождения не обнаружено, то
    пользователь получает сообщение о том, что в указанное им количество
    дней - дней рождения не обнаружено.
    Также вызывается поток, который удаляет информацию, отправленную ботом
    спустя 10 секунд.
    """
    days = int(call.data.split("_")[1])
    birthdays_list = db.find_upcoming_birthdays(days)
    if birthdays_list:
        reply_message = (
                f"Вот предстоящие дни рождения в течение следующих "
                f"{days} дней:\n" + "\n".join(birthdays_list)
        )
    else:
        reply_message = f"В ближайшие {days} дней, дней рождений нет."
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, reply_message)


@bot.message_handler(commands=['remind'])
def remind_birthdays_command(message):
    remind_birthdays(message.chat.id)


@bot.message_handler(commands=["delete"])
def delete_birthday(message):
    """
    По сути блок функций для удаления записи из БД по полученной Фамилии и
    имени msg - Переменная в которой хранится Фамилия и Имя введенные
    пользователем, эти данные передаются через register_next_step_handler в
    следующую функцию process_delete_input.
    """
    msg = bot.reply_to(
        message,
        "Отправь мне фамилию и имя сотрудника, "
        "которого нужно удалить из базы данных."
    )
    bot.register_next_step_handler(msg, process_delete_input)


def process_delete_input(message):
    """
    Функция для предоставления ответа пользователю о том что запись из БД была
    удалена или же о том, что запись не найдена.
    Функция принимает Фамилию Имя и передает эти данные в функцию
    delete_birthday_by_name, и если она вернула True, то пользователь получает
    положительный ответ, если же она возвращает False, то пользователю
    сообщается, что запись не найдена или произошла ошибка.
    """
    name = message.text  # Получаем имя сотрудника для удаления
    if db.delete_birthday_by_name(name):
        bot.reply_to(message,
                     f"Запись о {name} удалена из списка дней рождения.")
    else:
        bot.reply_to(message,
                     "Запись не найдена или произошла "
                     "ошибка при удалении.")


if __name__ == "__main__":
    threading.Thread(target=remind_loop).start()
    while True:
        bot.polling(none_stop=True)
