"""
特效基类

定义特效系统的抽象接口
"""

from abc import ABC, abstractmethod
from enum import Enum

import numpy as np

from misc import types
from misc.easing import EasingFunction, get_easing_function
from textures.sprite import Sprite


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
        sprite: Sprite,
        progress: float,
        **kwargs
    ) -> np.ndarray:
        """
        应用特效到图像


        :param sprite:
        :param progress: 原始进度值 [0.0, 1.0]
        :param kwargs: 特效特定的额外参数
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


class TransitionEffect(Effect, ABC):
    """
    转场特效基类

    转场特效通常涉及图像的进入或退出
    """

    def __init__(
        self,
        duration_ms: int,
        transition_type: types.TransitionType = types.TransitionType.IN,
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
            if transition_type == types.TransitionType.IN and easing == "ease-in-out":
                self.easing = get_easing_function("ease-out")
            elif transition_type == types.TransitionType.OUT and easing == "ease-in-out":
                self.easing = get_easing_function("ease-in")







