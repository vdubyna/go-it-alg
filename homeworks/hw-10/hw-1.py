from __future__ import annotations
from dataclasses import dataclass, field
from typing import Set, List, Optional


# Визначення класу Teacher
@dataclass(order=True)
class Teacher:
    first_name: str
    last_name: str
    age: int
    email: str
    can_teach_subjects: Set[str] = field(default_factory=set)
    assigned_subjects: Set[str] = field(default_factory=set, compare=False)

    def coverage(self, remaining: Set[str]) -> Set[str]:
        """Предмети, які цей викладач може покрити з невкритих."""
        return self.can_teach_subjects & remaining


def create_schedule(subjects: Set[str], teachers: List[Teacher]) -> Optional[List[Teacher]]:
    """
    Жадібно підбирає мінімальний (приблизно) набір викладачів для покриття усіх предметів.
    Критерій вибору на кроці: максимальне додаткове покриття; за рівності — молодший вік.
    Повертає список обраних викладачів з заповненими assigned_subjects, або None якщо покриття неможливе.
    """
    remaining = set(subjects)
    selected: List[Teacher] = []

    # Очистити попередні призначення (на випадок повторних запусків)
    for t in teachers:
        t.assigned_subjects.clear()

    # Поки є непокриті предмети — обираємо найкращого кандидата
    while remaining:
        # Обчислюємо, скільки нових предметів додає кожен викладач
        best_teacher: Optional[Teacher] = None
        best_cover: Set[str] = set()

        for t in teachers:
            add = t.coverage(remaining)
            if not add:
                continue

            if (len(add) > len(best_cover)) or (
                len(add) == len(best_cover) and best_teacher is not None and t.age < best_teacher.age
            ) or (
                len(add) == len(best_cover) and best_teacher is None
            ):
                best_teacher = t
                best_cover = add

        # Якщо ніхто не додає покриття — задача нерозв'язна з наявними викладачами
        if best_teacher is None or not best_cover:
            return None

        # Призначаємо обраного викладача на знайдені предмети
        best_teacher.assigned_subjects |= best_cover
        selected.append(best_teacher)
        # Оновлюємо залишок
        remaining -= best_cover

    # Якщо дійшли сюди — все покрито
    return selected


if __name__ == '__main__':
    # Множина предметів
    subjects = {'Математика', 'Фізика', 'Хімія', 'Інформатика', 'Біологія'}

    # Створення списку викладачів
    teachers = [
        Teacher('Олександр', 'Іваненко', 45, 'o.ivanenko@example.com', {'Математика', 'Фізика'}),
        Teacher('Марія', 'Петренко', 38, 'm.petrenko@example.com', {'Хімія'}),
        Teacher('Сергій', 'Коваленко', 50, 's.kovalenko@example.com', {'Інформатика', 'Математика'}),
        Teacher('Наталія', 'Шевченко', 29, 'n.shevchenko@example.com', {'Біологія', 'Хімія'}),
        Teacher('Дмитро', 'Бондаренко', 35, 'd.bondarenko@example.com', {'Фізика', 'Інформатика'}),
        Teacher('Олена', 'Гриценко', 42, 'o.grytsenko@example.com', {'Біологія'}),
    ]

    # Виклик функції створення розкладу
    schedule = create_schedule(subjects, teachers)

    # Виведення розкладу
    if schedule:
        print("Розклад занять:")
        # Для стабільності виводу можна відсортувати за прізвищем та ім'ям
        for teacher in sorted(schedule, key=lambda t: (t.last_name, t.first_name)):
            print(f"{teacher.first_name} {teacher.last_name}, {teacher.age} років, email: {teacher.email}")
            print(f"   Викладає предмети: {', '.join(sorted(teacher.assigned_subjects))}\n")
    else:
        print("Неможливо покрити всі предмети наявними викладачами.")
