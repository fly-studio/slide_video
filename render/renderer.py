"""
渲染引擎
"""

from pathlib import Path
from typing import Generator, Callable

import cv2
import numpy as np

from effects.base import Effect, create_canvas
from video.sideshow import Slide, Sideshow, SlideEffect
from video.video import distribute_frames_ceil_adjust
from effects import effect_registry


class FrameRenderer:
    """帧渲染器"""

    def __init__(self, sideshow: Sideshow):
        """
        初始化渲染器

        Args:
            sideshow: 幻灯片数据（包含视频配置）
        """
        self.sideshow = sideshow
        self.output_size = (sideshow.width, sideshow.height)
        self._image_cache: dict[str, np.ndarray] = {}

    def load_image(self, image_path: str | Path) -> np.ndarray:
        """加载并缓存图像"""
        path = str(image_path)

        if path in self._image_cache:
            return self._image_cache[path].copy()

        image_path_obj = Path(image_path)
        if not image_path_obj.exists():
            raise FileNotFoundError(f"图像文件不存在: {image_path}")

        image = cv2.imread(str(image_path_obj))
        if image is None:
            raise ValueError(f"无法加载图像: {image_path}")

        self._image_cache[path] = image.copy()
        return image

    def resize_image(self, image: np.ndarray, keep_aspect_ratio: bool = True) -> np.ndarray:
        """调整图像到目标分辨率"""
        target_w, target_h = self.output_size
        h, w = image.shape[:2]

        if not keep_aspect_ratio:
            return cv2.resize(image, (target_w, target_h), interpolation=cv2.INTER_LINEAR)

        # 保持宽高比，裁剪
        scale = max(target_w / w, target_h / h)
        new_w = int(w * scale)
        new_h = int(h * scale)

        resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

        # 居中裁剪
        crop_x = (new_w - target_w) // 2
        crop_y = (new_h - target_h) // 2

        cropped = resized[crop_y : crop_y + target_h, crop_x : crop_x + target_w]
        return cropped

    def preprocess_image(self, image_path: str | Path) -> np.ndarray:
        """加载并预处理图像"""
        image = self.load_image(image_path)
        processed = self.resize_image(image)
        return processed

    def render_slide(
        self,
        slide: Slide,
        total_frames: int,
    ) -> Generator[np.ndarray, None, None]:
        """
        渲染单个幻灯片的所有帧

        Args:
            slide: 幻灯片
            total_frames: 总帧数

        Yields:
            渲染后的帧
        """
        image = self.preprocess_image(slide.file_path)
        canvas = create_canvas(self.output_size[0], self.output_size[1])

        # 当前状态图像（会在特效之间累积变换）
        current_state = image
        last_frame = None

        frame_list = distribute_frames_ceil_adjust(
            self.sideshow.fps, [slide.in_effect.duration, slide.hold_effect.duration, slide.out_effect.duration], total_frames
        )

        # 1. 入场特效
        effect = self._create_effect(slide.in_effect)
        if effect:
            frame_count = frame_list[0]
            for frame in self._render_effect_frames(current_state, effect, frame_count, canvas):
                last_frame = frame
                yield frame
            # 更新状态：使用入场特效的最后一帧
            if last_frame is not None:
                current_state = last_frame

        # 2. Hold 效果
        effect = self._create_effect(slide.hold_effect)
        if effect:
            frame_count = frame_list[1]
            for frame in self._render_effect_frames(current_state, effect, frame_count, canvas):
                last_frame = frame
                yield frame
            # 更新状态：使用hold特效的最后一帧
            if last_frame is not None:
                current_state = last_frame

        # 3. 出场特效
        effect = self._create_effect(slide.out_effect)
        if effect:
            frame_count = frame_list[2]
            for frame in self._render_effect_frames(current_state, effect, frame_count, canvas):
                yield frame

    def _create_effect(
        self, slide_effect: SlideEffect
    ) -> Effect | None:
        """
        根据SlideEffect创建Effect对象

        Args:
            slide_effect: SlideEffect数据

        Returns:
            Effect对象，如果找不到则返回None
        """
        factory = effect_registry.get(slide_effect.effect)
        if factory:
            # 调用工厂函数，传入duration和extra
            return factory(slide_effect.duration, slide_effect.extra)
        return None

    def _render_effect_frames(
        self, image: np.ndarray, effect: Effect, frame_count: int, canvas: np.ndarray
    ) -> Generator[np.ndarray, None, None]:
        """渲染特效的所有帧"""
        for frame_idx in range(frame_count):
            progress = frame_idx / max(frame_count - 1, 1)
            frame = effect.apply(image, progress, canvas)
            yield frame
