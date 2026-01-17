"""
转场特效

实现各种图像转场效果：淡入淡出、旋转、移动、缩放、百叶窗、推送等
"""

from typing import Any, Callable, Type

import cv2

from effects.base import  TransitionType, TransitionEffect
from effects.mask import *
from effects.math import merge_mask, create_mask_with_center, alpha_blend


class FadeEffect(TransitionEffect):
    """
    淡入淡出特效

    最基础的转场效果，通过改变透明度实现
    """

    def apply(
        self,
        image: np.ndarray,
        progress: float,
        canvas: np.ndarray | None = None,
        **params: Any,
    ) -> np.ndarray:
        """
        应用淡入淡出特效

        Args:
            image: 输入图像
            progress: 进度 [0.0, 1.0]
            canvas: 背景画布（可选）
            **params: 额外参数

        Returns:
            处理后的图像
        """
        eased = self.get_eased_progress(progress)

        # 根据方向决定alpha值
        if self.transition_type == TransitionType.IN:
            alpha = eased  # 从0到1，淡入
        else:  # TransitionType.OUT
            alpha = 1.0 - eased  # 从1到0，淡出

        return alpha_blend(image, canvas, alpha)


class RotateEffect(TransitionEffect):
    """
    旋转特效

    图像旋转进入或退出
    """

    def __init__(
        self,
        duration_ms: int,
        transition_type: TransitionType = TransitionType.IN,
        easing: str = "ease-in-out",
        angle_range: tuple[float, float] = (0, 360),
        scale_range: tuple[float, float] = (0.5, 1.0),
    ):
        """
        初始化旋转特效

        Args:
            duration_ms: 持续时长
            transition_type: 类型 (TransitionType.IN 或 TransitionType.OUT)
            easing: 缓动函数
            angle_range: 旋转角度范围 (起始角度, 结束角度)
            scale_range: 缩放范围 (起始缩放, 结束缩放)
        """
        super().__init__(duration_ms, transition_type, easing)
        self.angle_range = angle_range
        self.scale_range = scale_range

    def apply(
        self,
        image: np.ndarray,
        progress: float,
        canvas: np.ndarray | None = None,
        **params: Any,
    ) -> np.ndarray:
        """应用旋转特效"""
        eased = self.get_eased_progress(progress)

        # 根据方向调整进度
        if self.transition_type == TransitionType.OUT:
            eased = 1.0 - eased

        # 计算旋转角度和缩放
        angle_start, angle_end = self.angle_range
        angle = angle_start + (angle_end - angle_start) * eased

        scale_start, scale_end = self.scale_range
        scale = scale_start + (scale_end - scale_start) * eased

        # 获取图像中心
        h, w = image.shape[:2]
        center = (w // 2, h // 2)

        # 创建旋转矩阵
        rotation_matrix = cv2.getRotationMatrix2D(center, angle, scale)

        # 应用旋转
        rotated = cv2.warpAffine(
            image, rotation_matrix, (w, h), borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0)
        )

        # 如果缩放小于1，需要与背景混合
        if scale < 1.0:
            alpha = scale
            result = alpha_blend(rotated, canvas, alpha)
        else:
            result = rotated

        return result


class SlideEffect(TransitionEffect):
    """
    移动特效

    图像从指定方向移入或移出
    支持4个方向：上、下、左、右
    """

    def __init__(
        self,
        duration_ms: int,
        slide_direction: Direction =  Direction.LEFT,
        transition_type: TransitionType = TransitionType.IN,
        easing: str = "ease-in-out",
    ):
        """
        初始化移动特效

        Args:
            duration_ms: 持续时长
            slide_direction: 移动方向（Direction枚举）
            transition_type: 入场/出场
            easing: 缓动函数
        """
        super().__init__(duration_ms, transition_type, easing)
        self.slide_direction = slide_direction

    def apply(
        self,
        image: np.ndarray,
        progress: float,
        canvas: np.ndarray | None = None,
        **params: Any,
    ) -> np.ndarray:
        """应用移动特效"""
        eased = self.get_eased_progress(progress)

        h, w = image.shape[:2]

        # 根据类型调整进度
        if self.transition_type == TransitionType.OUT:
            eased = 1.0 - eased

        # 计算偏移量
        if self.slide_direction == Direction.TOP:
            # 从上往下
            offset_x = 0
            offset_y = int(-h * (1 - eased))
        elif self.slide_direction == Direction.BOTTOM:
            # 从下往上
            offset_x = 0
            offset_y = int(h * (1 - eased))
        elif self.slide_direction == Direction.LEFT:
            # 从左往右
            offset_x = int(-w * (1 - eased))
            offset_y = 0
        else:  # Direction.RIGHT
            # 从右往左
            offset_x = int(w * (1 - eased))
            offset_y = 0

        # 创建平移矩阵
        translation_matrix = np.float32([[1, 0, offset_x], [0, 1, offset_y]])

        # 应用平移
        result = cv2.warpAffine(
            image,
            translation_matrix,
            (w, h),
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=(0, 0, 0),
        )

        # 与背景混合（填充移出的区域）
        mask = (result == 0).all(axis=2)
        result[mask] = canvas[mask]

        return result


class ZoomEffect(TransitionEffect):
    """
    缩放特效

    图像放大或缩小进入/退出
    """

    def __init__(
        self,
        duration_ms: int,
        transition_type: TransitionType = TransitionType.IN,
        easing: str = "ease-in-out",
        zoom_range: tuple[float, float] = (0.5, 1.0),
    ):
        """
        初始化缩放特效

        Args:
            duration_ms: 持续时长
            transition_type: 方向
            easing: 缓动函数
            zoom_range: 缩放范围 (起始缩放, 结束缩放)
        """
        super().__init__(duration_ms, transition_type, easing)
        self.zoom_range = zoom_range

    def apply(
        self,
        image: np.ndarray,
        progress: float,
        canvas: np.ndarray | None = None,
        **params: Any,
    ) -> np.ndarray:
        """应用缩放特效"""
        eased = self.get_eased_progress(progress)

        # 根据方向调整进度
        if self.transition_type == TransitionType.OUT:
            eased = 1.0 - eased

        # 计算缩放比例
        zoom_start, zoom_end = self.zoom_range
        scale = zoom_start + (zoom_end - zoom_start) * eased

        h, w = image.shape[:2]
        new_w = int(w * scale)
        new_h = int(h * scale)

        # 缩放图像
        if scale > 0:
            scaled = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        else:
            scaled = np.zeros((1, 1, 3), dtype=np.uint8)
            new_w, new_h = 1, 1

        # 计算居中位置
        x_offset = (w - new_w) // 2
        y_offset = (h - new_h) // 2

        # 创建结果图像
        result = canvas.copy()

        # 处理缩放后的图像放置
        if scale >= 1.0:
            # 放大：裁剪中心部分
            crop_x = (new_w - w) // 2
            crop_y = (new_h - h) // 2
            result = scaled[crop_y : crop_y + h, crop_x : crop_x + w]
        else:
            # 缩小：居中放置
            result[y_offset : y_offset + new_h, x_offset : x_offset + new_w] = scaled

        return result


class WipeEffect(TransitionEffect):
    """
    Mask擦除效果

    """

    def __init__(
        self,
        duration_ms: int,
        transition_type: TransitionType = TransitionType.IN,
        easing: str = "ease-in-out",
        shape: ShapeMaskStrategy = CircleMask,
        center: tuple[float, float] = (0.5, 0.5),
        feather: float = 0,
        **kwargs
    ):
        """
        初始化擦除效果

        Args:
            duration_ms: 持续时长
            transition_type: 方向
            easing: 缓动函数
            shape:
            center: 相对于w/h的位置，比如0.5就是图片的中心

        """
        super().__init__(duration_ms, transition_type, easing)
        self.shape = shape
        self.center = center
        self.feather = feather

        self.dx: np.ndarray|None = None
        self.dy: np.ndarray|None = None
        self.kwargs = kwargs



    def apply(
        self,
        image: np.ndarray,
        progress: float,
        canvas: np.ndarray|None = None,
        **params: Any,
    ) -> np.ndarray:
        """应用遮罩擦除特效"""
        # 获取缓动后的进度值 (0-1)
        eased = self.get_eased_progress(progress)
        # 统一语义：t 越大，mask（显示区域）越大
        if self.transition_type == TransitionType.IN:
            t = eased  # 0→1 逐渐显示
        else:
            t = 1.0 - eased  # 1→0 逐渐消

        if self.dx is None or self.dy is None:
            h, w = image.shape[:2]
            self.dy, self.dx = create_mask_with_center(w, h, self.center)

        mask = self.shape.compute(self.dx, self.dy, t, **self.kwargs)

        return merge_mask(image, canvas, mask)


def transition_effect(effect: Type[TransitionEffect], transition_type: TransitionType, **kwargs) -> Callable[[int, dict], TransitionEffect]:
    """转场特效工厂函数"""
    def _fun(duration_ms: int, extra: dict) -> TransitionEffect:
        easing = extra.get("easing", "ease-in-out")
        return effect(duration_ms, transition_type=transition_type, easing=easing, **kwargs)
    return _fun

# ============================================================================
# 特效注册表
# ============================================================================

effect_registry = {
    "fade_in": transition_effect(FadeEffect, TransitionType.IN),
    "fade_out": transition_effect(FadeEffect, TransitionType.OUT),
    "rotate_in": transition_effect(RotateEffect, TransitionType.IN),
    "rotate_out": transition_effect(RotateEffect, TransitionType.OUT),
    "slide_in": transition_effect(SlideEffect, TransitionType.IN),
    "slide_out": transition_effect(SlideEffect, TransitionType.OUT),
    "zoom_in": transition_effect(ZoomEffect, TransitionType.IN),
    "zoom_out": transition_effect(ZoomEffect, TransitionType.OUT),

    "wipe_heart_in": transition_effect(WipeEffect, TransitionType.IN, shape=HeartMask()),
    "wipe_heart_out": transition_effect(WipeEffect, TransitionType.OUT, shape=HeartMask()),
    "wipe_star_in": transition_effect(WipeEffect, TransitionType.IN, shape=Star5Mask()),
    "wipe_star_out": transition_effect(WipeEffect, TransitionType.OUT, shape=Star5Mask()),
    "wipe_circle_in": transition_effect(WipeEffect, TransitionType.IN, shape=CircleMask()),
    "wipe_circle_out": transition_effect(WipeEffect, TransitionType.OUT, shape=CircleMask()),
    "wipe_top_in": transition_effect(WipeEffect, TransitionType.IN, shape=RectMask(), direction=Direction.TOP),
    "wipe_top_out": transition_effect(WipeEffect, TransitionType.OUT, shape=RectMask(), direction=Direction.TOP),
    "wipe_bottom_in": transition_effect(WipeEffect, TransitionType.IN, shape=RectMask(), direction=Direction.BOTTOM),
    "wipe_bottom_out": transition_effect(WipeEffect, TransitionType.OUT, shape=RectMask(), direction=Direction.BOTTOM),
    "wipe_left_in": transition_effect(WipeEffect, TransitionType.IN, shape=RectMask(), direction=Direction.LEFT),
    "wipe_left_out": transition_effect(WipeEffect, TransitionType.OUT, shape=RectMask(), direction=Direction.RIGHT),
    "wipe_right_in": transition_effect(WipeEffect, TransitionType.IN, shape=RectMask(), direction=Direction.RIGHT),
    "wipe_right_out": transition_effect(WipeEffect, TransitionType.OUT, shape=RectMask()),
    "wipe_diamond_in": transition_effect(WipeEffect, TransitionType.IN, shape=DiamondMask()),
    "wipe_diamond_out": transition_effect(WipeEffect, TransitionType.OUT, shape=DiamondMask()),
    "wipe_triangle_in": transition_effect(WipeEffect, TransitionType.IN, shape=TriangleUpMask()),
    "wipe_triangle_out": transition_effect(WipeEffect, TransitionType.OUT, shape=TriangleUpMask()),
    "wipe_cross_in": transition_effect(WipeEffect, TransitionType.IN, shape=CrossMask()),
    "wipe_cross_out": transition_effect(WipeEffect, TransitionType.OUT, shape=CrossMask()),

}
