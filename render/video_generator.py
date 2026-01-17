"""
视频生成器
"""

from typing import Callable

import time
from .renderer import FrameRenderer
from video.sideshow import Sideshow
from .video_writer import VideoWriter


class VideoGenerator:
    """视频生成器"""

    def __init__(self, sideshow: Sideshow):
        """
        初始化视频生成器

        Args:
            sideshow: 幻灯片数据（包含视频配置）
        """
        self.sideshow = sideshow
        self.renderer = FrameRenderer(sideshow)



    def generate(self, progress_callback: Callable[[int, int, float], None] | None = None) -> None:
        """
        生成视频

        Args:
            progress_callback: 进度回调函数，参数: (当前slide索引, 总slide数)
        """

        start_at = time.perf_counter_ns()
        def callback(current_frame_index: int, total_frames: int):
            if progress_callback:
                speed = current_frame_index / (time.perf_counter_ns() - start_at) * 1_000_000_000 / self.sideshow.fps
                progress_callback(current_frame_index, total_frames, speed)

        with VideoWriter(
            output_path=self.sideshow.file_path,
            width=self.sideshow.width,
            height=self.sideshow.height,
            fps=self.sideshow.fps,
            codec=self.sideshow.codec,
        ) as writer:
            total_frames = self.sideshow.total_frames
            for slide_index, slide in enumerate(self.sideshow.slides):
                frame_offset = self.sideshow.frame_offset(slide_index)
                frame_count = self.sideshow.frame_count(slide_index)
                callback(frame_offset, total_frames)

                # 渲染并写入帧
                for frame_index, frame in enumerate(self.renderer.render_slide(slide, frame_count)):
                    # 计算当前帧索引
                    current_frame_index = frame_offset + frame_index
                    # 写入帧
                    writer.write_frame(frame)
                    callback(current_frame_index+1, total_frames)

            # 完成
            callback(total_frames, total_frames)

            print(
                f"\n✅ 完成！总帧数: {writer.get_frame_count()}, 时长: {writer.get_duration_seconds():.2f}s"
            )
