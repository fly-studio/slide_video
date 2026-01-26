"""
渲染引擎
"""

from pathlib import Path
from typing import Generator

import numpy as np

from effects.base import Effect
from misc import types
from textures.sprite import ImageSprite
from textures.stage import Stage
from video.sideshow import Slide, Sideshow
from video.video import distribute_frames_ceil_adjust
from effects import effect_registry


class FrameRenderer:
    """帧渲染器"""

    def __init__(self, sideshow: Sideshow, stage: Stage):
        """
        初始化渲染器

        Args:
            sideshow: 幻灯片数据（包含视频配置）
        """
        self.sideshow = sideshow
        self.stage = stage
        self.output_size = (sideshow.width, sideshow.height)
        self._sprite_cache: dict[str, ImageSprite] = {}  # 缓存 Sprite 实例


    def get_or_create_sprite(self, image_path: str | Path) -> ImageSprite:
        """
        获取或创建 ImageSprite

        Args:
            image_path: 图像路径

        Returns:
            ImageSprite 实例
        """
        # 检查缓存
        if image_path in self._sprite_cache:
            sprite = self._sprite_cache[image_path]
            # 重置 Sprite 属性为默认值
            sprite.reset_property()
            return sprite

        w, h = self.output_size

        # 创建 Sprite
        sprite = ImageSprite(image_file=image_path, width=w, height=h, x=0, y=0)

        # 缓存
        self._sprite_cache[image_path] = sprite
        return sprite

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
        # 获取或创建 Sprite
        sprite = self.get_or_create_sprite(slide.file_path)
        self.stage.add_child(sprite)

        frame_list = distribute_frames_ceil_adjust(
            self.sideshow.fps, [slide.in_effect.duration, slide.hold_effect.duration, slide.out_effect.duration], total_frames
        )

        # 1. 入场特效
        effect = self._create_effect(slide.in_effect.effect, types.TransitionType.IN, slide.in_effect.duration, slide.in_effect.extra)
        if effect:
            frame_count = frame_list[0]
            for frame in self._render_effect_frames(sprite, effect, frame_count):
                yield frame

        # 2. Hold 效果
        sprite.mask = None
        effect = self._create_effect(slide.hold_effect.effect, types.TransitionType.HOLD, slide.hold_effect.duration, slide.hold_effect.extra)
        if effect:
            frame_count = frame_list[1]
            for frame in self._render_effect_frames(sprite, effect, frame_count):
                yield frame

        # 3. 出场特效
        effect = self._create_effect(slide.out_effect.effect, types.TransitionType.OUT, slide.out_effect.duration, slide.out_effect.extra)
        if effect:
            frame_count = frame_list[2]
            for frame in self._render_effect_frames(sprite, effect, frame_count):
                yield frame

        # 移除image
        self.stage.remove_child(sprite)

    def _create_effect(
        self,
        effect_name: str,
        transition_type: types.TransitionType,
        duration: int,
        extra: dict
    ) -> Effect | None:
        """
        根据SlideEffect创建Effect对象

        Args:
            effect_name: 效果名称
            duration: 持续时长
            extra: 额外参数

        Returns:
            Effect对象，如果找不到则返回None
        """
        factory = effect_registry.get(effect_name)
        if factory:
            # 调用工厂函数，传入duration和extra
            return factory(transition_type, duration, extra)
        return None

    def _render_effect_frames(
        self,
        sprite: ImageSprite,
        effect: Effect,
        frame_count: int
    ) -> Generator[np.ndarray, None, None]:
        """
        使用 Sprite 渲染特效的所有帧


        :param sprite: ImageSprite 实例
        :param effect: Effect 对象
        :param frame_count: 帧数
        :yield: 渲染后的帧（numpy 数组）
        """
        for frame_idx in range(frame_count):
            progress = frame_idx / max(frame_count - 1, 1)

            # 如果是 TransitionEffect，使用新的 apply_to_sprite 方法
            effect.apply(sprite, progress)

            self.stage.render()
            frame = self.stage.to_ffmpeg()

            yield frame
