"""
Slider - 幻灯片特效视频生成器
"""
import threading

from video.sideshow import Slide, SlideEffect, Sideshow
from render.video_generator import VideoGenerator
import time
import taichi as ti

# 时长配置（毫秒）
IN_DURATION = 500  # 入场 0.5s
HOLD_DURATION = 2000  # Hold 4s
OUT_DURATION = 500  # 出场 0.5s

ti.init(arch=ti.cpu,
        debug=True,
        log_level=ti.TRACE,
        cpu_max_num_threads=16,
        advanced_optimization=True,
        offline_cache=True,
)


def main(index: str):
    """主函数"""
    print("=" * 60)
    print("  Slide - 幻灯片特效视频生成器")
    print("=" * 60)
    print()


    # 1. 手动定义每个 slide 的特效（写死，确保多次执行效果一致）
    slides = [
        Slide(
            file_path="0.jpg",
            in_effect=SlideEffect(IN_DURATION, "rectangle", {}),
            hold_effect=SlideEffect(HOLD_DURATION, "pan", {"direction": "left"}),
            out_effect=SlideEffect(OUT_DURATION, "rectangle", {}),
        ),
        # Slide(
        #     file_path="0.jpg",
        #     in_effect=SlideEffect(IN_DURATION, "rotate", {}),
        #     hold_effect=SlideEffect(HOLD_DURATION, "pan", {"direction": "top"}),
        #     out_effect=SlideEffect(OUT_DURATION, "rotate", {}),
        # ),
        # Slide(
        #     file_path="1.jpg",
        #     in_effect=SlideEffect(IN_DURATION, "fade", {}),
        #     hold_effect=SlideEffect(HOLD_DURATION, "pan", {"direction": "bottom"}),
        #     out_effect=SlideEffect(OUT_DURATION, "fade", {}),
        # ),
        # Slide(
        #     file_path="2.jpg",
        #     in_effect=SlideEffect(IN_DURATION, "slide", {}),
        #     hold_effect=SlideEffect(HOLD_DURATION, "pan", {"direction": "left"}),
        #     out_effect=SlideEffect(OUT_DURATION, "slide", {}),
        # ),
        # Slide(
        #     file_path="3.jpg",
        #     in_effect=SlideEffect(IN_DURATION, "zoom", {}),
        #     hold_effect=SlideEffect(HOLD_DURATION, "pan", {"direction": "right"}),
        #     out_effect=SlideEffect(OUT_DURATION, "zoom", {}),
        # ),
        # Slide(
        #     file_path="4.jpg",
        #     in_effect=SlideEffect(IN_DURATION, "circle", {}),
        #     hold_effect=SlideEffect(HOLD_DURATION, "pan", {"direction": "top_left"}),
        #     out_effect=SlideEffect(OUT_DURATION, "circle", {}),
        # ),
        # Slide(
        #     file_path="5.jpg",
        #     in_effect=SlideEffect(IN_DURATION, "star", {}),
        #     hold_effect=SlideEffect(HOLD_DURATION, "pan", {"direction": "top_right"}),
        #     out_effect=SlideEffect(OUT_DURATION, "star", {}),
        # ),
        # Slide(
        #     file_path="6.jpg",
        #     in_effect=SlideEffect(IN_DURATION, "top", {}),
        #     hold_effect=SlideEffect(HOLD_DURATION, "pan", {"direction": "bottom_left"}),
        #     out_effect=SlideEffect(OUT_DURATION, "top", {}),
        # ),
        # Slide(
        #     file_path="7.jpg",
        #     in_effect=SlideEffect(IN_DURATION, "left", {}),
        #     hold_effect=SlideEffect(HOLD_DURATION, "pan", {"direction": "bottom_right"}),
        #     out_effect=SlideEffect(OUT_DURATION, "left", {}),
        # ),
        # Slide(
        #     file_path="8.jpg",
        #     in_effect=SlideEffect(IN_DURATION, "diamond", {}),
        #     hold_effect=SlideEffect(HOLD_DURATION, "zoom_center", {}),
        #     out_effect=SlideEffect(OUT_DURATION, "diamond", {}),
        # ),
        # Slide(
        #     file_path="9.jpg",
        #     in_effect=SlideEffect(IN_DURATION, "triangle", {}),
        #     hold_effect=SlideEffect(HOLD_DURATION, "pan", {"direction": "top"}),
        #     out_effect=SlideEffect(OUT_DURATION, "triangle", {}),
        # ),
        # Slide(
        #     file_path="10.jpg",
        #     in_effect=SlideEffect(IN_DURATION, "cross", {}),
        #     hold_effect=SlideEffect(HOLD_DURATION, "pan", {"direction": "bottom"}),
        #     out_effect=SlideEffect(OUT_DURATION, "cross", {}),
        # ),
        # Slide(
        #     file_path="11.jpg",
        #     in_effect=SlideEffect(IN_DURATION, "fade", {}),
        #     hold_effect=SlideEffect(HOLD_DURATION, "pan", {"direction": "left"}),
        #     out_effect=SlideEffect(OUT_DURATION, "fade", {}),
        # ),
        # Slide(
        #     file_path="12.jpg",
        #     in_effect=SlideEffect(IN_DURATION, "fade", {}),
        #     hold_effect=SlideEffect(HOLD_DURATION, "pan", {"direction": "right"}),
        #     out_effect=SlideEffect(OUT_DURATION, "fade", {}),
        # ),
    ]

    # 2. 创建 Sideshow（包含视频配置）
    sideshow = Sideshow(
        fps=30, width=720, height=1280, file_path=f"output-{index}.mp4", slides=slides, codec="h264_nvenc"
    )

    # 3. 生成视频

    start_at = time.time()

    generator = VideoGenerator(sideshow, write_mode='ffmpeg')
    print("🎬 开始生成视频...")
    print()


    def progress(current, total, speed):
        percentage = (current / total * 100) if total > 0 else 0
        bar_width = 30
        filled = int(bar_width * current / total) if total > 0 else 0
        bar = "█" * filled + "░" * (bar_width - filled)
        print(f"\r  [{bar}] {percentage:5.1f}% ({current}/{total}) speed: {speed:.2f}x\t\tFFMPEG:", end="", flush=True)

    generator.generate(progress)

    print(f"\n✅ 完成！耗时: {time.time() - start_at:.2f}s")


if __name__ == "__main__":
    main(0)
    #thread1 = threading.Thread(target=main, args=(0,))
    #thread2 = threading.Thread(target=main, args=(1,))
    #thread3 = threading.Thread(target=main, args=(2,))
    #thread1.start()
    #thread2.start()
    #thread3.start()
