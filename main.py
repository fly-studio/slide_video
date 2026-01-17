"""
Slider - 幻灯片特效视频生成器
"""

from video.sideshow import Slide, SlideEffect, Sideshow
from render.video_generator import VideoGenerator
import time

# 时长配置（毫秒）
IN_DURATION = 500  # 入场 0.5s
HOLD_DURATION = 2000  # Hold 4s
OUT_DURATION = 500  # 出场 0.5s


def main():
    import cv2
    """主函数"""
    print("=" * 60)
    print("  Slider - 幻灯片特效视频生成器")
    print("=" * 60)
    print()


    # 1. 手动定义每个 slide 的特效（写死，确保多次执行效果一致）
    slides = [
        Slide(
            file_path="0.jpg",
            in_effect=SlideEffect(IN_DURATION, "rotate", {}),
            hold_effect=SlideEffect(HOLD_DURATION, "pan_top", {}),
            out_effect=SlideEffect(OUT_DURATION, "rotate", {}),
        ),
        Slide(
            file_path="1.jpg",
            in_effect=SlideEffect(IN_DURATION, "fade", {}),
            hold_effect=SlideEffect(HOLD_DURATION, "pan_bottom", {}),
            out_effect=SlideEffect(OUT_DURATION, "fade", {}),
        ),
        Slide(
            file_path="2.jpg",
            in_effect=SlideEffect(IN_DURATION, "slide", {}),
            hold_effect=SlideEffect(HOLD_DURATION, "pan_left", {}),
            out_effect=SlideEffect(OUT_DURATION, "slide", {}),
        ),
        Slide(
            file_path="3.jpg",
            in_effect=SlideEffect(IN_DURATION, "zoom", {}),
            hold_effect=SlideEffect(HOLD_DURATION, "pan_right", {}),
            out_effect=SlideEffect(OUT_DURATION, "zoom", {}),
        ),
        Slide(
            file_path="4.jpg",
            in_effect=SlideEffect(IN_DURATION, "wipe_circle", {}),
            hold_effect=SlideEffect(HOLD_DURATION, "pan_top_left", {}),
            out_effect=SlideEffect(OUT_DURATION, "wipe_circle", {}),
        ),
        # Slide(
        #     file_path="5.jpg",
        #     in_effect=SlideEffect(IN_DURATION, "wipe_star", {}),
        #     hold_effect=SlideEffect(HOLD_DURATION, "pan_top_right", {}),
        #     out_effect=SlideEffect(OUT_DURATION, "wipe_star", {}),
        # ),
        # Slide(
        #     file_path="6.jpg",
        #     in_effect=SlideEffect(IN_DURATION, "fade", {}),
        #     hold_effect=SlideEffect(HOLD_DURATION, "pan_bottom_left", {}),
        #     out_effect=SlideEffect(OUT_DURATION, "fade", {}),
        # ),
        # Slide(
        #     file_path="7.jpg",
        #     in_effect=SlideEffect(IN_DURATION, "fade", {}),
        #     hold_effect=SlideEffect(HOLD_DURATION, "pan_bottom_right", {}),
        #     out_effect=SlideEffect(OUT_DURATION, "fade", {}),
        # ),
        # Slide(
        #     file_path="8.jpg",
        #     in_effect=SlideEffect(IN_DURATION, "fade", {}),
        #     hold_effect=SlideEffect(HOLD_DURATION, "zoom_center", {}),
        #     out_effect=SlideEffect(OUT_DURATION, "fade", {}),
        # ),
        # # 循环使用9个效果
        # Slide(
        #     file_path="9.jpg",
        #     in_effect=SlideEffect(IN_DURATION, "fade", {}),
        #     hold_effect=SlideEffect(HOLD_DURATION, "pan_top", {}),
        #     out_effect=SlideEffect(OUT_DURATION, "fade", {}),
        # ),
        # Slide(
        #     file_path="10.jpg",
        #     in_effect=SlideEffect(IN_DURATION, "fade", {}),
        #     hold_effect=SlideEffect(HOLD_DURATION, "pan_bottom", {}),
        #     out_effect=SlideEffect(OUT_DURATION, "fade", {}),
        # ),
        # Slide(
        #     file_path="11.jpg",
        #     in_effect=SlideEffect(IN_DURATION, "fade", {}),
        #     hold_effect=SlideEffect(HOLD_DURATION, "pan_left", {}),
        #     out_effect=SlideEffect(OUT_DURATION, "fade", {}),
        # ),
        # Slide(
        #     file_path="12.jpg",
        #     in_effect=SlideEffect(IN_DURATION, "fade", {}),
        #     hold_effect=SlideEffect(HOLD_DURATION, "pan_right", {}),
        #     out_effect=SlideEffect(OUT_DURATION, "fade", {}),
        # ),
    ]

    # 2. 创建 Sideshow（包含视频配置）
    sideshow = Sideshow(
        fps=30, width=720, height=1280, file_path="output.mp4", slides=slides, codec="h264_nvenc"
    )

    # 3. 生成视频

    start_at = time.time()

    generator = VideoGenerator(sideshow)
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
    main()
