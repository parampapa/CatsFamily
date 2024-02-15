import telebot
import sqlite3
from datetime import datetime, timedelta
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import threading
import time
import os



TOKEN = os.environ['TOKEN']
chat_id = '6166156542'

bot = telebot.TeleBot(TOKEN)




conn = sqlite3.connect('birthday.db', check_same_thread=False)
cursor = conn.cursor()


@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(message.chat.id, '''Ну, Привет! Давай кратко объясню что сейчас может бот:
    /add - по этой команде ты сможешь внести Фамилию, Имя и дату рождения сотрудника в базу данных,
    /upcoming - по этой команде ты можешь запросить у кого будет день рождения от 1 до 7 дней
    /remind - эта команда напомнит о днях рождения завтра если такие есть)''')

# Создаем таблицу для хранения информации о днях рождения, если она не существует
cursor.execute('''
CREATE TABLE IF NOT EXISTS birthdays (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    birthday DATE NOT NULL
)
''')
conn.commit()


def load_birthdays():
    cursor.execute('SELECT name, birthday FROM birthdays')
    return [{"name": row[0], "birthday": row[1]} for row in cursor.fetchall()]


def save_birthday(name, birthday):
    cursor.execute('INSERT INTO birthdays (name, birthday) VALUES (?, ?)', (name, birthday))
    conn.commit()


def remind_birthdays(chat_id: int):
    """
    Функция выполняет проверку в базе данных наличия дней рождения на завтрашний день
    Функция принимает id чата, куда необходимо отправить напоминанием о дне рождения
    today - в переменной хранится дата сегодняшнего  день
    tomorrow - хранится дата завтра путем прибавления дня к today,

    """
    today = datetime.now().date()
    tomorrow = today + timedelta(days=1)
    birthdays = load_birthdays()

    for person in birthdays:
        birthday_date = datetime.strptime(person["birthday"], "%Y-%m-%d").date()
        if birthday_date.month == tomorrow.month and birthday_date.day == tomorrow.day:
            reminder_message = f"Завтра {tomorrow.strftime('%d.%m.%Y')} день рождения празднует {person['name']}!"
            bot.send_message(chat_id, reminder_message)


def remind_loop():
    while True:
        chat_id = '6166156542'  # Id чата, куда необходимо каждый день отправлять информацию
        remind_birthdays(chat_id)
        time.sleep(24 * 60 * 60)  # Ожидание 24 часа


@bot.message_handler(commands=['add'])
def add_birthday(message):
    chat_id = message.chat.id
    bot.reply_to(message, "Отправь мне имя и дату рождения в формате Фамилия Имя: ДД.ММ.ГГГГ.")
    bot.register_next_step_handler(message, process_birthday_input)


def process_birthday_input(message):
    try:
        name, birthday = message.text.split(": ")
        birthday_date = datetime.strptime(birthday, "%d.%m.%Y").date()
        save_birthday(name, birthday_date.strftime("%Y-%m-%d"))
        bot.reply_to(message, f"Спасибо! {name} добавлен(а) в список дней рождения.")
    except ValueError:
        bot.reply_to(message, "Некорректный формат ввода. Пожалуйста, используйте Фамилию Имя: ДД.ММ.ГГГГ.")


# Функция для отображения встроенной клавиатуры с выбором количества дней
@bot.message_handler(commands=['upcoming'])
def display_options(message):
    markup = InlineKeyboardMarkup()
    options = ['7', '6', '5', '4', '3', '2']  # Количество дней для выбора
    for opt in options:
        markup.add(InlineKeyboardButton(f'Дни рождения в течение {opt} дней', callback_data=f'days_{opt}'))
    bot.send_message(message.chat.id, 'Выберите период:', reply_markup=markup)

# Функция для обработки callback-ов от кнопок
@bot.callback_query_handler(func=lambda call: call.data.startswith('days_'))
def handle_query(call):
    days = int(call.data.split('_')[1])
    birthdays_list = find_upcoming_birthdays(days)
    if birthdays_list:
        reply_message = f"Вот предстоящие дни рождения в течение следующих {days} дней:\n" + "\n".join(birthdays_list)
    else:
        reply_message = f"В ближайшие {days} дней дней рождений нет."
    sent = bot.send_message(call.message.chat.id, reply_message)
    threading.Thread(target=delete_message_later, args=(call.message.chat.id, sent.message_id, 10)).start()
    bot.answer_callback_query(call.id)

# Функция для поиска предстоящих дней рождения
def find_upcoming_birthdays(days):
    upcoming_birthdays = []
    today = datetime.now().date()
    for day in range(days + 1):
        check_date = today + timedelta(days=day)
        cursor.execute("SELECT name, strftime('%d.%m.%Y', birthday) FROM birthdays "
                       "WHERE strftime('%m-%d', birthday) = ?", (check_date.strftime('%m-%d'),))
        birthdays_today = cursor.fetchall()
        for name, birthday in birthdays_today:
            upcoming_birthdays.append(f"{name} - {birthday}")
    return upcoming_birthdays

@bot.message_handler(commands=['remind'])
def remind_birthdays_command(message):
    remind_birthdays(message.chat.id)


def delete_message_later(chat_id, message_id, delay):
    time.sleep(delay)
    bot.delete_message(chat_id, message_id)

@bot.message_handler(commands=['delete'])
def delete_birthday(message):
    msg = bot.reply_to(message, "Отправь мне имя сотрудника, которого нужно удалить из базы данных.")
    bot.register_next_step_handler(msg, process_delete_input)

def process_delete_input(message):
    name = message.text  # Получаем имя сотрудника для удаления
    if delete_birthday_by_name(name):
        bot.reply_to(message, f"Запись о {name} удалена из списка дней рождения.")
    else:
        bot.reply_to(message, "Запись не найдена или произошла ошибка при удалении.")

def delete_birthday_by_name(name):
    cursor.execute('SELECT * FROM birthdays WHERE name = ?', (name,))
    if cursor.fetchone():
        cursor.execute('DELETE FROM birthdays WHERE name = ?', (name,))
        conn.commit()
        return True
    return False


if __name__ == "__main__":
    threading.Thread(target=remind_loop).start()
    while True:
        bot.polling(none_stop=True)