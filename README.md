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

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 准备配置文件
编辑 `config.yaml`（项目已包含示例配置）：

```yaml
# 视频输出配置
output:
  file_path: "output.mp4"
  fps: 30
  width: 1920
  height: 1080
  codec: "libx264"

# 幻灯片配置
slides:
  default_durations:
    in: 500      # 入场时长（毫秒）
    hold: 3500   # 保持时长
    out: 500     # 出场时长

  items:
    - image: "0.jpg"              # 支持本地路径或 URL
      in_effect:
        name: "fade"
        params: {}
      hold_effect:
        name: "pan"
        params:
          direction: "top"
      out_effect:
        name: "fade"
        params: {}

    - image: "1.jpg"
      in_effect:
        name: "circle"
        params:
          feather: 20
      hold_effect:
        name: "pan"
        params:
          direction: "center"
      out_effect:
        name: "star"
        params:
          feather: 30
```

### 3. 运行 CLI
```bash
# 使用默认配置
python main.py

# 指定配置文件
python main.py -c my_config.yaml

# 使用 CPU 后端（调试用）
python main.py --backend cpu

# 设置图片下载并发数
python main.py -j 10

# 查看所有选项
python main.py --help
```

### 4. CLI 参数说明

| 参数 | 简写 | 说明 | 默认值 |
|------|------|------|--------|
| `--config` | `-c` | 配置文件路径 | `config.yaml` |
| `--backend` | `-b` | Taichi 后端 (`gpu`/`cpu`) | `gpu` |
| `--max-concurrent` | `-j` | 图片下载最大并发数 | `5` |

---

## 📋 配置文件说明

### 完整配置示例

详见项目中的 `config.yaml` 文件，包含：
- ✅ 视频输出配置（分辨率、帧率、编码器）
- ✅ 音频配置（可选，支持 URL 或本地路径）
- ✅ 字幕配置（可选，ASS 格式）
- ✅ 幻灯片配置（图片、效果、时长）

### 图片来源

支持两种方式：
```yaml
# 本地文件
- image: "path/to/image.jpg"

# 网络 URL（自动并发下载）
- image: "https://example.com/image.jpg"
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

## 📝 完整配置示例

`config.yaml` 完整示例：

```yaml
# 视频输出配置
output:
  file_path: "output.mp4"
  fps: 30
  width: 1920
  height: 1080
  codec: "libx264"  # 或 h264_nvenc (NVIDIA GPU), h264_qsv (Intel GPU)

# 音频配置（可选）
audio:
  url: ""  # 留空则不添加音频
  # url: "https://example.com/audio.mp3"
  # url: "./audio.mp3"

# 字幕配置（可选）
subtitle:
  ass_content: ""  # 留空则不添加字幕

# 幻灯片配置
slides:
  default_durations:
    in: 500
    hold: 3500
    out: 500

  items:
    # 第1张：淡入 + 向上平移 + 淡出
    - image: "0.jpg"
      in_effect:
        name: "fade"
        params: {}
      hold_effect:
        name: "pan"
        params:
          direction: "top"
      out_effect:
        name: "fade"
        params: {}

    # 第2张：圆形擦除 + 缩放 + 五角星擦除
    - image: "1.jpg"
      in_effect:
        name: "circle"
        params:
          feather: 20
          feather_mode: "smoothstep"
      hold_effect:
        name: "pan"
        params:
          direction: "center"
          zoom_range: [1.0, 1.2]
      out_effect:
        name: "star"
        params:
          feather: 30
          feather_mode: "sigmoid"

    # 第3张：从左滑入 + 向右平移 + 旋转退出
    - image: "2.jpg"
      in_effect:
        name: "slide"
        params:
          direction: "left"
          easing: "ease-out"
      hold_effect:
        name: "pan"
        params:
          direction: "right"
          pan_intensity: 0.1
      out_effect:
        name: "rotate"
        params:
          easing: "ease-in"

    # 第4张：矩形方向擦除 + 对角平移 + 心形擦除
    - image: "3.jpg"
      in_effect:
        name: "rectangle"
        params:
          direction: "top_left"
          feather: 15
      hold_effect:
        name: "pan"
        params:
          direction: "bottom_right"
      out_effect:
        name: "heart"
        params:
          feather: 25
          center: [0.5, 0.5]

    # 支持网络图片
    - image: "https://example.com/image.jpg"
      in_effect:
        name: "zoom"
        params: {}
      hold_effect:
        name: "pan"
        params:
          direction: "center"
      out_effect:
        name: "diamond"
        params: {}
```

运行：
```bash
python main.py -c config.yaml
```

---

## ⚙️ 高级配置

### 并发下载控制

通过 `-j` 参数控制图片下载并发数：

```bash
# 默认并发 5
python main.py -c config.yaml

# 高并发（适合快速网络）
python main.py -c config.yaml -j 10

# 低并发（适合慢速网络或限流服务器）
python main.py -c config.yaml -j 3

# 串行下载（最保守）
python main.py -c config.yaml -j 1
```

### GPU 后端选择

```bash
# 使用 GPU（默认，推荐）
python main.py --backend gpu

# 使用 CPU（调试用）
python main.py --backend cpu
```

### 视频编码器

在 `config.yaml` 中配置：

```yaml
output:
  codec: "libx264"      # CPU 编码（兼容性最好）
  # codec: "h264_nvenc" # NVIDIA GPU 硬件编码（最快）
  # codec: "h264_qsv"   # Intel GPU 硬件编码
  # codec: "h264_amf"   # AMD GPU 硬件编码
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
