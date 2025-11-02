from __future__ import annotations

import random
import time
from collections import deque
from typing import Dict, Deque

class SlidingWindowRateLimiter:
    """
    Rate Limiter зі Sliding Window.
    Зберігає часові мітки повідомлень для кожного user_id у deque.
    Параметри:
      - window_size (секунди)
      - max_requests (скільки подій дозволено всередині будь-яких window_size секунд)
    """
    def __init__(self, window_size: int = 10, max_requests: int = 1):
        self.window_size = int(window_size)
        self.max_requests = int(max_requests)
        self._history: Dict[str, Deque[float]] = {}

    def _cleanup_window(self, user_id: str, current_time: float) -> None:
        """
        Видаляє застарілі таймстемпи (старші за current_time - window_size).
        Якщо черга спорожніла — видаляє запис про користувача.
        """
        dq = self._history.get(user_id)
        if dq is None:
            return
        limit = current_time - self.window_size
        while dq and dq[0] <= limit:
            dq.popleft()
        if not dq:
            self._history.pop(user_id, None)

    def can_send_message(self, user_id: str) -> bool:
        """
        Повертає True, якщо користувач може надіслати повідомлення зараз.
        """
        now = time.time()
        self._cleanup_window(user_id, now)
        dq = self._history.get(user_id)
        if dq is None:
            return True
        return len(dq) < self.max_requests

    def record_message(self, user_id: str) -> bool:
        """
        Якщо відправлення дозволено — записує таймстемп і повертає True.
        Якщо ні — повертає False (нічого не записує).
        """
        now = time.time()
        self._cleanup_window(user_id, now)
        dq = self._history.get(user_id)
        if dq is None:
            dq = deque()
            self._history[user_id] = dq
        if len(dq) < self.max_requests:
            dq.append(now)
            return True
        return False

    def time_until_next_allowed(self, user_id: str) -> float:
        """
        Повертає час очікування до наступного дозволу (секунди, >= 0).
        Якщо можна вже зараз — 0.0.
        """
        now = time.time()
        self._cleanup_window(user_id, now)
        dq = self._history.get(user_id)
        if dq is None or len(dq) < self.max_requests:
            return 0.0
        # коли вийде з вікна найстаріший запис
        wait = dq[0] + self.window_size - now
        return max(0.0, wait)


# --- Демонстрація роботи ---

def test_rate_limiter():
    # Створюємо rate limiter: вікно 10 секунд, 1 повідомлення
    limiter = SlidingWindowRateLimiter(window_size=10, max_requests=1)

    # Симулюємо потік повідомлень від користувачів (послідовні ID від 1 до 5)
    print("\n=== Симуляція потоку повідомлень ===")
    for message_id in range(1, 11):
        user_id = message_id % 5 + 1
        uid = str(user_id)
        result = limiter.record_message(uid)
        wait_time = limiter.time_until_next_allowed(uid)
        print(f"Повідомлення {message_id:2d} | Користувач {user_id} | "
              f"{'✓' if result else f'× (очікування {wait_time:.1f}с)'}")
        time.sleep(random.uniform(0.1, 1.0))

    print("\nОчікуємо 4 секунди...")
    time.sleep(4)

    print("\n=== Нова серія повідомлень після очікування ===")
    for message_id in range(11, 21):
        user_id = message_id % 5 + 1
        uid = str(user_id)
        result = limiter.record_message(uid)
        wait_time = limiter.time_until_next_allowed(uid)
        print(f"Повідомлення {message_id:2d} | Користувач {user_id} | "
              f"{'✓' if result else f'× (очікування {wait_time:.1f}с)'}")
        time.sleep(random.uniform(0.1, 1.0))

def main():
    test_rate_limiter()


if __name__ == "__main__":
    main()
