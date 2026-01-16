# Slider 系统架构设计

## 1. 整体架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                          Main Entry                          │
│                          (main.py)                           │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                      Configuration                           │
│                        (config.py)                           │
│  • FPS配置  • 分辨率配置  • 时长配置  • 特效配置             │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                     Video Generator                          │
│                    (video_generator.py)                      │
│              编排整个视频生成流程                            │
└─────┬─────────────────────┬─────────────────────┬───────────┘
      │                     │                     │
      ▼                     ▼                     ▼
┌───────────┐      ┌─────────────────┐    ┌──────────────┐
│  Renderer │      │  Effect System  │    │ Video Writer │
│ (渲染器)  │◄─────┤   (特效系统)    │    │ (视频输出)   │
└───────────┘      └─────────────────┘    └──────────────┘
      │                     │                     │
      │                     ▼                     │
      │            ┌─────────────────┐            │
      │            │  Easing Module  │            │
      │            │  (缓动函数)     │            │
      │            └─────────────────┘            │
      │                                            │
      └─────────────────────┬──────────────────────┘
                            ▼
                    ┌──────────────┐
                    │    FFmpeg    │
                    │   Pipeline   │
                    └──────────────┘
```

## 2. 核心模块设计

### 2.1 数据模型层 (sideshow.py) ✓ 已实现

```python
@dataclass
class SlideEffect:
    duration: int      # 持续时长(ms)
    effect: str        # 特效类型
    expr: str          # 表达式/参数

@dataclass
class Slide:
    start_at: int
    file_path: str
    in_effect: SlideEffect      # 入场特效
    hold_effect: SlideEffect    # Hold效果
    out_effect: SlideEffect     # 出场特效

@dataclass
class Sideshow:
    slides: list[Slide]
```

### 2.2 缓动函数模块 (easing.py) 🆕

**职责**: 提供CSS3标准缓动曲线实现

**关键特性**:
- 实现CSS3标准缓动函数
- 与前端完全一致的算法
- 支持自定义cubic-bezier

**核心接口**:
```python
class EasingFunction(Protocol):
    """缓动函数协议"""
    def __call__(self, t: float) -> float:
        """
        Args:
            t: 进度值 [0.0, 1.0]
        Returns:
            缓动后的值 [0.0, 1.0]
        """
        ...

# 预定义缓动函数
def ease(t: float) -> float:
    """CSS3 ease: cubic-bezier(0.25, 0.1, 0.25, 1.0)"""

def ease_in(t: float) -> float:
    """CSS3 ease-in: cubic-bezier(0.42, 0, 1.0, 1.0)"""

def ease_out(t: float) -> float:
    """CSS3 ease-out: cubic-bezier(0, 0, 0.58, 1.0)"""

def ease_in_out(t: float) -> float:
    """CSS3 ease-in-out: cubic-bezier(0.42, 0, 0.58, 1.0)"""

def linear(t: float) -> float:
    """线性: cubic-bezier(0, 0, 1.0, 1.0)"""

def cubic_bezier(p1x: float, p1y: float, p2x: float, p2y: float) -> EasingFunction:
    """创建自定义cubic-bezier缓动函数"""
```

**设计原则**:
- 使用贝塞尔曲线标准算法
- 与CSS3规范完全对齐
- 易于前端复现

### 2.3 特效系统 (effects/) 🆕

#### 2.3.1 基础抽象 (effects/base.py)

```python
from abc import ABC, abstractmethod
from typing import Callable
import numpy as np

class Effect(ABC):
    """特效基类"""

    def __init__(self, duration_ms: int, easing: Callable[[float], float]):
        self.duration_ms = duration_ms
        self.easing = easing

    @abstractmethod
    def apply(self, image: np.ndarray, progress: float, **params) -> np.ndarray:
        """
        应用特效到图像

        Args:
            image: 输入图像 (H, W, C)
            progress: 原始进度 [0.0, 1.0]
            **params: 特效参数

        Returns:
            处理后的图像
        """
        pass

    def get_eased_progress(self, progress: float) -> float:
        """应用缓动函数"""
        return self.easing(progress)
```

#### 2.3.2 转场特效 (effects/transition.py)

```python
class FadeEffect(Effect):
    """淡入淡出特效"""

class RotateEffect(Effect):
    """旋转入场/出场"""

class SlideEffect(Effect):
    """4方向移入移出
    - TOP: 从上往下
    - BOTTOM: 从下往上
    - LEFT: 从左往右
    - RIGHT: 从右往左
    """

class ZoomEffect(Effect):
    """缩放特效 (放大/缩小)"""

class BlindsEffect(Effect):
    """百叶窗特效"""

class PushEffect(Effect):
    """推送特效"""
```

#### 2.3.3 Ken Burns效果 (effects/kenburns.py)

```python
from enum import Enum

class KenBurnsDirection(Enum):
    """Ken Burns 8方向"""
    TOP = "top"
    BOTTOM = "bottom"
    LEFT = "left"
    RIGHT = "right"
    TOP_LEFT = "top_left"
    TOP_RIGHT = "top_right"
    BOTTOM_LEFT = "bottom_left"
    BOTTOM_RIGHT = "bottom_right"

class KenBurnsEffect(Effect):
    """Ken Burns 效果

    实现缓慢的平移+缩放，产生动态感
    """

    def __init__(
        self,
        duration_ms: int,
        direction: KenBurnsDirection,
        zoom_range: tuple[float, float] = (1.0, 1.2),  # 起始和结束缩放比例
        easing: Callable[[float], float] = ease_in_out
    ):
        super().__init__(duration_ms, easing)
        self.direction = direction
        self.zoom_range = zoom_range
```

### 2.4 渲染引擎 (renderer.py) 🆕

```python
class FrameRenderer:
    """帧渲染器

    职责:
    - 加载和预处理图像
    - 应用特效生成帧
    - 分辨率转换
    """

    def __init__(self, output_size: tuple[int, int]):
        """
        Args:
            output_size: (width, height) 输出分辨率
        """
        self.output_size = output_size

    def load_image(self, image_path: str) -> np.ndarray:
        """加载并预处理图像"""

    def resize_image(self, image: np.ndarray) -> np.ndarray:
        """调整图像到目标分辨率"""

    def render_slide(
        self,
        slide: Slide,
        fps: int,
        effect_registry: dict[str, Effect]
    ) -> Generator[np.ndarray, None, None]:
        """
        渲染单个slide的所有帧

        Returns:
            生成器，逐帧yield numpy数组
        """
```

### 2.5 视频输出管道 (video_writer.py) 🆕

```python
import subprocess
from typing import Generator

class VideoWriter:
    """FFmpeg视频输出管道

    职责:
    - 启动ffmpeg进程
    - 管道写入帧数据
    - 处理进程生命周期
    """

    def __init__(
        self,
        output_path: str,
        width: int,
        height: int,
        fps: int,
        codec: str = "libx264",
        pix_fmt: str = "yuv420p"
    ):
        self.output_path = output_path
        self.width = width
        self.height = height
        self.fps = fps
        self.codec = codec
        self.pix_fmt = pix_fmt
        self.process: subprocess.Popen | None = None

    def __enter__(self):
        """启动ffmpeg进程"""
        cmd = [
            'ffmpeg',
            '-y',  # 覆盖输出文件
            '-f', 'rawvideo',
            '-vcodec', 'rawvideo',
            '-s', f'{self.width}x{self.height}',
            '-pix_fmt', 'bgr24',  # OpenCV默认BGR格式
            '-r', str(self.fps),
            '-i', '-',  # 从stdin读取
            '-an',  # 无音频
            '-vcodec', self.codec,
            '-pix_fmt', self.pix_fmt,
            self.output_path
        ]
        self.process = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        return self

    def write_frame(self, frame: np.ndarray):
        """写入一帧"""

    def __exit__(self, *args):
        """关闭进程"""
```

### 2.6 配置管理 (config.py) 🆕

```python
from dataclasses import dataclass
from typing import Literal

@dataclass
class VideoConfig:
    """视频配置"""
    fps: int = 30
    output_width: int = 720
    output_height: int = 1280
    output_path: str = "output.mp4"
    codec: str = "libx264"
    pix_fmt: str = "yuv420p"

@dataclass
class SlideTimingConfig:
    """幻灯片时长配置"""
    in_duration_ms: int = 500      # 入场特效 0.5s
    hold_duration_ms: int = 3500   # Hold效果 3.5s
    out_duration_ms: int = 500     # 出场特效 0.5s

    @property
    def total_duration_ms(self) -> int:
        return self.in_duration_ms + self.hold_duration_ms + self.out_duration_ms

@dataclass
class Config:
    """总配置"""
    video: VideoConfig
    timing: SlideTimingConfig

    # 默认缓动函数
    default_easing: str = "ease-in-out"
```

### 2.7 视频生成器 (video_generator.py) 🆕

```python
class VideoGenerator:
    """视频生成器 - 编排整个流程

    职责:
    - 协调各个模块
    - 管理生成流程
    - 进度报告
    """

    def __init__(self, config: Config):
        self.config = config
        self.renderer = FrameRenderer(
            output_size=(config.video.output_width, config.video.output_height)
        )
        self.effect_registry = self._build_effect_registry()

    def _build_effect_registry(self) -> dict[str, Effect]:
        """构建特效注册表"""

    def generate(self, sideshow: Sideshow, progress_callback=None):
        """
        生成视频

        Args:
            sideshow: 幻灯片数据
            progress_callback: 进度回调函数
        """
        with VideoWriter(**self.config.video.__dict__) as writer:
            for slide_idx, slide in enumerate(sideshow.slides):
                frames = self.renderer.render_slide(
                    slide,
                    self.config.video.fps,
                    self.effect_registry
                )

                for frame in frames:
                    writer.write_frame(frame)

                if progress_callback:
                    progress_callback(slide_idx + 1, len(sideshow.slides))
```

### 2.8 主入口 (main.py) 🆕

```python
def main():
    """主入口"""
    # 1. 加载配置
    config = Config(
        video=VideoConfig(
            fps=30,
            output_width=720,
            output_height=1280,
            output_path="output.mp4"
        ),
        timing=SlideTimingConfig()
    )

    # 2. 构建幻灯片数据
    slides = []
    for i in range(21):  # 0-20.jpg
        slide = Slide(
            start_at=i * config.timing.total_duration_ms,
            file_path=f"{i}.jpg",
            in_effect=SlideEffect(
                duration=config.timing.in_duration_ms,
                effect="fade",
                expr="in"
            ),
            hold_effect=SlideEffect(
                duration=config.timing.hold_duration_ms,
                effect="kenburns",
                expr="random"  # 随机选择8个方向
            ),
            out_effect=SlideEffect(
                duration=config.timing.out_duration_ms,
                effect="fade",
                expr="out"
            )
        )
        slides.append(slide)

    sideshow = Sideshow(slides=slides)

    # 3. 生成视频
    generator = VideoGenerator(config)

    def progress_callback(current, total):
        print(f"进度: {current}/{total} ({current/total*100:.1f}%)")

    print("开始生成视频...")
    generator.generate(sideshow, progress_callback)
    print(f"视频生成完成: {config.video.output_path}")

if __name__ == "__main__":
    main()
```

## 3. 文件结构

```
slider/
├── main.py                    # 主入口 🆕
├── config.py                  # 配置管理 🆕
├── sideshow.py                # 数据模型 ✓
├── effect.py                  # (废弃，改用effects/)
├── easing.py                  # 缓动函数库 🆕
├── renderer.py                # 渲染引擎 🆕
├── video_writer.py            # 视频输出 🆕
├── video_generator.py         # 视频生成器 🆕
├── effects/                   # 特效系统 🆕
│   ├── __init__.py
│   ├── base.py               # 基类
│   ├── transition.py         # 转场特效
│   └── kenburns.py           # Ken Burns效果
├── 0.jpg ~ 20.jpg            # 输入图片
├── .venv/                    # 虚拟环境
└── ARCHITECTURE.md           # 本文档

```

## 4. 设计原则应用

### 4.1 SOLID原则

**S - 单一职责原则**:
- 每个类职责明确单一
- `VideoWriter` 只负责ffmpeg管道
- `FrameRenderer` 只负责渲染
- `Effect` 只负责特效算法

**O - 开闭原则**:
- 新增特效只需继承 `Effect` 基类
- 无需修改现有代码

**L - 里氏替换原则**:
- 所有 `Effect` 子类可互相替换
- 统一的 `apply()` 接口

**I - 接口隔离原则**:
- `EasingFunction` 协议简洁明确
- 各模块接口最小化

**D - 依赖倒置原则**:
- 依赖抽象 `Effect` 而非具体实现
- 通过配置注入依赖

### 4.2 其他原则

**DRY - 不重复**:
- 缓动函数统一在 `easing.py`
- 特效算法统一在 `effects/`

**KISS - 简单至上**:
- 每个模块职责清晰
- 接口简洁易懂

**YAGNI - 只实现所需**:
- 仅实现需求中的特效
- 避免过度设计

## 5. 扩展性考虑

### 5.1 新增特效
```python
# 只需在 effects/transition.py 中添加新类
class MyCustomEffect(Effect):
    def apply(self, image, progress, **params):
        # 实现特效逻辑
        return processed_image
```

### 5.2 新增缓动函数
```python
# 在 easing.py 中添加
def my_easing(t: float) -> float:
    return custom_curve(t)
```

### 5.3 前端同步
- `easing.py` 中的算法可直接转换为JavaScript
- 特效参数通过JSON配置共享
- 保证视觉效果一致性

## 6. 性能考虑

### 6.1 内存优化
- 使用生成器逐帧生成，避免一次性加载所有帧
- 及时释放不用的图像数据

### 6.2 计算优化
- 图像预缩放，减少重复计算
- 使用NumPy向量化操作
- 考虑多进程并行渲染（可选）

### 6.3 I/O优化
- 使用管道避免临时文件
- 异步写入（如需要）

## 7. 实现优先级

### Phase 1: 核心框架
1. ✅ 数据模型 (sideshow.py)
2. 🔲 缓动函数 (easing.py)
3. 🔲 配置管理 (config.py)
4. 🔲 特效基类 (effects/base.py)

### Phase 2: 基础特效
1. 🔲 淡入淡出 (FadeEffect)
2. 🔲 Ken Burns (KenBurnsEffect)
3. 🔲 渲染引擎 (renderer.py)
4. 🔲 视频输出 (video_writer.py)

### Phase 3: 高级特效
1. 🔲 旋转特效 (RotateEffect)
2. 🔲 移动特效 (SlideEffect)
3. 🔲 缩放特效 (ZoomEffect)
4. 🔲 百叶窗 (BlindsEffect)
5. 🔲 推送 (PushEffect)

### Phase 4: 集成与优化
1. 🔲 视频生成器 (video_generator.py)
2. 🔲 主入口 (main.py)
3. 🔲 测试与优化

## 8. 下一步行动

建议按照以下顺序实施：

1. **实现缓动函数库** - 基础设施
2. **实现特效基类** - 建立框架
3. **实现淡入淡出** - 验证框架可行性
4. **实现渲染和输出** - 打通完整流程
5. **逐步添加更多特效** - 丰富功能
