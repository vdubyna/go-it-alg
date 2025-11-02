from __future__ import annotations

import ipaddress
import math
import os
import re
import time
from dataclasses import dataclass
from hashlib import blake2b
from typing import Iterator, Optional, List

# ------------------------
# Налаштування за умовою
# ------------------------
LOG_PATH = "./data/lms-stage-access.log"
HLL_P = 14  # m = 2**p регістрів, очікувана похибка ≈ 1.04 / sqrt(m)

# ------------------------
# Парсер IP з логу
# ------------------------
_IP_RE = re.compile(r"(?:\d{1,3}\.){3}\d{1,3}")

def iter_ips_from_log(path: str) -> Iterator[str]:
    """Потокове читання IP з лог-файлу, ігноруємо некоректні рядки/IP."""
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            m = _IP_RE.search(line)
            if not m:
                continue
            ip = m.group(0)
            try:
                ipaddress.IPv4Address(ip)  # відсікає 999.999.999.999 тощо
            except Exception:
                continue
            yield ip

# ------------------------
# HyperLogLog (мінімаліст)
# ------------------------
class HyperLogLog:
    """
    Спрощена реалізація HyperLogLog.
    - p у [4..18], m = 2**p регістрів (по 1 байту на регістр).
    - Похибка ~ 1.04 / sqrt(m).
    """
    __slots__ = ("p", "m", "registers", "_alpha_m")

    def __init__(self, p: int = 14):
        if not (4 <= p <= 18):
            raise ValueError("p має бути в межах [4..18]")
        self.p = p
        self.m = 1 << p
        self.registers = bytearray(self.m)
        self._alpha_m = self._alpha(self.m)

    @staticmethod
    def _alpha(m: int) -> float:
        if m == 16:
            return 0.673
        if m == 32:
            return 0.697
        if m == 64:
            return 0.709
        return 0.7213 / (1.0 + 1.079 / m)

    @staticmethod
    def _hash64(x: str) -> int:
        # 64-бітний хеш без зовнішніх бібліотек
        return int.from_bytes(blake2b(x.encode("utf-8", "ignore"), digest_size=8).digest(), "big", signed=False)

    @staticmethod
    def _rho(w: int, max_bits: int) -> int:
        """
        Позиція першого 1-біта зліва (1-indexed) в max_bits-бітному слові.
        Якщо w == 0 => max_bits + 1.
        """
        if w == 0:
            return max_bits + 1
        return (max_bits - w.bit_length()) + 1

    def add(self, x: str) -> None:
        h = self._hash64(x)
        idx = h >> (64 - self.p)                      # верхні p біт для індексу регістра
        w = h & ((1 << (64 - self.p)) - 1)            # нижні 64-p біт
        rank = self._rho(w, 64 - self.p)
        if rank > self.registers[idx]:
            self.registers[idx] = rank

    def count(self) -> float:
        # Сира оцінка
        indicator = 0.0
        zeros = 0
        for v in self.registers:
            indicator += 2.0 ** (-v)
            if v == 0:
                zeros += 1
        E = self._alpha_m * (self.m ** 2) * (1.0 / indicator)

        # Малий діапазон (Linear Counting): E* = m * ln(m / V), якщо V > 0
        if E <= 2.5 * self.m and zeros > 0:
            return self.m * math.log(self.m / float(zeros))

        # Великий діапазон (для 64-бітного хешу): корекція наближенням
        # (на практиці рідко потрібно; залишаємо без корекції)
        return E

# ------------------------
# Точний та наближений підрахунок
# ------------------------
def exact_count_unique_ips(path: str) -> int:
    uniq: set[str] = set()
    for ip in iter_ips_from_log(path):
        uniq.add(ip)
    return len(uniq)

def hll_count_unique_ips(path: str, p: int = HLL_P) -> float:
    hll = HyperLogLog(p=p)
    for ip in iter_ips_from_log(path):
        hll.add(ip)
    return hll.count()

# ------------------------
# Бенчмарк + друк таблиці
# ------------------------
@dataclass
class BenchmarkResult:
    unique_exact: Optional[int]
    unique_hll: Optional[float]
    time_exact_sec: Optional[float]
    time_hll_sec: Optional[float]
    p: int
    m: int

def benchmark_counts(path: str, p: int = HLL_P) -> BenchmarkResult:
    # HLL
    t0 = time.perf_counter()
    hll_val = hll_count_unique_ips(path, p=p)
    t1 = time.perf_counter()

    # Exact
    t2 = time.perf_counter()
    exact_val = exact_count_unique_ips(path)
    t3 = time.perf_counter()

    return BenchmarkResult(
        unique_exact=exact_val,
        unique_hll=hll_val,
        time_exact_sec=(t3 - t2),
        time_hll_sec=(t1 - t0),
        p=p,
        m=(1 << p),
    )

def print_comparison_table(res: BenchmarkResult) -> None:
    print("\nРезультати порівняння:")
    headers = ["", "Точний підрахунок", "HyperLogLog"]
    rows = [
        ["Унікальні елементи",
         f"{res.unique_exact:.1f}",
         f"{res.unique_hll:.1f}"],
        ["Час виконання (сек.)",
         f"{res.time_exact_sec:.6f}",
         f"{res.time_hll_sec:.6f}"],
        ["Параметри HLL",
         "—",
         f"p={res.p}, m={res.m} (похибка ≈ {1.04/(res.m**0.5):.4f})"],
    ]

    col_w = [max(len(str(r[i])) for r in ([headers] + rows)) for i in range(3)]

    def fmt_row(r: List[str]) -> str:
        return "  ".join(str(r[i]).ljust(col_w[i]) for i in range(3))

    print(fmt_row(headers))
    print("-" * (sum(col_w) + 4))
    for r in rows:
        print(fmt_row(r))
    print()

# ------------------------
# main
# ------------------------
def main() -> None:
    if not os.path.exists(LOG_PATH):
        print(f"Лог-файл '{LOG_PATH}' не знайдено. Покладіть файл у цю директорію та запустіть знову.")
        return
    res = benchmark_counts(LOG_PATH, p=HLL_P)
    print_comparison_table(res)

if __name__ == "__main__":
    main()
