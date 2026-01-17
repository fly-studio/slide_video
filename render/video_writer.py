"""
视频输出管道

使用 FFmpeg 将帧写入视频文件
"""

import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np


class VideoWriter:
    """
    FFmpeg 视频输出管道

    使用 context manager 模式管理 ffmpeg 进程生命周期
    """

    def __init__(
        self,
        output_path: str,
        width: int,
        height: int,
        fps: int,
        codec: str = "libx264",
        pix_fmt: str = "yuv420p",
        crf: int = 18,
        preset: str = "medium",
        audio_file: str | None = None,
        **extra_params: Any,
    ):
        """
        初始化视频写入器

        Args:
            output_path: 输出文件路径
            width: 视频宽度
            height: 视频高度
            fps: 帧率
            codec: 视频编码器，默认 "libx264" (H.264)
            pix_fmt: 像素格式，默认 "yuv420p"
            crf: 质量控制，0-51，越小质量越高，默认18（视觉无损）
            preset: 编码速度预设，默认 "medium"
                   选项: ultrafast, superfast, veryfast, faster, fast,
                        medium, slow, slower, veryslow
            audio_file: 音频文件路径，默认 None
            **extra_params: 额外的 ffmpeg 参数
        """
        self.output_path = output_path
        self.width = width
        self.height = height
        self.fps = fps
        self.codec = codec
        self.pix_fmt = pix_fmt
        self.crf = crf
        self.preset = preset
        self.extra_params = extra_params
        self.audio_file = audio_file

        self.process: subprocess.Popen | None = None
        self.frame_count = 0

    def __enter__(self) -> "VideoWriter":
        """启动 ffmpeg 进程"""
        self._start_ffmpeg()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """关闭 ffmpeg 进程"""
        has_error = exc_type is not None
        self._close_ffmpeg(has_error=has_error)

    def _use_nvenc(self) -> bool:
        """是否使用NVENC编码"""
        return self.codec.endswith("nvenc")

    def _start_ffmpeg(self) -> None:
        """启动 ffmpeg 进程"""
        # 确保输出目录存在
        output_dir = Path(self.output_path).parent
        if output_dir != Path(".") and not output_dir.exists():
            output_dir.mkdir(parents=True, exist_ok=True)

        # 构建 ffmpeg 命令
        cmd = [
            "ffmpeg",
            "-y",  # 覆盖输出文件
            # 视频输入参数
            "-f", "rawvideo",  # 输入格式：原始视频
            "-vcodec", "rawvideo",
            "-s", f"{self.width}x{self.height}",  # 输入尺寸
            "-pix_fmt", "bgr24",  # OpenCV 默认 BGR 格式
            "-r", str(self.fps),  # 输入帧率
            "-i", "-",  # 从 stdin 读取视频流
        ]



        # 处理音频部分
        if self.audio_file is not None and self.audio_file.strip() != "":
            # 添加音频输入文件
            cmd.extend(["-i", self.audio_file])
            # 设置音频编码器
            cmd.extend(["-c:a", "aac"])
        else:
            # 无音频
            cmd.append("-an")

        # 添加视频输出参数
        cmd.extend([
            "-vcodec", self.codec,  # 视频编码器
            "-pix_fmt", self.pix_fmt,  # 输出像素格式
            "-crf", str(self.crf),  # 质量控制
            "-preset", self.preset,  # 编码速度
        ])

        # 添加硬件加速参数
        if self._use_nvenc():
            cmd.extend([
                "-gpu", "0",
                '-rc', 'vbr_hq',  # 视频码率控制
                '-profile:v', 'high',  # 视频编码配置
            ])
        else:
            cmd.extend([
                '-tune', 'stillimage', # 优化静态/慢动内容
            ])

        # 添加额外参数
        for key, value in self.extra_params.items():
            cmd.extend([f"-{key}", str(value)])

        # 输出文件
        cmd.append(self.output_path)
        print(f"ffmpeg 命令: {' '.join(cmd)}")
        # 启动进程
        try:
            self.process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                #stdout=subprocess.PIPE,
                #stderr=subprocess.PIPE,
            )
            print(f"ffmpeg 已经启动，并等待stdin输入")
        except FileNotFoundError:
            raise RuntimeError(
                "FFmpeg 未找到。请确保 FFmpeg 已安装并在 PATH 中。\n"
                "下载地址: https://ffmpeg.org/download.html"
            )

    def write_frame(self, frame: np.ndarray) -> None:
        """
        写入一帧

        Args:
            frame: 帧数据，numpy 数组 (H, W, C)，BGR 格式

        Raises:
            RuntimeError: 如果 ffmpeg 进程未启动或已关闭
            ValueError: 如果帧尺寸不匹配
        """
        if self.process is None or self.process.stdin is None:
            raise RuntimeError("FFmpeg 进程未启动")

        # 验证帧尺寸
        h, w = frame.shape[:2]
        if w != self.width or h != self.height:
            raise ValueError(
                f"帧尺寸不匹配。期望 {self.width}x{self.height}，得到 {w}x{h}"
            )

        # 写入帧数据
        try:
            self.process.stdin.write(frame.tobytes())
            self.frame_count += 1
        except BrokenPipeError:
            # FFmpeg 进程可能已终止，获取错误信息
            if self.process.stderr:
                error = self.process.stderr.read().decode("utf-8", errors="ignore")
                raise RuntimeError(f"FFmpeg 错误:\n{error}")
            raise RuntimeError("FFmpeg 进程意外终止")

    def _close_ffmpeg(self, has_error: bool) -> None:
        """
        关闭 ffmpeg 进程

        Args:
            has_error: 是否发生了错误。如果为True，使用超时并强制终止；否则等待正常退出
        """
        if self.process and self.process.stdin:
            # 关闭输入流
            self.process.stdin.close()

            if has_error:
                # 发生错误，使用2秒超时，超时后强制终止
                try:
                    self.process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    print(f"FFmpeg 进程未在2秒内退出，强制终止", file=sys.stderr)
                    self.process.kill()
                    self.process.wait()  # 等待kill完成
            else:
                # 正常退出，等待ffmpeg完成编码和封装
                self.process.wait()

            # 检查返回码
            if self.process.returncode != 0 and self.process.stderr:
                error = self.process.stderr.read().decode("utf-8", errors="ignore")
                print(f"FFmpeg 警告:\n{error}", file=sys.stderr)

            self.process = None

    def get_frame_count(self) -> int:
        """获取已写入的帧数"""
        return self.frame_count

    def get_duration_seconds(self) -> float:
        """获取视频时长（秒）"""
        return self.frame_count / self.fps

    def __repr__(self) -> str:
        """字符串表示"""
        return (
            f"VideoWriter("
            f"output='{self.output_path}', "
            f"size={self.width}x{self.height}, "
            f"fps={self.fps}, "
            f"frames={self.frame_count})"
        )


def check_ffmpeg_installed() -> bool:
    """
    检查 FFmpeg 是否已安装

    Returns:
        是否已安装
    """
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=5,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def get_ffmpeg_version() -> str | None:
    """
    获取 FFmpeg 版本

    Returns:
        版本字符串，如果未安装则返回 None
    """
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=5,
            text=True,
        )
        if result.returncode == 0:
            # 提取第一行的版本信息
            first_line = result.stdout.split("\n")[0]
            return first_line
        return None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
