# Slider 项目架构（最新版本）

## 目录结构

```
slider/
├── main.py                    # 主入口文件
├── effects/                   # 特效模块
│   ├── __init__.py           # 导出 effect_registry
│   ├── base.py               # 特效基类和工具函数
│   ├── easing.py             # CSS3 缓动函数
│   ├── kenburns.py           # Ken Burns 9个工厂函数
│   └── transition.py         # 转场特效（淡入淡出等）
├── render/                    # 渲染模块
│   └── renderer.py           # FrameRenderer 帧渲染器
└── video/                     # 视频相关
    ├── sideshow.py           # 数据模型（Slide, SlideEffect, Sideshow）
    ├── video_generator.py    # VideoGenerator 视频生成器
    └── video_writer.py       # VideoWriter FFmpeg 输出管道
```

## 模块导入关系

### main.py
```python
from video.sideshow import Slide, SlideEffect, Sideshow
from video.video_generator import VideoGenerator
```

### video/video_generator.py
```python
from effects import effect_registry
from render.renderer import FrameRenderer
from video.sideshow import Sideshow
from video.video_writer import VideoWriter
```

### render/renderer.py
```python
from effects.base import Effect, create_canvas
from video.sideshow import Slide, Sideshow, SlideEffect
```

### effects/__init__.py
```python
from effects.base import Effect
from effects.kenburns import effect_registry as kenburns_registry
from effects.transition import effect_registry as transition_registry

# 合并所有特效注册表
effect_registry = {}
effect_registry.update(kenburns_registry)
effect_registry.update(transition_registry)
```

## 核心组件

### 1. 数据模型 (video/sideshow.py)
- `SlideEffect`: 特效定义（duration, effect名称, extra参数）
- `Slide`: 幻灯片（file_path, in_effect, hold_effect, out_effect）
- `Sideshow`: 视频配置（fps, width, height, file_path, slides列表）

### 2. 特效系统 (effects/)
- **工厂函数模式**: 每个特效是一个工厂函数 `(duration_ms: int, extra: dict) -> Effect`
- **全局注册表**: effects/__init__.py 导出统一的 effect_registry
- **Ken Burns 9个效果**: pan_top, pan_bottom, pan_left, pan_right, pan_top_left, pan_top_right, pan_bottom_left, pan_bottom_right, zoom_center
- **转场特效**: fade_in, fade_out

### 3. 渲染引擎 (render/renderer.py)
- `FrameRenderer`: 负责加载图像、应用特效、生成帧
- `render_slide()`: 渲染单个 slide 的所有帧（in → hold → out）
- `_create_effect()`: 通过 effect_registry 调用工厂函数创建 Effect 实例

### 4. 视频生成 (video/)
- `VideoGenerator`: 协调渲染器和视频写入器
- `VideoWriter`: FFmpeg 管道，将帧写入 H.264 视频

## 数据流

```
main.py
  ↓ 创建 Slide 列表和 Sideshow
VideoGenerator(sideshow)
  ↓ 初始化 FrameRenderer
  ↓ 遍历每个 slide
FrameRenderer.render_slide(slide, effect_registry)
  ↓ 加载图像 → 预处理
  ↓ 应用 in_effect → 生成帧
  ↓ 应用 hold_effect → 生成帧
  ↓ 应用 out_effect → 生成帧
  ↓ yield 所有帧
VideoWriter.write_frame(frame)
  ↓ 通过 FFmpeg stdin 管道写入
output.mp4
```

## 关键设计模式

1. **工厂函数模式**: 特效在运行时动态创建，确保可复现性
2. **生成器模式**: 逐帧生成，内存高效
3. **管道模式**: FFmpeg 通过 stdin 接收帧数据
4. **模块化注册表**: 每个特效模块维护自己的注册表，在 __init__.py 中统一导出

## 重要约定

- 所有时长单位为毫秒 (ms)
- 图像分辨率：输入 1152x2048，输出 720x1280
- 保持宽高比并裁剪
- 特效通过字符串名称引用（如 "fade_in", "pan_top"）
- extra 参数提供可选配置（如 zoom_range, pan_intensity）
- 无 start_at 字段，幻灯片按顺序渲染
