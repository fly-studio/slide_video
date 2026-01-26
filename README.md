# Slider - GPU-Accelerated Slideshow Video Generator

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Taichi](https://img.shields.io/badge/Taichi-GPU%20Accelerated-orange.svg)](https://www.taichi-lang.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**高性能幻灯片视频生成器，基于 Taichi GPU 加速和 OpenCV**

[功能特性](#-功能特性) • [安装](#-安装) • [快速开始](#-快速开始) • [效果列表](#-效果列表) • [性能](#-性能)

</div>

---

## ✨ 功能特性

### 🚀 GPU 加速
- **Taichi 驱动** - 利用 GPU (CUDA/Metal/Vulkan) 进行实时渲染
- **高性能** - RTX 5090 可达 30fps 11倍速处理
- **内存优化** - 流式帧生成，内存占用低

### 🎬 丰富的转场效果
- **基础转场** - Fade（淡入淡出）、Rotate（旋转）、Slide（移动）、Zoom（缩放）
- **形状擦除** - Circle（圆形）、Star（五角星）、Heart（心形）、Diamond（菱形）、Triangle（三角形）、Cross（十字）、Rectangle（矩形）
- **方向支持** - Slide 和 Rectangle 支持 4/8 方向参数

### 🎥 Ken Burns 效果
- **8方向平移** - Top, Bottom, Left, Right, Top-Left, Top-Right, Bottom-Left, Bottom-Right
- **中心缩放** - Zoom Center
- **可配置参数** - 缩放范围、平移强度

### ⚡ 其他特性
- **CSS3 缓动函数** - ease, ease-in, ease-out, ease-in-out, cubic-bezier
- **羽化效果** - Linear, Conic, Smoothstep, Sigmoid 四种羽化曲线
- **FFmpeg 集成** - 硬件加速视频编码

---

## 📋 系统要求

- **Python** 3.12+
- **FFmpeg** (必须在 PATH 中)
- **GPU** (CUDA/Metal/Vulkan) - 可选但强烈推荐

---

## 🔧 安装

### 1. 克隆仓库
```bash
git clone https://github.com/yourusername/slider.git
cd slider
```

### 2. 安装依赖
```bash
pip install -r requirements.txt
```

### 3. 验证 FFmpeg
```bash
ffmpeg -version
```

---

## 🚀 快速开始

### 1. 准备图片
将图片命名为 `0.jpg`, `1.jpg`, `2.jpg`, ... 并放在项目根目录

### 2. 编辑 main.py

```python
from video.sideshow import Slide, SlideEffect

# 时长配置（毫秒）
IN_DURATION = 500      # 入场时长
HOLD_DURATION = 3500   # 保持时长
OUT_DURATION = 500     # 出场时长

# 定义幻灯片
slides = [
    Slide(
        file_path="0.jpg",
        in_effect=SlideEffect(IN_DURATION, "fade", {}),
        hold_effect=SlideEffect(HOLD_DURATION, "pan", {"direction": "top"}),
        out_effect=SlideEffect(OUT_DURATION, "fade", {}),
    ),
    Slide(
        file_path="1.jpg",
        in_effect=SlideEffect(IN_DURATION, "circle", {"feather": 20}),
        hold_effect=SlideEffect(HOLD_DURATION, "pan", {"direction": "center"}),
        out_effect=SlideEffect(OUT_DURATION, "star", {"feather": 30}),
    ),
    # ... 更多幻灯片
]
```

### 3. 运行
```bash
python main.py
```

---

## 🎨 效果列表

### 基础转场效果

| 效果名称 | 说明 | 参数 | 示例 |
|---------|------|------|------|
| `fade` | 淡入淡出 | 无 | `SlideEffect(500, "fade", {})` |
| `rotate` | 旋转 | 无 | `SlideEffect(500, "rotate", {})` |
| `slide` | 移动 | `direction`: `"top"`, `"bottom"`, `"left"`, `"right"` | `SlideEffect(500, "slide", {"direction": "left"})` |
| `zoom` | 缩放 | 无 | `SlideEffect(500, "zoom", {})` |

### 形状擦除效果

| 效果名称 | 说明 | 参数 | 示例 |
|---------|------|------|------|
| `circle` | 圆形扩散 | `feather`: 羽化半径<br>`feather_mode`: 羽化模式 | `SlideEffect(500, "circle", {"feather": 20})` |
| `star` | 五角星扩散 | 同上 | `SlideEffect(500, "star", {"feather": 30})` |
| `heart` | 心形扩散 | 同上 | `SlideEffect(500, "heart", {})` |
| `diamond` | 菱形扩散 | 同上 | `SlideEffect(500, "diamond", {})` |
| `triangle` | 三角形扩散 | 同上 | `SlideEffect(500, "triangle", {})` |
| `cross` | 十字扩散 | 同上 | `SlideEffect(500, "cross", {})` |
| `rectangle` | 矩形扩散 | `direction`: 8个方向<br>`feather`: 羽化半径 | `SlideEffect(500, "rectangle", {"direction": "top"})` |

**Rectangle 方向参数：**
- 4个基本方向：`"top"`, `"bottom"`, `"left"`, `"right"`
- 4个对角方向：`"top_left"`, `"top_right"`, `"bottom_left"`, `"bottom_right"`

### Ken Burns 效果

| 效果名称 | 说明 | 参数 | 示例 |
|---------|------|------|------|
| `pan` | 平移/缩放 | `direction`: 9个方向<br>`zoom_range`: 缩放范围<br>`pan_intensity`: 平移强度 | `SlideEffect(3500, "pan", {"direction": "top"})` |

**Pan 方向参数：**
- 4个基本方向：`"top"`, `"bottom"`, `"left"`, `"right"`
- 4个对角方向：`"top_left"`, `"top_right"`, `"bottom_left"`, `"bottom_right"`
- 中心缩放：`"center"` (仅缩放，不平移)

---

## 🎯 参数说明

### 通用参数

```python
SlideEffect(duration, effect_name, extra_params)
```

- **duration** (int): 效果持续时间（毫秒）
- **effect_name** (str): 效果名称（见上表）
- **extra_params** (dict): 额外参数

### 额外参数 (extra_params)

| 参数名 | 类型 | 说明 | 默认值 | 适用效果 |
|--------|------|------|--------|---------|
| `easing` | str | 缓动函数 | `"ease-in-out"` | 所有 |
| `direction` | str | 方向 | - | `slide`, `rectangle`, `pan` |
| `feather` | int | 羽化半径（像素） | `0` | 形状擦除 |
| `feather_mode` | str | 羽化模式 | `"linear"` | 形状擦除 |
| `center` | tuple | 中心位置 (x, y)，范围 0-1 | `(0.5, 0.5)` | 形状擦除 |
| `zoom_range` | tuple | 缩放范围 (start, end) | `(1.0, 1.2)` | `pan` |
| `pan_intensity` | float | 平移强度 | `0.1` | `pan` |

### 缓动函数 (easing)

- `"linear"` - 线性
- `"ease"` - 标准缓动
- `"ease-in"` - 缓入
- `"ease-out"` - 缓出
- `"ease-in-out"` - 缓入缓出
- `"cubic-bezier(x1,y1,x2,y2)"` - 自定义贝塞尔曲线

### 羽化模式 (feather_mode)

- `"linear"` - 线性渐变
- `"conic"` - 二次曲线
- `"smoothstep"` - 平滑阶跃（Hermite 插值）
- `"sigmoid"` - S 曲线（Logistic 函数）

---

## 📝 完整示例

```python
from video.sideshow import Slide, SlideEffect, Sideshow
from render.video_generator import VideoGenerator

# 时长配置
IN_DURATION = 500
HOLD_DURATION = 3500
OUT_DURATION = 500

# 定义幻灯片序列
slides = [
    # 第1张：淡入 + 向上平移 + 淡出
    Slide(
        file_path="0.jpg",
        in_effect=SlideEffect(IN_DURATION, "fade", {}),
        hold_effect=SlideEffect(HOLD_DURATION, "pan", {"direction": "top"}),
        out_effect=SlideEffect(OUT_DURATION, "fade", {}),
    ),

    # 第2张：圆形擦除 + 缩放 + 五角星擦除
    Slide(
        file_path="1.jpg",
        in_effect=SlideEffect(IN_DURATION, "circle", {
            "feather": 20,
            "feather_mode": "smoothstep"
        }),
        hold_effect=SlideEffect(HOLD_DURATION, "pan", {"direction": "center"}),
        out_effect=SlideEffect(OUT_DURATION, "star", {
            "feather": 30,
            "feather_mode": "sigmoid"
        }),
    ),

    # 第3张：从左滑入 + 向右平移 + 旋转退出
    Slide(
        file_path="2.jpg",
        in_effect=SlideEffect(IN_DURATION, "slide", {
            "direction": "left",
            "easing": "ease-out"
        }),
        hold_effect=SlideEffect(HOLD_DURATION, "pan", {"direction": "right"}),
        out_effect=SlideEffect(OUT_DURATION, "rotate", {
            "easing": "ease-in"
        }),
    ),

    # 第4张：矩形方向擦除 + 对角平移 + 心形擦除
    Slide(
        file_path="3.jpg",
        in_effect=SlideEffect(IN_DURATION, "rectangle", {
            "direction": "top_left",
            "feather": 15
        }),
        hold_effect=SlideEffect(HOLD_DURATION, "pan", {"direction": "bottom_right"}),
        out_effect=SlideEffect(OUT_DURATION, "heart", {
            "feather": 25,
            "center": (0.5, 0.5)
        }),
    ),
]

# 创建幻灯片对象
sideshow = Sideshow(slides=slides)

# 生成视频
generator = VideoGenerator(sideshow)
generator.generate()
```

---

## ⚙️ 配置

### GPU 后端配置 (gpu.py)

```python
import taichi as ti

# GPU 模式（推荐）
ti.init(
    arch=ti.gpu,              # 使用 GPU (CUDA/Metal/Vulkan)
    device_memory_GB=2.0,     # GPU 内存分配
    advanced_optimization=True,
    offline_cache=True,
)

# CPU 模式（调试用）
ti.init(
    arch=ti.cpu,
    cpu_max_num_threads=16,
    debug=True,
)
```

### 视频配置 (main.py)

```python
from video.video import VideoProperties

VIDEO_CONFIG = VideoProperties(
    fps=30,                    # 帧率
    width=1920,                # 输出宽度
    height=1080,               # 输出高度
    file_path="output.mp4",    # 输出文件路径
)
```

---

## 🔬 性能

### 性能基准

| 硬件配置 | 分辨率 | 帧率 | 处理速度 |
|---------|--------|------|---------|
| RTX 5090 | 1920x1080 | 30fps | **11x 实时** |
| RTX 4090 | 1920x1080 | 30fps | ~8-9x 实时 |
| RTX 3060 | 1920x1080 | 30fps | ~3-4x 实时 |
| RTX 3060 | 720x1280 | 30fps | ~5-6x 实时 |
| M1 Pro | 1920x1080 | 30fps | ~2-3x 实时 |

### 优化建议

1. **启用 GPU** - 确保使用 `ti.gpu` 而非 `ti.cpu`
2. **调整内存** - 根据 GPU 显存调整 `device_memory_GB`
3. **降低羽化** - 减小 `feather` 参数可提升性能
4. **批量处理** - 一次性处理多个视频

---

## 📚 项目结构

```
slider/
├── main.py                    # 主入口
├── gpu.py                     # GPU 配置
├── requirements.txt           # 依赖列表
│
├── effects/                   # 效果系统
│   ├── base.py               # 基础效果类
│   ├── transition.py         # 转场效果
│   └── kenburns.py           # Ken Burns 效果
│
├── textures/                  # 纹理与遮罩
│   ├── sprite.py             # 精灵（图像）
│   ├── stage.py              # 舞台（合成）
│   └── mask.py               # 遮罩实现
│
├── render/                    # 渲染引擎
│   ├── renderer.py           # 核心渲染器
│   ├── video_generator.py    # 视频生成器
│   └── video_writer.py       # FFmpeg 集成
│
├── misc/                      # 工具模块
│   ├── easing.py             # 缓动函数
│   ├── image.py              # 图像工具
│   ├── taichi.py             # Taichi 内核
│   └── types.py              # 类型定义
│
└── video/                     # 视频模型
    ├── video.py              # 视频属性
    └── sideshow.py           # 幻灯片数据模型
```

---

## 🤝 贡献

欢迎贡献！请随时提交 Pull Request。

### 贡献方向

- [ ] 更多转场效果
- [ ] 更多形状遮罩
- [ ] 音频支持
- [ ] 实时预览
- [ ] CLI 命令行界面
- [ ] 配置文件支持

---

## 📝 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

---

## 🙏 致谢

- **Taichi** - GPU 加速计算框架
- **OpenCV** - 计算机视觉库
- **FFmpeg** - 视频编解码

---

## 📧 联系方式

- **Issues**: [GitHub Issues](https://github.com/yourusername/slider/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/slider/discussions)

---

<div align="center">

**Made with ❤️ and GPU acceleration**

[⬆ 返回顶部](#slider---gpu-accelerated-slideshow-video-generator)

</div>
