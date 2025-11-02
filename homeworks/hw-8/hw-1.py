from __future__ import annotations

import random
import time
from collections import deque, OrderedDict
from dataclasses import dataclass
from typing import Dict, Deque, List, Tuple, Iterable


class LRUCache:
    """
    Проста реалізація LRU на базі OrderedDict.
    - get(key) -> value або -1, якщо немає
    - put(key, value) із витісненням найстарішого елемента при переповненні
    """
    def __init__(self, capacity: int = 1000) -> None:
        self.capacity = capacity
        self._od: OrderedDict = OrderedDict()

    def get(self, key):
        if key not in self._od:
            return -1
        self._od.move_to_end(key)  # mark as recently used
        return self._od[key]

    def put(self, key, value) -> None:
        if key in self._od:
            self._od.move_to_end(key)
        self._od[key] = value
        if len(self._od) > self.capacity:
            self._od.popitem(last=False)  # LRU eviction

    def keys(self) -> Iterable:
        return self._od.keys()

    def delete(self, key) -> None:
        if key in self._od:
            del self._od[key]

    def __len__(self) -> int:
        return len(self._od)


def make_queries(n: int, q: int, hot_pool: int = 30, p_hot: float = 0.95, p_update: float = 0.03):
    hot = [(random.randint(0, n // 2), random.randint(n // 2, n - 1)) for _ in range(hot_pool)]
    queries = []
    for _ in range(q):
        if random.random() < p_update:  # ~3% Update
            idx = random.randint(0, n - 1)
            val = random.randint(1, 100)
            queries.append(("Update", idx, val))
        else:  # ~97% Range
            if random.random() < p_hot:  # 95% гарячі
                left, right = random.choice(hot)
            else:  # 5% випадкові
                left = random.randint(0, n - 1)
                right = random.randint(left, n - 1)
            queries.append(("Range", left, right))
    return queries


# --- Функції без кешу ---

def range_sum_no_cache(array: List[int], left: int, right: int) -> int:
    """Сума на діапазоні без кешу."""
    return sum(array[left:right + 1])

def update_no_cache(array: List[int], index: int, value: int) -> None:
    """Оновлення елемента без кешу."""
    array[index] = value


# --- Функції з LRU-кешем ---

@dataclass(frozen=True)
class RangeKey:
    L: int
    R: int

def range_sum_with_cache(array: List[int], left: int, right: int, cache: LRUCache) -> int:
    """
    Повертає суму на діапазоні з кешем:
      - ключ: (left, right)
      - на cache-miss рахує sum(...) і кладе в кеш
    """
    key = RangeKey(left, right)
    cached = cache.get(key)
    if cached != -1:
        return cached
    s = sum(array[left:right + 1])
    cache.put(key, s)
    return s

def update_with_cache(array: List[int], index: int, value: int, cache: LRUCache) -> None:
    """
    Оновлює масив та інвалідовує ВСІ кєшовані діапазони, що містять index.
    Інвалідація — лінійний прохід по ключах кешу (як вимагалось).
    """
    array[index] = value
    # обхід копії списку ключів, бо під час видалення ітерація по самому od некоректна
    for key in list(cache.keys()):
        if isinstance(key, RangeKey):
            if key.L <= index <= key.R:
                cache.delete(key)


# --- Запуск експерименту ---

def run_experiment(n: int = 100_000, q: int = 50_000, seed: int = 42, k_cache: int = 1000) -> None:
    random.seed(seed)

    # великі дані
    base_array = [random.randint(1, 100) for _ in range(n)]
    queries = make_queries(n, q)

    # --- Прогін без кешу ---
    arr_no = base_array.copy()
    t0 = time.perf_counter()
    total_no = 0  # акумулюємо, щоби Python не викидав роботу
    for op in queries:
        if op[0] == "Range":
            _, L, R = op
            total_no += range_sum_no_cache(arr_no, L, R)
        else:
            _, idx, val = op
            update_no_cache(arr_no, idx, val)
    t1 = time.perf_counter()
    time_no = t1 - t0

    # --- Прогін із кешем ---
    arr_cached = base_array.copy()
    cache = LRUCache(capacity=k_cache)
    t2 = time.perf_counter()
    total_with = 0
    hits = 0
    misses = 0
    for op in queries:
        if op[0] == "Range":
            _, L, R = op
            key = RangeKey(L, R)
            got = cache.get(key)
            if got != -1:
                hits += 1
                total_with += got
            else:
                misses += 1
                s = range_sum_with_cache(arr_cached, L, R, cache)
                total_with += s
        else:
            _, idx, val = op
            update_with_cache(arr_cached, idx, val, cache)
    t3 = time.perf_counter()
    time_with = t3 - t2

    speedup = time_no / time_with if time_with > 0 else float("inf")

    # Вивід результатів
    print("\n=== Завдання 1: LRU-кеш для Range/Update ===")
    print(f"Без кешу : {time_no:8.2f} c")
    print(f"LRU-кеш  : {time_with:8.2f} c  (прискорення ×{speedup:.2f})")
    print(f"Cache size: {len(cache)}, hits: {hits}, misses: {misses}")
    # друк тоталів аби уникнути оптимізації (без змісту, але корисно для “чесного” заміру)
    print(f"Checksum (no cache)   : {total_no}")
    print(f"Checksum (with cache) : {total_with}")

def main():
    run_experiment(n=100_000, q=50_000, seed=42, k_cache=1000)

if __name__ == "__main__":
    main()
