"""
转场特效

实现各种图像转场效果：淡入淡出、旋转、移动、缩放、百叶窗、推送等
"""

from enum import Enum
from typing import Any, Callable, Type

import cv2
import numpy as np

from effects.base import Effect, TransitionType, TransitionEffect, create_canvas, blend_images


class Direction(Enum):
    """移动方向枚举"""

    TOP = "top"  # 从上往下
    BOTTOM = "bottom"  # 从下往上
    LEFT = "left"  # 从左往右
    RIGHT = "right"  # 从右往左



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

        # 创建背景（如果没有提供）
        if canvas is None:
            canvas = create_canvas(image.shape[1], image.shape[0])

        # 根据方向决定alpha值
        if self.transition_type == TransitionType.IN:
            alpha = eased  # 从0到1，淡入
        else:  # TransitionType.OUT
            alpha = 1.0 - eased  # 从1到0，淡出

        return blend_images(image, canvas, alpha)


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

        # 创建背景
        if canvas is None:
            canvas = create_canvas(image.shape[1], image.shape[0])

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
            result = blend_images(rotated, canvas, alpha)
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

        # 创建背景
        if canvas is None:
            canvas = create_canvas(image.shape[1], image.shape[0])

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

        # 创建背景
        if canvas is None:
            canvas = create_canvas(image.shape[1], image.shape[0])

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


class BlindsEffect(TransitionEffect):
    """
    百叶窗特效

    像百叶窗一样的条纹转场
    """

    def __init__(
        self,
        duration_ms: int,
        transition_type: TransitionType = TransitionType.IN,
        easing: str = "ease-in-out",
        num_blinds: int = 10,
        orientation: str = "horizontal",
    ):
        """
        初始化百叶窗特效

        Args:
            duration_ms: 持续时长
            transition_type: 方向
            easing: 缓动函数
            num_blinds: 百叶窗数量
            orientation: 方向，"horizontal" 或 "vertical"
        """
        super().__init__(duration_ms, transition_type, easing)
        self.num_blinds = num_blinds
        self.orientation = orientation

    def apply(
        self,
        image: np.ndarray,
        progress: float,
        canvas: np.ndarray | None = None,
        **params: Any,
    ) -> np.ndarray:
        """应用百叶窗特效"""
        eased = self.get_eased_progress(progress)

        # 创建背景
        if canvas is None:
            canvas = create_canvas(image.shape[1], image.shape[0])

        # 根据类型调整alpha
        if self.transition_type == TransitionType.IN:
            alpha = eased
        else:
            alpha = 1.0 - eased

        h, w = image.shape[:2]

        # 创建遮罩
        mask = np.zeros((h, w), dtype=np.float32)

        if self.orientation == "horizontal":
            # 水平百叶窗
            blind_height = h // self.num_blinds
            for i in range(self.num_blinds):
                y_start = i * blind_height
                y_end = min((i + 1) * blind_height, h)
                # 每个百叶窗有自己的进度偏移
                blind_progress = min(1.0, max(0.0, alpha + (i / self.num_blinds) * 0.2))
                mask[y_start:y_end, :] = blind_progress
        else:
            # 垂直百叶窗
            blind_width = w // self.num_blinds
            for i in range(self.num_blinds):
                x_start = i * blind_width
                x_end = min((i + 1) * blind_width, w)
                blind_progress = min(1.0, max(0.0, alpha + (i / self.num_blinds) * 0.2))
                mask[:, x_start:x_end] = blind_progress

        # 应用遮罩
        mask_3d = np.stack([mask] * 3, axis=2)
        result = (image * mask_3d + canvas * (1 - mask_3d)).astype(np.uint8)

        return result


class PushEffect(TransitionEffect):
    """
    推送特效

    新图像推开旧图像
    """

    def __init__(
        self,
        duration_ms: int,
        push_direction: Direction = Direction.LEFT,
        transition_type: TransitionType = TransitionType.IN,
        easing: str = "ease-in-out",
    ):
        """
        初始化推送特效

        Args:
            duration_ms: 持续时长
            push_direction: 推送方向
            transition_type: 入场/出场
            easing: 缓动函数
        """
        super().__init__(duration_ms, transition_type, easing)
        self.push_direction = push_direction

    def apply(
        self,
        image: np.ndarray,
        progress: float,
        canvas: np.ndarray | None = None,
        **params: Any,
    ) -> np.ndarray:
        """
        应用推送特效

        Note: 此特效需要前一张图像作为 canvas 参数
        """
        eased = self.get_eased_progress(progress)

        # 创建背景
        if canvas is None:
            canvas = create_canvas(image.shape[1], image.shape[0])

        h, w = image.shape[:2]

        # 根据方向调整进度
        if self.transition_type == TransitionType.OUT:
            eased = 1.0 - eased

        # 创建结果画布
        result = np.zeros_like(image)

        # 计算偏移量
        if self.push_direction == Direction.LEFT:
            # 向左推
            offset = int(w * eased)
            # 新图像从右边进入
            if offset < w:
                result[:, : w - offset] = canvas[:, offset:]
                result[:, w - offset :] = image[:, : offset]
        elif self.push_direction == Direction.RIGHT:
            # 向右推
            offset = int(w * eased)
            if offset < w:
                result[:, offset:] = canvas[:, : w - offset]
                result[:, :offset] = image[:, w - offset :]
        elif self.push_direction == Direction.TOP:
            # 向上推
            offset = int(h * eased)
            if offset < h:
                result[: h - offset, :] = canvas[offset:, :]
                result[h - offset :, :] = image[:offset, :]
        else:  # Direction.BOTTOM
            # 向下推
            offset = int(h * eased)
            if offset < h:
                result[offset:, :] = canvas[: h - offset, :]
                result[:offset, :] = image[h - offset :, :]

        return result


def transition_effect(effect: Type[TransitionEffect], transition_type: TransitionType) -> Callable[[int, dict], TransitionEffect]:
    """转场特效工厂函数"""
    def _fun(duration_ms: int, extra: dict) -> TransitionEffect:
        # 当direction为in时，easing默认ease-out，即先快后慢
        # 当direction为out时，easing默认ease-in，即先慢后快
        easing = extra.get("easing", "ease-in-out")
        return effect(duration_ms, transition_type=transition_type, easing=easing)
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
    "blinds_in": transition_effect(BlindsEffect, TransitionType.IN),
    "blinds_out": transition_effect(BlindsEffect, TransitionType.OUT),
    "push_in": transition_effect(PushEffect, TransitionType.IN),
    "push_out": transition_effect(PushEffect, TransitionType.OUT),
}


if __name__ == "__main__":
    # 测试转场特效
    print("=== 转场特效测试 ===\n")

    # 创建测试图像
    test_image = np.ones((480, 640, 3), dtype=np.uint8) * 255  # 白色图像
    canvas = np.zeros((480, 640, 3), dtype=np.uint8)  # 黑色背景

    # 测试淡入淡出
    print("1. 测试淡入淡出特效")
    fade_in = FadeEffect(duration_ms=500, transition_type=TransitionType.IN)
    print(f"   {fade_in}")
    for p in [0.0, 0.5, 1.0]:
        result = fade_in.apply(test_image, p, canvas)
        mean_val = np.mean(result)
        print(f"   progress={p:.1f}, 平均亮度={mean_val:.1f}")

    # 测试旋转
    print("\n2. 测试旋转特效")
    rotate = RotateEffect(duration_ms=500, transition_type=TransitionType.IN)
    print(f"   {rotate}")

    # 测试移动
    print("\n3. 测试移动特效")
    slide = SlideEffect(duration_ms=500, slide_direction=Direction.LEFT, transition_type=TransitionType.IN)
    print(f"   {slide}")

    # 测试缩放
    print("\n4. 测试缩放特效")
    zoom = ZoomEffect(duration_ms=500, transition_type=TransitionType.IN)
    print(f"   {zoom}")

    # 测试百叶窗
    print("\n5. 测试百叶窗特效")
    blinds = BlindsEffect(duration_ms=500, transition_type=TransitionType.IN, num_blinds=10)
    print(f"   {blinds}")

    # 测试推送
    print("\n6. 测试推送特效")
    push = PushEffect(duration_ms=500, push_direction=Direction.LEFT, transition_type=TransitionType.IN)
    print(f"   {push}")

    print("\n✓ 所有转场特效测试完成")
