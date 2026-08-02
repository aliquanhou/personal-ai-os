def fibonacci(n):
    """计算斐波那契数列前 n 个数"""
    fib = [0, 1]
    for i in range(2, n):
        fib.append(fib[i - 1] + fib[i - 2])
    return fib[:n]


if __name__ == "__main__":
    nums = fibonacci(20)
    for i, num in enumerate(nums, start=1):
        print(f"F({i}) = {num}")
