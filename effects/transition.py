"""
转场特效

实现各种图像转场效果：淡入淡出、旋转、移动、缩放、百叶窗、推送等
"""

from typing import Any, Callable, Type

import numpy as np

from effects.base import TransitionEffect
from misc import types
from textures import mask



class FadeEffect(TransitionEffect):
    """
    淡入淡出特效

    最基础的转场效果，通过改变透明度实现
    """

    def apply(self, sprite, progress: float, **kwargs: Any):
        """修改 Sprite 的 alpha 属性"""
        eased = self.get_eased_progress(progress)

        # 根据方向决定alpha值
        if self.transition_type == types.TransitionType.IN:
            alpha = eased  # 从0到1，淡入
        else:  # types.TransitionType.OUT
            alpha = 1.0 - eased  # 从1到0，淡出

        sprite.alpha = alpha
        return None  # 不需要 mask



class RotateEffect(TransitionEffect):
    """
    旋转特效

    图像旋转进入或退出
    """

    def __init__(
        self,
        duration_ms: int,
        transition_type: types.TransitionType = types.TransitionType.IN,
        easing: str = "ease-in-out",
        angle_range: tuple[float, float] = (0, 360),
        scale_range: tuple[float, float] = (0.5, 1.0),
    ):
        """
        初始化旋转特效

        Args:
            duration_ms: 持续时长
            transition_type: 类型 (types.TransitionType.IN 或 types.TransitionType.OUT)
            easing: 缓动函数
            angle_range: 旋转角度范围 (起始角度, 结束角度)，单位：度
            scale_range: 缩放范围 (起始缩放, 结束缩放)
        """
        super().__init__(duration_ms, transition_type, easing)
        self.angle_range = angle_range
        self.scale_range = scale_range

    def apply(self, sprite, progress: float, **kwargs: Any):
        """修改 Sprite 的 rotation 和 scale 属性"""
        eased = self.get_eased_progress(progress)

        # 根据方向调整进度
        if self.transition_type == types.TransitionType.OUT:
            eased = 1.0 - eased

        # 计算旋转角度和缩放
        angle_start, angle_end = self.angle_range
        angle_deg = angle_start + (angle_end - angle_start) * eased
        angle_rad = np.deg2rad(angle_deg)  # 转换为弧度

        scale_start, scale_end = self.scale_range
        scale = scale_start + (scale_end - scale_start) * eased

        # 设置变换属性
        sprite.rotation = angle_rad
        sprite.scale = scale
        sprite.alpha = 1.0 if scale >= 0.01 else 0.0
        return None



class SlideEffect(TransitionEffect):
    """
    移动特效

    图像从指定方向移入或移出
    支持4个方向：上、下、左、右
    """

    def __init__(
        self,
        duration_ms: int,
        slide_direction: types.Direction = types.Direction.LEFT,
        transition_type: types.TransitionType = types.TransitionType.IN,
        easing: str = "ease-in-out",
    ):
        """
        初始化移动特效

        Args:
            duration_ms: 持续时长
            slide_direction: 移动方向（types.Direction枚举）
            transition_type: 入场/出场
            easing: 缓动函数
        """
        super().__init__(duration_ms, transition_type, easing)
        self.slide_direction = slide_direction

    def apply(self, sprite, progress: float, **kwargs: Any):
        """修改 Sprite 的 x 和 y 属性"""
        eased = self.get_eased_progress(progress)

        h, w = sprite.height, sprite.width

        # 根据类型调整进度
        if self.transition_type == types.TransitionType.OUT:
            eased = 1.0 - eased

        # 计算偏移量
        if self.slide_direction == types.Direction.TOP:
            # 从上往下
            offset_x = 0
            offset_y = int(-h * (1 - eased))
        elif self.slide_direction == types.Direction.BOTTOM:
            # 从下往上
            offset_x = 0
            offset_y = int(h * (1 - eased))
        elif self.slide_direction == types.Direction.LEFT:
            # 从左往右
            offset_x = int(-w * (1 - eased))
            offset_y = 0
        else:  # types.Direction.RIGHT
            # 从右往左
            offset_x = int(w * (1 - eased))
            offset_y = 0

        # 设置位置
        sprite.x = offset_x
        sprite.y = offset_y
        sprite.alpha = 1.0
        return None


class ZoomEffect(TransitionEffect):
    """
    缩放特效

    图像放大或缩小进入/退出
    """

    def __init__(
        self,
        duration_ms: int,
        transition_type: types.TransitionType = types.TransitionType.IN,
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

    def apply(self, sprite, progress: float, **kwargs: Any):
        """修改 Sprite 的 scale 属性"""
        eased = self.get_eased_progress(progress)

        # 根据方向调整进度
        if self.transition_type == types.TransitionType.OUT:
            eased = 1.0 - eased

        # 计算缩放比例
        zoom_start, zoom_end = self.zoom_range
        scale = zoom_start + (zoom_end - zoom_start) * eased

        # 设置缩放
        sprite.scale = scale
        sprite.alpha = 1.0 if scale >= 0.01 else 0.0
        return None


class WipeEffect(TransitionEffect):
    """
    Mask擦除效果
    """

    def __init__(
        self,
        duration_ms: int,
        transition_type: types.TransitionType = types.TransitionType.IN,
        easing: str = "ease-in-out",
        center: tuple[float, float] = (0.5, 0.5),
        feather_radius: int = None,
        feather_mode: types.FeatherCurve = types.FeatherCurve.LINEAR,
        mask_class: Type[mask.ShapeMask] = None,
        **kwargs
    ):
        """
        初始化擦除效果

        Args:
            duration_ms: 持续时长
            transition_type: 方向
            easing: 缓动函数
            mask_class: Mask 实例
            center: 相对于w/h的位置，比如0.5就是图片的中心
            feather: 羽化半径
        """
        super().__init__(duration_ms, transition_type, easing)
        self.feather_radius = feather_radius
        self.feather_mode = feather_mode
        self.mask_class = mask_class
        self.mask : mask.ShapeMask|None = None
        self.center = center
        self.mask_kwargs = kwargs

    def apply(self, sprite, progress: float, **kwargs):
        """修改 Sprite 属性并返回 Mask"""

        if self.mask is None:
            self.mask: mask.ShapeMask = self.mask_class(
                width=sprite.width,
                height=sprite.height,
                cx=self.center[0],
                cy=self.center[1],
                feather_radius=self.feather_radius,
                feather_mode=self.feather_mode,
                **self.mask_kwargs
            )
            sprite.mask = self.mask


        # 获取缓动后的进度值 (0-1)
        eased = self.get_eased_progress(progress)

        # 统一语义：t 越大，mask（显示区域）越大
        if self.transition_type == types.TransitionType.IN:
            t = eased  # 0→1 逐渐显示
        else:
            t = 1.0 - eased  # 1→0 逐渐消失

        self.mask.t = t
        self.mask.render()




def transition_effect(effect: Type[TransitionEffect], transition_type: types.TransitionType, **kwargs) -> Callable[[int, dict], TransitionEffect]:
    """转场特效工厂函数"""
    def _fun(duration_ms: int, extra: dict) -> TransitionEffect:
        easing = extra.get("easing", "ease-in-out")
        return effect(duration_ms, transition_type=transition_type, easing=easing, **kwargs)
    return _fun


def wipe_effect(mask_class: Type[mask.ShapeMask], transition_type: types.TransitionType, **mask_kwargs) -> Callable[[int, dict], WipeEffect]:
    """Wipe 特效工厂函数"""
    def _fun(duration_ms: int, extra: dict) -> WipeEffect:
        easing = extra.get("easing", "ease-in-out")
        center = extra.get("center", (0.5, 0.5))
        feather = extra.get("feather", 0)
        feather_mode = extra.get("feather_mode", types.FeatherCurve.LINEAR)


        return WipeEffect(
            duration_ms=duration_ms,
            transition_type=transition_type,
            easing=easing,
            mask_class=mask_class,
            center=center,
            feather_radius=feather,
            feather_mode=feather_mode,
            **mask_kwargs
        )
    return _fun

# ============================================================================
# 特效注册表
# ============================================================================

effect_registry = {
    "fade_in": transition_effect(FadeEffect, types.TransitionType.IN),
    "fade_out": transition_effect(FadeEffect, types.TransitionType.OUT),
    "rotate_in": transition_effect(RotateEffect, types.TransitionType.IN),
    "rotate_out": transition_effect(RotateEffect, types.TransitionType.OUT),
    "slide_in": transition_effect(SlideEffect, types.TransitionType.IN),
    "slide_out": transition_effect(SlideEffect, types.TransitionType.OUT),
    "zoom_in": transition_effect(ZoomEffect, types.TransitionType.IN),
    "zoom_out": transition_effect(ZoomEffect, types.TransitionType.OUT),

    # Wipe 效果 - 使用新的 Mask 系统
    "wipe_heart_in": wipe_effect(mask.HeartMask, types.TransitionType.IN),
    "wipe_heart_out": wipe_effect(mask.HeartMask, types.TransitionType.OUT),
    "wipe_star_in": wipe_effect(mask.Star5Mask, types.TransitionType.IN),
    "wipe_star_out": wipe_effect(mask.Star5Mask, types.TransitionType.OUT),
    "wipe_circle_in": wipe_effect(mask.CircleMask, types.TransitionType.IN),
    "wipe_circle_out": wipe_effect(mask.CircleMask, types.TransitionType.OUT),
    "wipe_center_in": wipe_effect(mask.RectExpandMask, types.TransitionType.IN),
    "wipe_center_out": wipe_effect(mask.RectExpandMask, types.TransitionType.OUT),
    "wipe_top_in": wipe_effect(mask.RectMask, types.TransitionType.IN, direction=types.Direction.TOP),
    "wipe_top_out": wipe_effect(mask.RectMask, types.TransitionType.OUT, direction=types.Direction.TOP),
    "wipe_bottom_in": wipe_effect(mask.RectMask, types.TransitionType.IN, direction=types.Direction.BOTTOM),
    "wipe_bottom_out": wipe_effect(mask.RectMask, types.TransitionType.OUT, direction=types.Direction.BOTTOM),
    "wipe_left_in": wipe_effect(mask.RectMask, types.TransitionType.IN, direction=types.Direction.LEFT),
    "wipe_left_out": wipe_effect(mask.RectMask, types.TransitionType.OUT, direction=types.Direction.LEFT),
    "wipe_right_in": wipe_effect(mask.RectMask, types.TransitionType.IN, direction=types.Direction.RIGHT),
    "wipe_right_out": wipe_effect(mask.RectMask, types.TransitionType.OUT, direction=types.Direction.RIGHT),
    "wipe_top_left_in": wipe_effect(mask.RectMask, types.TransitionType.IN, direction=types.Direction.TOP_LEFT),
    "wipe_top_left_out": wipe_effect(mask.RectMask, types.TransitionType.OUT, direction=types.Direction.TOP_LEFT),
    "wipe_bottom_left_in": wipe_effect(mask.RectMask, types.TransitionType.IN, direction=types.Direction.BOTTOM_LEFT),
    "wipe_bottom_left_out": wipe_effect(mask.RectMask, types.TransitionType.OUT, direction=types.Direction.BOTTOM_LEFT),
    "wipe_top_right_in": wipe_effect(mask.RectMask, types.TransitionType.IN, direction=types.Direction.TOP_RIGHT),
    "wipe_top_right_out": wipe_effect(mask.RectMask, types.TransitionType.OUT, direction=types.Direction.TOP_RIGHT),
    "wipe_bottom_right_in": wipe_effect(mask.RectMask, types.TransitionType.IN, direction=types.Direction.BOTTOM_RIGHT),
    "wipe_bottom_right_out": wipe_effect(mask.RectMask, types.TransitionType.OUT, direction=types.Direction.BOTTOM_RIGHT),
    "wipe_diamond_in": wipe_effect(mask.DiamondMask, types.TransitionType.IN),
    "wipe_diamond_out": wipe_effect(mask.DiamondMask, types.TransitionType.OUT),
    "wipe_triangle_in": wipe_effect(mask.TriangleUpMask, types.TransitionType.IN),
    "wipe_triangle_out": wipe_effect(mask.TriangleUpMask, types.TransitionType.OUT),
    "wipe_cross_in": wipe_effect(mask.CrossMask, types.TransitionType.IN),
    "wipe_cross_out": wipe_effect(mask.CrossMask, types.TransitionType.OUT),
}
