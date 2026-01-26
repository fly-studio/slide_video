#!/usr/bin/env python3
"""
Slider - 幻灯片特效视频生成器 CLI
"""
import argparse
import asyncio
import atexit
import os
import shutil
import sys
import tempfile
import time
import uuid
from pathlib import Path
from typing import Dict, Any, List
from urllib.parse import urlparse

import httpx
import taichi as ti
import yaml

from video.sideshow import Slide, SlideEffect, Sideshow
from render.video_generator import VideoGenerator


class ConfigLoader:
    """配置文件加载器"""

    def __init__(self, config_path: str, temp_dir: Path):
        self.config_path = config_path
        self.config: Dict[str, Any] = {}
        self.temp_dir = temp_dir

    def load(self) -> Dict[str, Any]:
        """加载配置文件"""
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"配置文件不存在: {self.config_path}")

        with open(self.config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

        return self.config

    def validate(self) -> bool:
        """验证配置文件"""
        required_keys = ["output", "slides"]
        for key in required_keys:
            if key not in self.config:
                raise ValueError(f"配置文件缺少必需字段: {key}")

        # 验证 output 配置
        output = self.config["output"]
        required_output_keys = ["file_path", "fps", "width", "height"]
        for key in required_output_keys:
            if key not in output:
                raise ValueError(f"output 配置缺少必需字段: {key}")

        # 验证 slides 配置
        slides = self.config["slides"]
        if "items" not in slides or not slides["items"]:
            raise ValueError("slides 配置缺少 items 或 items 为空")

        return True


class ImageDownloader:
    """图片下载器（支持并发下载，带并发限制）"""

    def __init__(self, temp_dir: Path, max_concurrent: int = 5):
        self.temp_dir = temp_dir
        self.temp_dir.mkdir(exist_ok=True)
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)

    @staticmethod
    def is_url(path: str) -> bool:
        """判断是否为 URL"""
        try:
            result = urlparse(path)
            return result.scheme in ("http", "https")
        except Exception:
            return False

    async def download_image(self, url: str, client: httpx.AsyncClient) -> str:
        """下载单个图片（带并发控制）"""
        async with self.semaphore:  # 限制并发数
            try:
                # 生成本地文件名
                filename = Path(urlparse(url).path).name
                if not filename:
                    filename = f"image_{hash(url)}.jpg"

                local_path = self.temp_dir / filename

                # 如果已存在，直接返回
                if local_path.exists():
                    print(f"  ✓ 已缓存: {filename}")
                    return str(local_path)

                # 下载图片
                print(f"  ⬇ 下载中: {url}")
                response = await client.get(url, timeout=30.0)
                response.raise_for_status()

                # 保存到本地
                with open(local_path, "wb") as f:
                    f.write(response.content)

                print(f"  ✓ 完成: {filename}")
                return str(local_path)

            except Exception as e:
                print(f"  ✗ 下载失败: {url} - {e}")
                raise

    async def download_images(self, image_paths: List[str]) -> Dict[str, str]:
        """并发下载多个图片（带并发限制）"""
        url_to_local = {}

        # 分离 URL 和本地路径
        urls = [path for path in image_paths if self.is_url(path)]
        local_paths = [path for path in image_paths if not self.is_url(path)]

        # 本地路径直接映射
        for path in local_paths:
            url_to_local[path] = path

        # 并发下载 URL
        if urls:
            print(f"\n📥 开始下载 {len(urls)} 个图片（最大并发: {self.max_concurrent}）...")
            async with httpx.AsyncClient() as client:
                tasks = [self.download_image(url, client) for url in urls]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                for url, result in zip(urls, results):
                    if isinstance(result, Exception):
                        raise result
                    url_to_local[url] = result

            print(f"✅ 所有图片下载完成\n")

        return url_to_local


class SliderCLI:
    """Slider CLI 主类"""

    def __init__(self, config_path: str, gpu_backend: str = "gpu", max_concurrent: int = 5):
        self.config_path = config_path
        self.gpu_backend = gpu_backend
        self.max_concurrent = max_concurrent

        # 创建唯一的临时目录（系统临时目录 + UUID）
        system_temp = Path(tempfile.gettempdir())
        unique_id = uuid.uuid4().hex[:8]
        self.temp_dir = system_temp / f"slider_{unique_id}"
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        # 注册清理函数
        atexit.register(self.cleanup)

        self.loader = ConfigLoader(config_path, self.temp_dir)
        self.downloader = ImageDownloader(self.temp_dir, max_concurrent=max_concurrent)

    def cleanup(self):
        """清理临时目录"""
        if self.temp_dir.exists():
            try:
                shutil.rmtree(self.temp_dir)
                print(f"🧹 已清理临时目录: {self.temp_dir}")
            except Exception as e:
                print(f"⚠️  清理临时目录失败: {e}")

    def init_taichi(self):
        """初始化 Taichi"""
        if self.gpu_backend == "cpu":
            ti.init(
                arch=ti.cpu,
                debug=True,
                log_level=ti.TRACE,
                cpu_max_num_threads=16,
                advanced_optimization=True,
                offline_cache=True,
            )
            print("🖥️  使用 CPU 后端")
        else:
            ti.init(
                arch=ti.gpu,
                device_memory_GB=2.0,
                advanced_optimization=True,
                offline_cache=True,
            )
            print("🚀 使用 GPU 后端")

    async def prepare_images(self, config: Dict[str, Any]) -> Dict[str, str]:
        """准备图片（下载 URL 图片）"""
        image_paths = [item["image"] for item in config["slides"]["items"]]
        return await self.downloader.download_images(image_paths)

    def build_slides(self, config: Dict[str, Any], image_map: Dict[str, str]) -> List[Slide]:
        """根据配置构建 Slide 列表"""
        slides = []
        slides_config = config["slides"]
        default_durations = slides_config.get("default_durations", {})

        # 默认时长
        default_in = default_durations.get("in", 500)
        default_hold = default_durations.get("hold", 3500)
        default_out = default_durations.get("out", 500)

        for item in slides_config["items"]:
            # 获取本地图片路径
            image_path = image_map[item["image"]]

            # 构建效果
            in_effect_config = item.get("in_effect", {})
            hold_effect_config = item.get("hold_effect", {})
            out_effect_config = item.get("out_effect", {})

            in_effect = SlideEffect(
                duration=in_effect_config.get("duration", default_in),
                effect_name=in_effect_config.get("name", "fade"),
                extra_params=in_effect_config.get("params", {}),
            )

            hold_effect = SlideEffect(
                duration=hold_effect_config.get("duration", default_hold),
                effect_name=hold_effect_config.get("name", "pan"),
                extra_params=hold_effect_config.get("params", {"direction": "center"}),
            )

            out_effect = SlideEffect(
                duration=out_effect_config.get("duration", default_out),
                effect_name=out_effect_config.get("name", "fade"),
                extra_params=out_effect_config.get("params", {}),
            )

            slide = Slide(
                file_path=image_path,
                in_effect=in_effect,
                hold_effect=hold_effect,
                out_effect=out_effect,
            )
            slides.append(slide)

        return slides

    async def run(self):
        """运行主流程"""
        print("=" * 60)
        print("  Slider - 幻灯片特效视频生成器")
        print("=" * 60)
        print(f"📁 临时目录: {self.temp_dir}")
        print()

        # 1. 加载配置
        print("📄 加载配置文件...")
        config = self.loader.load()
        self.loader.validate()
        print("✅ 配置文件验证通过\n")

        # 2. 初始化 Taichi
        self.init_taichi()
        print()

        # 3. 准备图片（下载 URL 图片）
        image_map = await self.prepare_images(config)

        # 4. 构建 Slides
        print("🎬 构建幻灯片...")
        slides = self.build_slides(config, image_map)
        print(f"✅ 共 {len(slides)} 个幻灯片\n")

        # 5. 创建 Sideshow
        output_config = config["output"]
        sideshow = Sideshow(
            fps=output_config["fps"],
            width=output_config["width"],
            height=output_config["height"],
            file_path=output_config["file_path"],
            slides=slides,
            codec=output_config.get("codec", "libx264"),
        )

        # 6. 生成视频
        start_time = time.time()
        generator = VideoGenerator(sideshow, write_mode="ffmpeg")
        print("🎥 开始生成视频...\n")

        def progress_callback(current, total, speed):
            percentage = (current / total * 100) if total > 0 else 0
            bar_width = 30
            filled = int(bar_width * current / total) if total > 0 else 0
            bar = "█" * filled + "░" * (bar_width - filled)
            print(
                f"\r  [{bar}] {percentage:5.1f}% ({current}/{total}) 速度: {speed:.2f}x",
                end="",
                flush=True,
            )

        generator.generate(progress_callback)

        elapsed = time.time() - start_time
        print(f"\n\n✅ 视频生成完成！")
        print(f"📁 输出文件: {output_config['file_path']}")
        print(f"⏱️  耗时: {elapsed:.2f}s")
        print()


def main():
    """CLI 入口"""
    parser = argparse.ArgumentParser(
        description="Slider - GPU 加速的幻灯片视频生成器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s -c config.yaml                         # 使用默认配置
  %(prog)s -c config.yaml --backend cpu           # 使用 CPU 后端
  %(prog)s -c config.yaml -j 10                   # 设置最大并发下载数为 10
  %(prog)s -c config.yaml --backend gpu -j 3      # GPU 后端 + 3 个并发下载
        """,
    )

    parser.add_argument(
        "-c",
        "--config",
        type=str,
        default="config.yaml",
        help="配置文件路径 (默认: config.yaml)",
    )

    parser.add_argument(
        "-b",
        "--backend",
        type=str,
        choices=["gpu", "cpu"],
        default="gpu",
        help="Taichi 后端 (默认: gpu)",
    )

    parser.add_argument(
        "-j",
        "--max-concurrent",
        type=int,
        default=5,
        help="图片下载最大并发数 (默认: 5)",
    )

    args = parser.parse_args()

    try:
        cli = SliderCLI(
            config_path=args.config,
            gpu_backend=args.backend,
            max_concurrent=args.max_concurrent,
        )
        asyncio.run(cli.run())
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
