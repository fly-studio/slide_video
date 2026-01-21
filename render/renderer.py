"""
渲染引擎
"""

from pathlib import Path
from typing import Generator, Callable

import numpy as np

from effects.base import Effect, create_canvas
from misc.image import load_image, resize_image
from video.sideshow import Slide, Sideshow
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



    def preprocess_image(self, image_path: str | Path) -> np.ndarray:
        """加载并预处理图像"""

        if image_path in self._image_cache:
            return self._image_cache[image_path].copy()

        image = load_image(image_path)
        self._image_cache[image_path] = image_path.copy()
        processed = resize_image(image, width=self.output_size[0], height=self.output_size[1])
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
        # 创建画布，也就是背景
        canvas = create_canvas(self.output_size[0], self.output_size[1], color=self.sideshow.background_color)

        # 当前状态图像（会在特效之间累积变换）
        current_state = image
        last_frame = None

        frame_list = distribute_frames_ceil_adjust(
            self.sideshow.fps, [slide.in_effect.duration, slide.hold_effect.duration, slide.out_effect.duration], total_frames
        )

        # 1. 入场特效
        effect = self._create_effect(slide.in_effect.effect + "_in", slide.in_effect.duration, slide.in_effect.extra)
        if effect:
            frame_count = frame_list[0]
            for frame in self._render_effect_frames(current_state, effect, frame_count, canvas):
                last_frame = frame
                yield frame
            # 更新状态：使用入场特效的最后一帧
            if last_frame is not None:
                current_state = last_frame

        # 2. Hold 效果
        effect = self._create_effect(slide.hold_effect.effect, slide.hold_effect.duration, slide.hold_effect.extra)
        if effect:
            frame_count = frame_list[1]
            for frame in self._render_effect_frames(current_state, effect, frame_count, canvas):
                last_frame = frame
                yield frame
            # 更新状态：使用hold特效的最后一帧
            if last_frame is not None:
                current_state = last_frame

        # 3. 出场特效
        effect = self._create_effect(slide.out_effect.effect + "_out", slide.out_effect.duration, slide.out_effect.extra)
        if effect:
            frame_count = frame_list[2]
            for frame in self._render_effect_frames(current_state, effect, frame_count, canvas):
                yield frame

    def _create_effect(
        self,
        effect_name: str,
        duration: int,
        extra: dict
    ) -> Effect | None:
        """
        根据SlideEffect创建Effect对象

        Args:
            slide_effect: SlideEffect数据

        Returns:
            Effect对象，如果找不到则返回None
        """
        factory = effect_registry.get(effect_name)
        if factory:
            # 调用工厂函数，传入duration和extra
            return factory(duration, extra)
        return None

    def _render_effect_frames(
        self, image: np.ndarray, effect: Effect, frame_count: int, canvas: np.ndarray
    ) -> Generator[np.ndarray, None, None]:
        """渲染特效的所有帧"""
        for frame_idx in range(frame_count):
            progress = frame_idx / max(frame_count - 1, 1)
            frame = effect.apply(image, progress, canvas)
            yield frame
