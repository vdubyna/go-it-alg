from __future__ import annotations

import struct
from hashlib import sha256, blake2b
from typing import Dict, Iterable, Iterator, Optional, List


class BloomFilter:
    """
    Проста реалізація фільтра Блума на базі bytearray.
    - size: розмір бітового масиву (кількість бітів)
    - num_hashes: кількість геш-функцій
    Хеші будуємо з одного криптографічного гешу шляхом "соління" індекса.
    """
    __slots__ = ("size", "num_hashes", "_bits")

    def __init__(self, size: int, num_hashes: int):
        if size <= 0:
            raise ValueError("size має бути > 0")
        if num_hashes <= 0:
            raise ValueError("num_hashes має бути > 0")
        self.size = size
        self.num_hashes = num_hashes
        # зберігаємо як масив байт; кожен біт — позиція в цьому масиві
        self._bits = bytearray((size + 7) // 8)

    def _set_bit(self, idx: int) -> None:
        byte_i = idx // 8
        mask = 1 << (idx % 8)
        self._bits[byte_i] |= mask

    def _get_bit(self, idx: int) -> bool:
        byte_i = idx // 8
        mask = 1 << (idx % 8)
        return (self._bits[byte_i] & mask) != 0

    def _hashes(self, item: str) -> Iterator[int]:
        """
        Виводить k індексів у [0, size), використовуючи sha256 + різні "солоності".
        Для зменшення колізій — комбінуємо два 64-бітні значення (double hashing).
        """
        # нормалізуємо вхід як bytes
        data = item.encode("utf-8", errors="ignore")
        # базовий дайджест
        h0 = sha256(data).digest()  # 32 байти
        # виберемо 16 байт як два 64-бітні значення
        a = struct.unpack_from(">Q", h0, 0)[0]
        b = struct.unpack_from(">Q", h0, 8)[0]
        # якщо хтось хоче більше незалежності, додамо blake2b(seed=i)
        # але для k ітерацій вистачить double hashing: h_i = a + i*b
        for i in range(self.num_hashes):
            # трохи перемішаємо через blake2b соль
            salt = i.to_bytes(2, "big")
            h = blake2b(h0 + salt, digest_size=16).digest()
            c = struct.unpack_from(">Q", h, 0)[0]
            # комбінований індекс
            idx = (a + i * b + c) % self.size
            yield idx

    def add(self, item: str) -> None:
        for idx in self._hashes(item):
            self._set_bit(idx)

    def __contains__(self, item: str) -> bool:
        # "Можливо у множині": усі біти встановлені -> True (можливі false positive)
        for idx in self._hashes(item):
            if not self._get_bit(idx):
                return False
        return True


def check_password_uniqueness(
    bloom: BloomFilter,
    new_passwords: Iterable[object],
    *,
    mark_invalid: bool = True
) -> Dict[str, str]:
    """
    Перевіряє список нових паролів на унікальність, використовуючи BloomFilter.
    - Порожні/некоректні значення можуть повертатись зі статусом "некоректний", якщо mark_invalid=True.
    - Паролі обробляємо як рядки без хешування (за вимогами).

    Повертає: {пароль_як_рядок: "вже використаний"/"унікальний"/"некоректний"}
    """
    results: Dict[str, str] = {}
    for raw in new_passwords:
        s = "" if raw is None else str(raw)
        s_norm = s.strip()
        if mark_invalid and not s_norm:
            results[s] = "некоректний"
            continue

        if s_norm in bloom:
            results[s] = "вже використаний"
        else:
            results[s] = "унікальний"
            # ключовий момент: ми одразу додаємо новий унікальний пароль у фільтр,
            # аби надалі його вважати "вже використаним"
            bloom.add(s_norm)
    return results

def main(argv: Optional[List[str]] = None) -> None:
    """Демо для Завдання 1 згідно з прикладом у ТЗ."""
    print("=== Завдання 1: Перевірка унікальності паролів (Bloom Filter) ===")
    bloom = BloomFilter(size=1000, num_hashes=3)

    # Додаємо існуючі паролі
    existing_passwords = ["password123", "admin123", "qwerty123"]
    for password in existing_passwords:
        bloom.add(password)

    # Перевірка нових
    new_passwords_to_check = ["password123", "newpassword", "admin123", "guest"]
    results = check_password_uniqueness(bloom, new_passwords_to_check)

    # Виведення (точно в стилі з умови)
    for password, status in results.items():
        if status == "некоректний":
            print(f"Пароль '{password}' — некоректний.")
        elif status == "вже використаний":
            print(f"Пароль '{password}' — вже використаний.")
        else:
            print(f"Пароль '{password}' — унікальний.")


if __name__ == "__main__":
    main()