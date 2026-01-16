"""
Ken Burns 效果

9个工厂函数：根据extra参数创建效果
"""

from enum import Enum
from typing import Any

import cv2
import numpy as np

from effects.base import Effect


class KenBurnsDirection(Enum):
    """Ken Burns 9个方向"""

    TOP = "top"
    BOTTOM = "bottom"
    LEFT = "left"
    RIGHT = "right"
    TOP_LEFT = "top_left"
    TOP_RIGHT = "top_right"
    BOTTOM_LEFT = "bottom_left"
    BOTTOM_RIGHT = "bottom_right"
    CENTER = "center"


class KenBurnsEffect(Effect):
    """Ken Burns 效果"""

    def __init__(
        self,
        duration_ms: int,
        direction: KenBurnsDirection,
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
        image: np.ndarray,
        progress: float,
        canvas: np.ndarray | None = None,
        **params: Any,
    ) -> np.ndarray:
        """应用 Ken Burns 效果"""
        eased = self.get_eased_progress(progress)
        h, w = image.shape[:2]

        # 计算缩放
        zoom_start, zoom_end = self.zoom_range
        scale = zoom_start + (zoom_end - zoom_start) * eased

        # 计算平移量
        pan_x, pan_y = self._calculate_pan(w, h, eased)

        # 创建变换矩阵
        center_x, center_y = w / 2, h / 2
        transform_matrix = np.float32(
            [
                [scale, 0, -center_x * scale + center_x + pan_x],
                [0, scale, -center_y * scale + center_y + pan_y],
            ]
        )

        # 应用变换
        result = cv2.warpAffine(
            image,
            transform_matrix,
            (w, h),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_REPLICATE,
        )
        return result

    def _calculate_pan(self, width: int, height: int, progress: float) -> tuple[float, float]:
        """根据方向计算平移量"""
        max_pan_x = width * self.pan_intensity
        max_pan_y = height * self.pan_intensity

        direction_vectors = {
            KenBurnsDirection.TOP: (0, -1),
            KenBurnsDirection.BOTTOM: (0, 1),
            KenBurnsDirection.LEFT: (-1, 0),
            KenBurnsDirection.RIGHT: (1, 0),
            KenBurnsDirection.TOP_LEFT: (-1, -1),
            KenBurnsDirection.TOP_RIGHT: (1, -1),
            KenBurnsDirection.BOTTOM_LEFT: (-1, 1),
            KenBurnsDirection.BOTTOM_RIGHT: (1, 1),
            KenBurnsDirection.CENTER: (0, 0),
        }

        dx, dy = direction_vectors[self.direction]

        # 归一化对角线方向
        if abs(dx) + abs(dy) > 1:
            factor = 1 / np.sqrt(2)
            dx *= factor
            dy *= factor

        pan_x = dx * max_pan_x * progress
        pan_y = dy * max_pan_y * progress
        return pan_x, pan_y


# ============================================================================
# 9个工厂函数（根据extra创建Effect对象）
# ============================================================================

def pan_top(duration_ms: int, extra: dict) -> KenBurnsEffect:
    """向上平移"""
    zoom_range = extra.get("zoom_range", (1.0, 1.2))
    pan_intensity = extra.get("pan_intensity", 0.1)
    return KenBurnsEffect(duration_ms, KenBurnsDirection.TOP, zoom_range, pan_intensity)


def pan_bottom(duration_ms: int, extra: dict) -> KenBurnsEffect:
    """向下平移"""
    zoom_range = extra.get("zoom_range", (1.0, 1.2))
    pan_intensity = extra.get("pan_intensity", 0.1)
    return KenBurnsEffect(duration_ms, KenBurnsDirection.BOTTOM, zoom_range, pan_intensity)


def pan_left(duration_ms: int, extra: dict) -> KenBurnsEffect:
    """向左平移"""
    zoom_range = extra.get("zoom_range", (1.0, 1.2))
    pan_intensity = extra.get("pan_intensity", 0.1)
    return KenBurnsEffect(duration_ms, KenBurnsDirection.LEFT, zoom_range, pan_intensity)


def pan_right(duration_ms: int, extra: dict) -> KenBurnsEffect:
    """向右平移"""
    zoom_range = extra.get("zoom_range", (1.0, 1.2))
    pan_intensity = extra.get("pan_intensity", 0.1)
    return KenBurnsEffect(duration_ms, KenBurnsDirection.RIGHT, zoom_range, pan_intensity)


def pan_top_left(duration_ms: int, extra: dict) -> KenBurnsEffect:
    """左上平移"""
    zoom_range = extra.get("zoom_range", (1.0, 1.2))
    pan_intensity = extra.get("pan_intensity", 0.1)
    return KenBurnsEffect(duration_ms, KenBurnsDirection.TOP_LEFT, zoom_range, pan_intensity)


def pan_top_right(duration_ms: int, extra: dict) -> KenBurnsEffect:
    """右上平移"""
    zoom_range = extra.get("zoom_range", (1.0, 1.2))
    pan_intensity = extra.get("pan_intensity", 0.1)
    return KenBurnsEffect(duration_ms, KenBurnsDirection.TOP_RIGHT, zoom_range, pan_intensity)


def pan_bottom_left(duration_ms: int, extra: dict) -> KenBurnsEffect:
    """左下平移"""
    zoom_range = extra.get("zoom_range", (1.0, 1.2))
    pan_intensity = extra.get("pan_intensity", 0.1)
    return KenBurnsEffect(duration_ms, KenBurnsDirection.BOTTOM_LEFT, zoom_range, pan_intensity)


def pan_bottom_right(duration_ms: int, extra: dict) -> KenBurnsEffect:
    """右下平移"""
    zoom_range = extra.get("zoom_range", (1.0, 1.2))
    pan_intensity = extra.get("pan_intensity", 0.1)
    return KenBurnsEffect(duration_ms, KenBurnsDirection.BOTTOM_RIGHT, zoom_range, pan_intensity)


def zoom_center(duration_ms: int, extra: dict) -> KenBurnsEffect:
    """中心放大"""
    zoom_range = extra.get("zoom_range", (1.0, 1.2))
    return KenBurnsEffect(duration_ms, KenBurnsDirection.CENTER, zoom_range, 0.0)


# ============================================================================
# 特效注册表
# ============================================================================

effect_registry = {
    "pan_top": pan_top,
    "pan_bottom": pan_bottom,
    "pan_left": pan_left,
    "pan_right": pan_right,
    "pan_top_left": pan_top_left,
    "pan_top_right": pan_top_right,
    "pan_bottom_left": pan_bottom_left,
    "pan_bottom_right": pan_bottom_right,
    "zoom_center": zoom_center,
}
