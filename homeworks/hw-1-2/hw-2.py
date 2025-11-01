from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict

@dataclass
class PrintJob:
    id: str
    volume: float
    priority: int  # 1 — найвищий
    print_time: int  # хвилини


@dataclass
class PrinterConstraints:
    max_volume: float
    max_items: int


def optimize_printing(print_jobs: List[Dict], constraints: Dict) -> Dict:
    """
    Оптимізує чергу 3D-друку за пріоритетами та обмеженнями.
    Жадібна стратегія заповнення батчів:
      1) Формуємо батчі послідовно.
      2) На кожному кроці беремо всі доступні задачі найвищого пріоритету (1→2→3),
         намагаючись додати якомога більше в поточний батч без перевищення
         max_volume і max_items (стабільно за початковим порядком усередині пріоритету).
      3) Якщо ще лишається місце у батчі, "дозаповнюємо" задачами нижчих пріоритетів.

    Час друку батча = max(print_time) у батчі.
    Повертає:
        {
            "print_order": [...],  # список ID у порядку пріоритетів (стабільно), не за батчами
            "total_time": int      # сума часів батчів
        }
    """
    # Валідація та перетворення у dataclass
    jobs: List[PrintJob] = []
    for j in print_jobs:
        pj = PrintJob(
            id=str(j["id"]),
            volume=float(j["volume"]),
            priority=int(j["priority"]),
            print_time=int(j["print_time"]),
        )
        if pj.volume <= 0 or pj.print_time <= 0:
            raise ValueError(f"Некоректні параметри задачі: {pj}")
        jobs.append(pj)

    cn = PrinterConstraints(
        max_volume=float(constraints["max_volume"]),
        max_items=int(constraints["max_items"]),
    )
    if cn.max_volume <= 0 or cn.max_items <= 0:
        raise ValueError("Обмеження принтера мають бути > 0")

    # Стабільно впорядковуємо за пріоритетом (1 кращий), зберігаючи вихідний порядок в межах пріоритету
    # (stable sort: спочатку групуємо списки за пріоритетами)
    by_prio: Dict[int, List[PrintJob]] = {1: [], 2: [], 3: []}
    for j in jobs:
        if j.priority not in (1, 2, 3):
            raise ValueError(f"Невідомий пріоритет {j.priority} у задачі {j.id}")
        by_prio[j.priority].append(j)

    # Підготуємо "черги очікування" за пріоритетами (FIFO)
    pending: Dict[int, List[PrintJob]] = {
        1: list(by_prio[1]),
        2: list(by_prio[2]),
        3: list(by_prio[3]),
    }

    total_time = 0
    batches: List[List[PrintJob]] = []

    # Поки є хоч одна задача — формуємо батч
    def any_pending() -> bool:
        return any(pending[p] for p in (1, 2, 3))

    while any_pending():
        batch: List[PrintJob] = []
        vol_used = 0.0
        cnt_used = 0

        # Допоміжна функція "спробувати додати" з конкретного списку
        def try_fill_from(pr: int):
            nonlocal vol_used, cnt_used
            i = 0
            while i < len(pending[pr]):
                if cnt_used >= cn.max_items:
                    break
                cand = pending[pr][i]
                if vol_used + cand.volume <= cn.max_volume:
                    # додаємо у батч
                    batch.append(cand)
                    vol_used += cand.volume
                    cnt_used += 1
                    pending[pr].pop(i)  # видалити доданого
                    # не збільшуємо i, бо елемент видалили
                else:
                    i += 1  # перейти до наступного кандидата

        # 1) спочатку намагаємось максимально додати задач найвищого пріоритету, потім 2, потім 3
        for pr in (1, 2, 3):
            if cnt_used >= cn.max_items:
                break
            try_fill_from(pr)

        # 2) Якщо батч ще не заповнений (є місце), дозаповнюємо "згори донизу" ще раз,
        #    дозволяючи міксувати пріоритети, щоб не втрачати пропускну здатність.
        for pr in (1, 2, 3):
            if cnt_used >= cn.max_items:
                break
            try_fill_from(pr)

        # Якщо з якоїсь причини нічого не додалося (наприклад, надто великий об'єм одиночної моделі),
        # примусово друкуємо найбільш пріоритетну доступну одинично (інакше зациклиться).
        if not batch:
            for pr in (1, 2, 3):
                if pending[pr]:
                    cand = pending[pr].pop(0)
                    batch = [cand]
                    break

        batches.append(batch)
        batch_time = max(job.print_time for job in batch)
        total_time += batch_time

    # Формуємо print_order як плоский список ID у порядку пріоритетів і стабільності
    # (не в порядку батчів), щоб відповідати прикладам очікуваного результату.
    print_order = [j.id for j in by_prio[1]] + [j.id for j in by_prio[2]] + [j.id for j in by_prio[3]]

    return {
        "print_order": print_order,
        "total_time": total_time,
    }

def test_printing_optimization():
    # Тест 1: Моделі однакового пріоритету
    test1_jobs = [
        {"id": "M1", "volume": 100, "priority": 1, "print_time": 120},
        {"id": "M2", "volume": 150, "priority": 1, "print_time": 90},
        {"id": "M3", "volume": 120, "priority": 1, "print_time": 150}
    ]

    # Тест 2: Моделі різних пріоритетів
    test2_jobs = [
        {"id": "M1", "volume": 100, "priority": 2, "print_time": 120},  # лабораторна
        {"id": "M2", "volume": 150, "priority": 1, "print_time": 90},   # дипломна
        {"id": "M3", "volume": 120, "priority": 3, "print_time": 150}   # особистий проєкт
    ]

    # Тест 3: Перевищення обмежень об'єму
    test3_jobs = [
        {"id": "M1", "volume": 250, "priority": 1, "print_time": 180},
        {"id": "M2", "volume": 200, "priority": 1, "print_time": 150},
        {"id": "M3", "volume": 180, "priority": 2, "print_time": 120}
    ]

    constraints = {
        "max_volume": 300,
        "max_items": 2
    }

    print("Тест 1 (однаковий пріоритет):")
    result1 = optimize_printing(test1_jobs, constraints)
    print(f"Порядок друку: {result1['print_order']}")
    print(f"Загальний час: {result1['total_time']} хвилин")
    assert result1["print_order"] == ['M1', 'M2', 'M3']
    assert result1["total_time"] == 270

    print("\nТест 2 (різні пріоритети):")
    result2 = optimize_printing(test2_jobs, constraints)
    print(f"Порядок друку: {result2['print_order']}")
    print(f"Загальний час: {result2['total_time']} хвилин")
    assert result2["print_order"] == ['M2', 'M1', 'M3']
    assert result2["total_time"] == 270

    print("\nТест 3 (перевищення обмежень):")
    result3 = optimize_printing(test3_jobs, constraints)
    print(f"Порядок друку: {result3['print_order']}")
    print(f"Загальний час: {result3['total_time']} хвилин")
    assert result3["print_order"] == ['M1', 'M2', 'M3']
    assert result3["total_time"] == 450


if __name__ == "__main__":
    test_printing_optimization()
