"""
缓动函数库 - 完全符合CSS3标准

提供与CSS3完全一致的缓动曲线实现，确保前端可以复现相同的视觉效果。
所有函数接收 t ∈ [0, 1] 并返回缓动后的值 ∈ [0, 1]
"""

from typing import Callable, Protocol


class EasingFunction(Protocol):
    """缓动函数协议"""

    def __call__(self, t: float) -> float:
        """
        应用缓动函数

        Args:
            t: 进度值，范围 [0.0, 1.0]

        Returns:
            缓动后的值，范围 [0.0, 1.0]
        """
        ...


def linear(t: float) -> float:
    """
    线性缓动 - 无缓动效果
    CSS3: cubic-bezier(0, 0, 1, 1)

    Args:
        t: 进度 [0.0, 1.0]

    Returns:
        相同的进度值
    """
    return t


def ease(t: float) -> float:
    """
    标准缓动 - 先加速后减速
    CSS3: cubic-bezier(0.25, 0.1, 0.25, 1.0)

    这是CSS3的默认缓动函数，提供平滑的动画效果
    """
    return _cubic_bezier(0.25, 0.1, 0.25, 1.0)(t)


def ease_in(t: float) -> float:
    """
    缓入 - 慢速开始，加速结束
    CSS3: cubic-bezier(0.42, 0, 1.0, 1.0)

    适合出场动画
    """
    return _cubic_bezier(0.42, 0.0, 1.0, 1.0)(t)


def ease_out(t: float) -> float:
    """
    缓出 - 快速开始，减速结束
    CSS3: cubic-bezier(0, 0, 0.58, 1.0)

    适合入场动画
    """
    return _cubic_bezier(0.0, 0.0, 0.58, 1.0)(t)


def ease_in_out(t: float) -> float:
    """
    缓入缓出 - 慢速开始和结束
    CSS3: cubic-bezier(0.42, 0, 0.58, 1.0)

    适合完整的动画循环，最常用的缓动函数
    """
    return _cubic_bezier(0.42, 0.0, 0.58, 1.0)(t)


def cubic_bezier(p1x: float, p1y: float, p2x: float, p2y: float) -> EasingFunction:
    """
    创建自定义三次贝塞尔曲线缓动函数

    Args:
        p1x: 第一个控制点的x坐标 [0, 1]
        p1y: 第一个控制点的y坐标 (可以超出[0,1]范围产生弹性效果)
        p2x: 第二个控制点的x坐标 [0, 1]
        p2y: 第二个控制点的y坐标 (可以超出[0,1]范围产生弹性效果)

    Returns:
        缓动函数

    Example:
        >>> bounce = cubic_bezier(0.68, -0.55, 0.265, 1.55)
        >>> value = bounce(0.5)
    """
    return _cubic_bezier(p1x, p1y, p2x, p2y)


def _cubic_bezier(p1x: float, p1y: float, p2x: float, p2y: float) -> Callable[[float], float]:
    """
    内部实现：三次贝塞尔曲线

    使用二分法求解贝塞尔曲线，与浏览器实现保持一致
    贝塞尔曲线公式: B(t) = (1-t)³P₀ + 3(1-t)²tP₁ + 3(1-t)t²P₂ + t³P₃
    其中 P₀ = (0,0), P₃ = (1,1) 为固定端点
    """

    def bezier_x(t: float) -> float:
        """计算贝塞尔曲线的x坐标"""
        # B(t) = 3(1-t)²t*p1x + 3(1-t)t²*p2x + t³
        t2 = t * t
        t3 = t2 * t
        mt = 1 - t
        mt2 = mt * mt
        return 3 * mt2 * t * p1x + 3 * mt * t2 * p2x + t3

    def bezier_y(t: float) -> float:
        """计算贝塞尔曲线的y坐标"""
        t2 = t * t
        t3 = t2 * t
        mt = 1 - t
        mt2 = mt * mt
        return 3 * mt2 * t * p1y + 3 * mt * t2 * p2y + t3

    def solve_t_for_x(x: float) -> float:
        """
        使用二分法求解 bezier_x(t) = x 时的 t 值

        Args:
            x: 目标x坐标 [0, 1]

        Returns:
            对应的参数t [0, 1]
        """
        # 边界情况
        if x <= 0:
            return 0.0
        if x >= 1:
            return 1.0

        # 二分法求解
        t0 = 0.0
        t1 = 1.0
        epsilon = 1e-6  # 精度
        max_iterations = 20

        for _ in range(max_iterations):
            t_mid = (t0 + t1) / 2
            x_mid = bezier_x(t_mid)

            if abs(x_mid - x) < epsilon:
                return t_mid

            if x_mid < x:
                t0 = t_mid
            else:
                t1 = t_mid

        return (t0 + t1) / 2

    def easing_function(x: float) -> float:
        """
        缓动函数主体

        Args:
            x: 输入进度 [0, 1]

        Returns:
            缓动后的值 [0, 1] (可能超出范围如果控制点y超出[0,1])
        """
        # 边界情况优化
        if x <= 0:
            return 0.0
        if x >= 1:
            return 1.0

        # 求解对应的t值，然后计算y坐标
        t = solve_t_for_x(x)
        return bezier_y(t)

    return easing_function


# 预定义常用缓动函数名称映射
EASING_FUNCTIONS: dict[str, EasingFunction] = {
    "linear": linear,
    "ease": ease,
    "ease-in": ease_in,
    "ease-out": ease_out,
    "ease-in-out": ease_in_out,
}


def get_easing_function(name: str) -> EasingFunction:
    """
    根据名称获取缓动函数

    Args:
        name: 缓动函数名称，支持:
              - "linear", "ease", "ease-in", "ease-out", "ease-in-out"
              - "cubic-bezier(x1,y1,x2,y2)" 格式

    Returns:
        对应的缓动函数

    Raises:
        ValueError: 如果名称不支持

    Example:
        >>> easing = get_easing_function("ease-in-out")
        >>> easing = get_easing_function("cubic-bezier(0.42, 0, 0.58, 1)")
    """
    name = name.strip().lower()

    # 预定义函数
    if name in EASING_FUNCTIONS:
        return EASING_FUNCTIONS[name]

    # 解析 cubic-bezier 格式
    if name.startswith("cubic-bezier(") and name.endswith(")"):
        params_str = name[13:-1]  # 提取括号内的参数
        try:
            params = [float(p.strip()) for p in params_str.split(",")]
            if len(params) != 4:
                raise ValueError(f"cubic-bezier需要4个参数，得到{len(params)}个")
            return cubic_bezier(*params)
        except (ValueError, TypeError) as e:
            raise ValueError(f"无效的cubic-bezier参数: {params_str}") from e

    raise ValueError(
        f"不支持的缓动函数: {name}. "
        f"支持: {', '.join(EASING_FUNCTIONS.keys())}, 或 cubic-bezier(x1,y1,x2,y2)"
    )


if __name__ == "__main__":
    # 测试代码
    import numpy as np

    print("=== 缓动函数测试 ===\n")

    test_values = [0.0, 0.25, 0.5, 0.75, 1.0]

    for name, func in EASING_FUNCTIONS.items():
        print(f"{name}:")
        for t in test_values:
            result = func(t)
            print(f"  t={t:.2f} -> {result:.4f}")
        print()

    # 测试自定义cubic-bezier
    print("自定义 cubic-bezier(0.68, -0.55, 0.265, 1.55):")
    bounce = cubic_bezier(0.68, -0.55, 0.265, 1.55)
    for t in test_values:
        result = bounce(t)
        print(f"  t={t:.2f} -> {result:.4f}")
