"""
Ken Burns 效果

根据extra参数创建效果
"""

from typing import Callable

import numpy as np

from effects.base import Effect
from misc import types
from textures.sprite import Sprite

ken_burns_directions = {
    types.Direction.TOP: (0, -1),
    types.Direction.BOTTOM: (0, 1),
    types.Direction.LEFT: (-1, 0),
    types.Direction.RIGHT: (1, 0),
    types.Direction.TOP_LEFT: (-1, -1),
    types.Direction.TOP_RIGHT: (1, -1),
    types.Direction.BOTTOM_LEFT: (-1, 1),
    types.Direction.BOTTOM_RIGHT: (1, 1),
    types.Direction.CENTER: (0, 0),
}

class KenBurnsEffect(Effect):
    """Ken Burns 效果"""

    def __init__(
        self,
        duration_ms: int,
        direction: types.Direction,
        zoom_range: tuple[float, float],
        pan_intensity: float,
        easing: str = "linear",
    ):
        super().__init__(duration_ms, easing)
        self.direction = direction
        self.zoom_range = zoom_range
        self.pan_intensity = pan_intensity

    def apply(
        self,
        sprite: Sprite,
        progress: float,
        **kwargs
    ):
        """应用 Ken Burns 效果"""
        eased = self.get_eased_progress(progress)
        w, h = sprite.width, sprite.height

        # 计算缩放
        zoom_start, zoom_end = self.zoom_range
        scale = zoom_start + (zoom_end - zoom_start) * eased

        # 计算平移量
        pan_x, pan_y = self._calculate_pan(w, h, eased)

        # 直接修改 sprite 属性
        sprite.scale = scale
        sprite.x = int(pan_x)
        sprite.y = int(pan_y)
        sprite.alpha = 1.0

        return None


    def _calculate_pan(self, width: int, height: int, progress: float) -> tuple[float, float]:
        """根据方向计算平移量"""
        max_pan_x = width * self.pan_intensity
        max_pan_y = height * self.pan_intensity



        dx, dy = ken_burns_directions[self.direction]

        # 归一化对角线方向
        if abs(dx) + abs(dy) > 1:
            factor = 1 / np.sqrt(2)
            dx *= factor
            dy *= factor

        pan_x = dx * max_pan_x * progress
        pan_y = dy * max_pan_y * progress
        return pan_x, pan_y


def pan_effect(transition_type: types.TransitionType, duration_ms: int, extra: dict) -> KenBurnsEffect:
    """
    平移特效工厂函数

    Args:
        transition_type: 转场类型（未使用）
        duration_ms: 持续时间
        extra: 额外参数
            - direction: 方向 ("top", "bottom", "left", "right", "top_left", "top_right", "bottom_left", "bottom_right", "center")
            - zoom_range: 缩放范围，默认 (1.0, 1.2)
            - pan_intensity: 平移强度，默认 0.1
            - easing: 缓动函数，默认 "linear"

    Returns:
        KenBurnsEffect 对象
    """
    # 从 extra 参数读取方向
    direction = types.Direction[extra.get("direction", "center").upper()]

    zoom_range = extra.get("zoom_range", (1.0, 1.2))
    pan_intensity = extra.get("pan_intensity", 0.1)
    easing = extra.get("easing", "linear")

    return KenBurnsEffect(
        duration_ms=duration_ms,
        direction=direction,
        zoom_range=zoom_range,
        pan_intensity=pan_intensity,
        easing=easing
    )


# ============================================================================
# 特效注册表
# ============================================================================

effect_registry = {
    "pan": pan_effect,
}
