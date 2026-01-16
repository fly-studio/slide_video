"""
特效基类

定义特效系统的抽象接口
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

import numpy as np

from effects.easing import EasingFunction, get_easing_function


class Effect(ABC):
    """
    特效抽象基类

    所有特效都必须继承此类并实现 apply 方法
    """

    def __init__(self, duration_ms: int, easing: str | EasingFunction = "ease-in-out"):
        """
        初始化特效

        Args:
            duration_ms: 特效持续时长 (毫秒)
            easing: 缓动函数，可以是函数名称字符串或函数对象
        """
        self.duration_ms = duration_ms

        # 处理缓动函数
        if isinstance(easing, str):
            self.easing = get_easing_function(easing)
        else:
            self.easing = easing

    @abstractmethod
    def apply(
        self,
        image: np.ndarray,
        progress: float,
        canvas: np.ndarray | None = None,
        **params: Any,
    ) -> np.ndarray:
        """
        应用特效到图像

        Args:
            image: 输入图像，numpy数组 (H, W, C)，BGR格式
            progress: 原始进度值 [0.0, 1.0]
            canvas: 可选的画布，用于某些特效绘制
            **params: 特效特定的额外参数

        Returns:
            处理后的图像，numpy数组 (H, W, C)
        """
        pass

    def get_eased_progress(self, progress: float) -> float:
        """
        应用缓动函数到进度值

        Args:
            progress: 原始进度 [0.0, 1.0]

        Returns:
            缓动后的进度 [0.0, 1.0]
        """
        # 边界保护
        progress = max(0.0, min(1.0, progress))
        return self.easing(progress)

    @property
    def duration_seconds(self) -> float:
        """特效持续时长 (秒)"""
        return self.duration_ms / 1000.0

    def __repr__(self) -> str:
        """字符串表示"""
        return f"{self.__class__.__name__}(duration={self.duration_ms}ms)"

class TransitionType(Enum):
    """转场枚举"""

    IN = "in"  # 入场
    OUT = "out"  # 出场

class TransitionEffect(Effect):
    """
    转场特效基类

    转场特效通常涉及图像的进入或退出
    """

    def __init__(
        self,
        duration_ms: int,
        transition_type: TransitionType = TransitionType.IN,
        easing: str | EasingFunction = "ease-in-out",
    ):
        """
        初始化转场特效
        Args:
            duration_ms: 特效持续时长 (毫秒)
            transition_type: 转场类型，IN 表示入场，OUT 表示出场
            easing: 缓动函数
        """
        super().__init__(duration_ms, easing)
        self.transition_type = transition_type

        # 根据方向调整默认缓动
        if isinstance(easing, str):
            if transition_type == TransitionType.IN and easing == "ease-in-out":
                self.easing = get_easing_function("ease-out")
            elif transition_type == TransitionType.OUT and easing == "ease-in-out":
                self.easing = get_easing_function("ease-in")


class CompositeEffect(Effect):
    """
    组合特效基类

    允许组合多个特效依次或同时应用
    """

    def __init__(self, effects: list[Effect]):
        """
        初始化组合特效

        Args:
            effects: 特效列表
        """
        # 使用第一个特效的时长和缓动
        if not effects:
            raise ValueError("组合特效至少需要一个子特效")

        total_duration = sum(e.duration_ms for e in effects)
        super().__init__(total_duration, effects[0].easing)
        self.effects = effects

    def apply(
        self,
        image: np.ndarray,
        progress: float,
        canvas: np.ndarray | None = None,
        **params: Any,
    ) -> np.ndarray:
        """
        依次应用所有特效

        Args:
            image: 输入图像
            progress: 总进度 [0.0, 1.0]
            canvas: 画布
            **params: 额外参数

        Returns:
            处理后的图像
        """
        # 计算当前应该应用哪个特效
        total_duration = sum(e.duration_ms for e in self.effects)
        current_time = progress * total_duration

        accumulated_time = 0.0
        result = image

        for effect in self.effects:
            if current_time < accumulated_time:
                break

            if current_time <= accumulated_time + effect.duration_ms:
                # 当前特效正在进行
                local_progress = (current_time - accumulated_time) / effect.duration_ms
                result = effect.apply(result, local_progress, canvas, **params)
                break

            # 当前特效已完成，应用完整效果
            result = effect.apply(result, 1.0, canvas, **params)
            accumulated_time += effect.duration_ms

        return result


def create_canvas(width: int, height: int, color: tuple[int, int, int] = (0, 0, 0)) -> np.ndarray:
    """
    创建空白画布

    Args:
        width: 宽度
        height: 高度
        color: 背景颜色 (B, G, R)

    Returns:
        numpy数组 (H, W, C)
    """

    return np.full((height, width, 3), color, dtype=np.uint8)
    # canvas = np.zeros((height, width, 3), dtype=np.uint8)
    # canvas[:, :] = color
    # return canvas


def blend_images(
    foreground: np.ndarray, background: np.ndarray, alpha: float
) -> np.ndarray:
    """
    混合两个图像

    Args:
        foreground: 前景图像
        background: 背景图像
        alpha: 混合系数 [0.0, 1.0]，0表示完全背景，1表示完全前景

    Returns:
        混合后的图像
    """
    alpha = max(0.0, min(1.0, alpha))
    return (foreground * alpha + background * (1 - alpha)).astype(np.uint8)


def resize_to_fit(
    image: np.ndarray, target_size: tuple[int, int], keep_aspect_ratio: bool = True
) -> np.ndarray:
    """
    调整图像大小以适应目标尺寸

    Args:
        image: 输入图像
        target_size: 目标尺寸 (width, height)
        keep_aspect_ratio: 是否保持宽高比

    Returns:
        调整后的图像
    """
    import cv2

    target_width, target_height = target_size
    h, w = image.shape[:2]

    if not keep_aspect_ratio:
        return cv2.resize(image, (target_width, target_height), interpolation=cv2.INTER_LINEAR)

    # 计算缩放比例
    scale = min(target_width / w, target_height / h)
    new_w = int(w * scale)
    new_h = int(h * scale)

    # 缩放
    resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

    # 居中放置
    canvas = create_canvas(target_width, target_height)
    x_offset = (target_width - new_w) // 2
    y_offset = (target_height - new_h) // 2
    canvas[y_offset : y_offset + new_h, x_offset : x_offset + new_w] = resized

    return canvas


if __name__ == "__main__":
    # 测试基类
    print("=== 特效基类测试 ===\n")

    # 创建一个简单的测试特效
    class TestEffect(Effect):
        def apply(self, image, progress, canvas=None, **params):
            eased = self.get_eased_progress(progress)
            print(f"  progress={progress:.2f}, eased={eased:.4f}")
            return image

    effect = TestEffect(duration_ms=500, easing="ease-in-out")
    print(f"特效: {effect}")
    print(f"持续时长: {effect.duration_seconds}s")

    print("\n应用特效（测试缓动）:")
    dummy_image = np.zeros((100, 100, 3), dtype=np.uint8)
    for p in [0.0, 0.25, 0.5, 0.75, 1.0]:
        effect.apply(dummy_image, p)

    print("\n✓ 特效基类测试完成")
