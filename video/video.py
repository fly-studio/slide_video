import math
from dataclasses import dataclass
from abc import ABC, abstractmethod

@dataclass(frozen=True)
class VideoProperty(ABC):
    width: int
    height: int
    file_path: str
    audio_file: str | None = None
    fps: int = 30
    # 编码格式: libx264, h264_nvenc, libx265, hevc_nvenc, libaom-av1, av1_nvenc（仅RTX 30+支持）
    codec: str = "libx264"


    @property
    @abstractmethod
    def duration(self) -> int:
        pass

    @property
    def duration_seconds(self) -> float:
        return self.duration / 1000


def distribute_frames_ceil_adjust(fps: int, duration_ms_list: list[int], total_frames: int = None) -> list[int]:
    """
    均匀分布帧数，确保总帧数严格等于 总时长×FPS 的精确值。

    核心逻辑：
    1. 每段先ceil取整，保证单段帧数不亏；
    2. 计算总帧数delta，均匀调整（多减少加），最终总帧数严格等于 总时长×FPS 的精确值；
    3. 误差均匀分散，避免集中在某一段。
    """
    # 1. 基础计算：总时长（秒）、目标总帧数（精确值取整，比如总时长×FPS=902.7→903）
    target_total_frames = round(sum(duration_ms_list) / 1000.0 * fps) if total_frames is None else total_frames  # 目标总帧数

    # 2. 每段先ceil取整，得到初始帧数列表
    frame_list = []
    for d_ms in duration_ms_list:
        theory_frames = (d_ms / 1000.0) * fps
        frame_list.append(math.ceil(theory_frames))  # 每段先ceil，保证单段不亏

    # 3. 计算delta（初始总帧数 - 目标总帧数），需要调整的帧数
    current_total = sum(frame_list)
    delta = current_total - target_total_frames

    # 4. 均匀调整delta：多了就减，少了就加，误差分散到列表中
    if delta != 0:
        idx = 0
        list_len = len(frame_list)
        while delta != 0:
            # 保证调整后帧数≥1（避免减到0帧）
            if delta > 0 and frame_list[idx] > 1:
                frame_list[idx] -= 1
                delta -= 1
            elif delta < 0:
                frame_list[idx] += 1
                delta += 1
            # 循环遍历列表，均匀调整（0→1→2→...→n→0...）
            idx = (idx + 1) % list_len

    return frame_list


if __name__ == "__main__":
     # 测试场景：30FPS，60段各1003ms → 总时长=60×1003ms=60.18s → 目标总帧数=60.18×30=1805.4→round=1805
    fps = 30
    duration_ms_list = [1003 for _ in range(60)]  # 60段，每段1003ms

    # 计算帧列表
    frame_list = distribute_frames_ceil_adjust(fps, duration_ms_list)

    # 验证结果
    print(f"单段初始ceil帧数：{math.ceil(1003/1000*30)}")  # 1003ms→30.09帧→ceil=31
    print(f"调整后前10帧：{frame_list[:10]}")
    print(f"调整后总帧数：{sum(frame_list)}")  # 严格等于1805
    print(f"目标总帧数：{round(sum(duration_ms_list)/1000*fps)}")  # 1805
    print(f"是否完全匹配：{sum(frame_list) == round(sum(duration_ms_list)/1000*fps)}")  # True