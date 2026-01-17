"""
幻灯片数据模型
"""

from dataclasses import dataclass, field
from video.video import VideoProperty, distribute_frames_ceil_adjust


@dataclass
class SlideEffect:
    # 持续时长（ms）
    duration: int
    # 特效类型
    effect: str
    # 表达式
    extra: dict

    @property
    def duration_seconds(self) -> float:
        return self.duration / 1000

@dataclass
class Slide:
    # 图片路径
    file_path: str
    # 入场特效
    in_effect: SlideEffect
    # 中间态特效
    hold_effect: SlideEffect
    # 出场特效
    out_effect: SlideEffect

    @property
    def duration(self):
        return self.in_effect.duration + self.hold_effect.duration + self.out_effect.duration

    @property
    def duration_seconds(self) -> float:
        return self.duration / 1000


@dataclass(frozen=True)
class Sideshow(VideoProperty):
    slides: list[Slide] = field(default_factory=list)
    background_color: tuple[int, int, int] = (0xFF, 0xFF, 0xFF) # 背景颜色，默认白色
    _frame_list: list[int] = field(default_factory=list)

    def __post_init__(self):
        object.__setattr__(self, "_frame_list", distribute_frames_ceil_adjust(self.fps, [slide.duration for slide in self.slides]))

    @property
    def duration(self):
        return sum(slide.duration for slide in self.slides)


    @property
    def total_frames(self) -> int:
        """
        获取总帧数

        :return: 总帧数
        """
        return sum(self._frame_list)


    def frame_count(self, slide_index: int) -> int:
        """
        获取幻灯片的帧数量

        :param slide_index: 幻灯片索引
        :return: 帧数量
        """
        if slide_index < 0 or slide_index >= len(self.slides):
            raise IndexError("slide_index out of range")

        return self._frame_list[slide_index]

    def frame_offset(self, slide_index: int) -> int:
        """
        获取幻灯片的帧偏移量

        :param slide_index: 幻灯片索引
        :return: 帧偏移量
        """
        import math
        if slide_index < 0 or slide_index >= len(self.slides):
            raise IndexError("slide_index out of range")

        return sum(self._frame_list[:slide_index])

