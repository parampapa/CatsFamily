import os
import sqlite3
import threading
import time
from datetime import datetime, timedelta

import telebot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup

TOKEN =
# chat_id = ""

bot = telebot.TeleBot(TOKEN)

conn = sqlite3.connect("birthday.db", check_same_thread=False)
cursor = conn.cursor()


@bot.message_handler(commands=["start"])
def send_welcome(message):
    bot.send_message(
        message.chat.id,
        """Ну, Привет! Давай кратко объясню что ты можешь делать:
    /add - вносить Фамилию Имя и дату рождения сотрудника в базу данных.
    /upcoming - Запросить, у кого будет день рождения от 2 до 7 дней.
    /remind - эта команда напомнит о днях рождения завтра если такие есть)
    /delete - эта команда позволяет удалить из базы 
    данных информацию о человеке""",

    )


# Создаем таблицу для хранения информации о днях рождения,
# если она не существует
cursor.execute(
    """
CREATE TABLE IF NOT EXISTS birthdays (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    birthday DATE NOT NULL
)
"""
)
conn.commit()


def load_birthdays():
    """
    Функция загружает из базы данных информацию о днях рождения
    возвращает список словарей с информацией о днях рождения

    """
    cursor.execute("SELECT name, birthday FROM birthdays")
    return [{"name": row[0], "birthday": row[1]} for row in cursor.fetchall()]


def save_birthday(name, birthday):
    """
    Функция сохраняет информацию о днях рождения в базу данных
    Принимает:
    name - имя
    birthday - дата рождения

    """
    cursor.execute(
        "INSERT INTO birthdays (name, birthday) VALUES (?, ?)",
        (name, birthday)
    )
    conn.commit()


@bot.message_handler(commands=["remind"])
def remind_birthdays(chat_id: int):
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
    birthdays = load_birthdays()

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
    # chat_id = message.chat.id
    bot.reply_to(
        message,
        "Отправь мне имя и дату рождения в формате "
        "Фамилия Имя: ДД.ММ.ГГГГ."
    )
    bot.register_next_step_handler(message, process_birthday_input)


def process_birthday_input(message):
    """
    Функция для обработки ввода данных в формате Фамилия Имя: ДД.ММ.ГГГГ.
    Принимает message - объект сообщения, содержащий данные ввода.
    Принимает name - имя
    Принимает birthday - дата рождения

    В блоке try проверяется корректность введеных данных и в случае, если все
    корректно - переводит на функцию save_birthday, которая в свою очередь
    сохраняет данные

    Если данные были введены не корректно, то отрабатывает блок except, который
    сообщает пользователю о том, что данные, что он ввел не корректны и
    вызывается функция для ввода данных

    """
    try:
        name, birthday = message.text.split(": ")
        birthday_date = datetime.strptime(birthday, "%d.%m.%Y").date()
        save_birthday(name, birthday_date.strftime("%Y-%m-%d"))
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
    информацию о колличестве дней (days) и вызывает функцию
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
    birthdays_list = find_upcoming_birthdays(days)
    if birthdays_list:
        reply_message = (
                f"Вот предстоящие дни рождения в течение следующих "
                f"{days} дней:\n" + "\n".join(birthdays_list)
        )
    else:
        reply_message = f"В ближайшие {days} дней дней рождений нет."
    sent = bot.send_message(call.message.chat.id, reply_message)
    threading.Thread(
        target=delete_message_later,
        args=(call.message.chat.id, sent.message_id, 10)
    ).start()
    bot.answer_callback_query(call.id)


# Функция для поиска предстоящих дней рождения
def find_upcoming_birthdays(days):
    """
    Функция для поиска предстоящих дней рождения
    Принимает days - количество дней для поиска

    Возвращает список предстоящих дней рождения в указанном периоде

    """
    upcoming_birthdays = []
    today = datetime.now().date()
    for day in range(days + 1):
        check_date = today + timedelta(days=day)
        cursor.execute(
            "SELECT name, strftime('%d.%m.%Y', birthday) FROM birthdays "
            "WHERE strftime('%m-%d', birthday) = ?",
            (check_date.strftime("%m-%d"),),
        )
        birthdays_today = cursor.fetchall()
        for name, birthday in birthdays_today:
            upcoming_birthdays.append(f"{name} - {birthday}")
    return upcoming_birthdays


def delete_message_later(chat_id, message_id, delay):
    time.sleep(delay)
    bot.delete_message(chat_id, message_id)


@bot.message_handler(commands=["delete"])
def delete_birthday(message):
    """
    По сути блок функций для удаления записи из БД по полученой Фамилии и имени
    msg - Переменная в которой хранится Фамилия и Имя введеные пользователем,
    эти данные передаются через register_next_step_handler в следующую функцию
    process_delete_input.

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
    if delete_birthday_by_name(name):
        bot.reply_to(message,
                     f"Запись о {name} удалена из списка дней рождения.")
    else:
        bot.reply_to(message,
                     "Запись не найдена или произошла "
                     "ошибка при удалении.")


def delete_birthday_by_name(name):
    """
    Функция для проверки наличия в БД
    Принимает name - Фамилию Имя
    Если в БД обнаруживается запись из name - то функция возвращает True, в
    противном случае False

    """
    cursor.execute("SELECT * FROM birthdays WHERE name = ?",
                   (name,))
    if cursor.fetchone():
        cursor.execute("DELETE FROM birthdays WHERE name = ?",
                       (name,))
        conn.commit()
        return True
    return False


if __name__ == "__main__":
    threading.Thread(target=remind_loop).start()
    while True:
        bot.polling(none_stop=True)
