from __future__ import annotations
from typing import List, Tuple

def find_min_max_divide_and_conquer(arr: List[float], *, verbose: bool = False) -> Tuple[float, float]:
    """
    Знаходить (мінімум, максимум) масиву методом 'розділяй і володарюй'.
    Часова складність: O(n), допоміжна пам'ять: O(log n) через стек рекурсії.

    Args:
        arr: список чисел
        verbose: якщо True — детальний трейс у консоль

    Returns:
        (min_value, max_value)
    """
    if not arr:
        raise ValueError("Масив порожній")

    comparisons = 0  # підрахунок порівнянь мін/макс для наочності

    def rec(lo: int, hi: int, depth: int = 0) -> Tuple[float, float]:
        nonlocal comparisons
        pad = "  " * depth
        if verbose:
            print(f"{pad}▶️ Рекурсія у підмасив [{lo}:{hi}] → {arr[lo:hi+1]}")

        # База: один елемент
        if lo == hi:
            x = arr[lo]
            if verbose:
                print(f"{pad}  • База (1 ел.): min=max={x}")
            return x, x

        # База: два елементи
        if hi - lo == 1:
            a, b = arr[lo], arr[hi]
            comparisons += 1
            if a <= b:
                if verbose:
                    print(f"{pad}  • База (2 ел.): порівняння {a} ≤ {b} ✅ → min={a}, max={b}")
                return a, b
            else:
                if verbose:
                    print(f"{pad}  • База (2 ел.): порівняння {a} ≤ {b} ❌ → min={b}, max={a}")
                return b, a

        # Рекурсивний поділ
        mid = (lo + hi) // 2
        if verbose:
            print(f"{pad}  ⛏️ Ділю на [{lo}:{mid}] і [{mid+1}:{hi}]")

        mn1, mx1 = rec(lo, mid, depth + 1)
        mn2, mx2 = rec(mid + 1, hi, depth + 1)

        # Злиття результатів: глобальний мінімум і максимум
        comparisons += 2  # одне порівняння мінімумів і одне максимумів
        gmin = mn1 if mn1 <= mn2 else mn2
        gmax = mx1 if mx1 >= mx2 else mx2

        if verbose:
            print(f"{pad}  -> Злиття результатів:")
            print(f"{pad}     – лівий (min={mn1}, max={mx1}), правий (min={mn2}, max={mx2})")
            print(f"{pad}     – глобальний min = min({mn1}, {mn2}) = {gmin}")
            print(f"{pad}     – глобальний max = max({mx1}, {mx2}) = {gmax}")

        return gmin, gmax

    mn, mx = rec(0, len(arr) - 1, 0)
    if verbose:
        print(f"✅ Підсумок: min={mn}, max={mx}, порівнянь={comparisons}")
    return mn, mx


def _self_test_task1():
    # Базові перевірки для find_min_max_divide_and_conquer (без трейсингу)
    arr = [3, -5, 10, 0, 2, 9, -1, 7]
    mn, mx = find_min_max_divide_and_conquer(arr)
    assert (mn, mx) == (-5, 10)

    single = [42]
    assert find_min_max_divide_and_conquer(single) == (42, 42)

    pair = [5, 2]
    assert find_min_max_divide_and_conquer(pair) == (2, 5)

    # Демонстраційний прогін з трейсингом (видно основні операції)
    print("\n=== Демонстрація з verbose=True ===")
    demo = [3, -5, 10, 0, 2, 9, -1, 7]
    find_min_max_divide_and_conquer(demo, verbose=True)


if __name__ == "__main__":
    _self_test_task1()
