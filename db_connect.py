import sqlite3
from datetime import datetime, timedelta


class DBHelper:
    def __init__(self, db_name="birthday.db"):
        """Конструктор класса, инициализирующий подключение к базе данных и
        создающий курсор. Автоматически вызывает метод setup для создания
        таблицы, если она не существует
        db_name: название базы данных
        """
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.setup()

    def setup(self):
        """Создает таблицу birthdays, если она еще не существует.
        Таблица содержит колонки id (уникальный идентификатор),
        name (имя, фамилия) и birthday (дата рождения)"""
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS birthdays (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                birthday DATE NOT NULL
            )
            """
        )
        self.conn.commit()

    def add_birthday(self, name, birthday):
        """Добавляет запись о дне рождения в таблицу.
        :param name: Фамилия Имя
        :param birthday: Дата рождения
        """
        self.cursor.execute(
            "INSERT INTO birthdays (name, birthday) VALUES (?, ?)",
            (name, birthday)
        )
        self.conn.commit()

    def find_upcoming_birthdays(self, days):
        """Ищет предстоящие дни рождения в указанный период
        :param days: Количество дней, в которые необходимо найти дни
        рождения
        :return: Список строк, каждая из которых содержит информацию о
        предстоящем дне рождения в формате "Имя - ДД.ММ.ГГГГ"
        """
        upcoming_birthdays = []
        today = datetime.now().date()
        for day in range(days + 1):
            check_date = today + timedelta(days=day)
            self.cursor.execute(
                "SELECT name, strftime('%d.%m.%Y', birthday) "
                "FROM birthdays "
                "WHERE strftime('%m-%d', birthday) = ?",
                (check_date.strftime("%m-%d"),),
            )
            birthdays_today = self.cursor.fetchall()
            for name, birthday in birthdays_today:
                upcoming_birthdays.append(f"{name} - {birthday}")
        return upcoming_birthdays

    def load_birthdays(self):
        """
        Функция загружает из базы данных информацию о днях рождения
        :return: Список словарей, каждый из которых содержит информацию
        о дне рождения в формате "Фамилия Имя, ДД.ММ.ГГГГ"
        """
        self.cursor.execute("SELECT name, birthday FROM birthdays")
        return [{"name": row[0], "birthday": row[1]} for row in
                self.cursor.fetchall()]

    def delete_birthday_by_name(self, name):
        """Удаляет день рождения по имени.
        :param name: Фамилия Имя
        :return: True - если запись была удалена успешно
        False - если запись не была удалена или произошла ошибка"""
        self.cursor.execute("SELECT * FROM birthdays WHERE name = ?",
                            (name,))
        if self.cursor.fetchone():
            self.cursor.execute("DELETE FROM birthdays WHERE name = ?",
                                (name,))
            self.conn.commit()
            return True
        return False
