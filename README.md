# Slider - 幻灯片特效视频生成器

基于 OpenCV + FFmpeg 的幻灯片视频生成工具，支持转场特效和 Ken Burns 动画效果。

## ✨ 特性

### 🎬 转场特效
- ✅ **淡入淡出** (Fade)
- ✅ **旋转** (Rotate)
- ✅ **移动** (Slide) - 4方向
- ✅ **缩放** (Zoom)
- ✅ **百叶窗** (Blinds)
- ✅ **推送** (Push)

### 🎥 Ken Burns 效果
- ✅ 8个方向的平移动画
- ✅ 可配置缩放和平移强度
- ✅ 自动随机分配方向

### ⚡ 核心功能
- ✅ CSS3标准缓动函数
- ✅ 自动分辨率转换
- ✅ 内存优化的逐帧生成

## 📋 系统要求

- Python 3.12+
- FFmpeg（在PATH中）
- opencv-python
- numpy

### 安装依赖

```bash
uv pip install opencv-python numpy
```

## 🚀 使用

### 1. 准备图片

将图片命名为 `0.jpg`, `1.jpg`, `2.jpg`, ... 放在项目目录

### 2. 配置 main.py

直接修改 `main.py` 顶部的配置：

```python
# 视频配置
VIDEO_CONFIG = VideoProperties(
    fps=30,              # 帧率
    width=720,           # 输出宽度
    height=1280,         # 输出高度
    file_path="output.mp4",  # 输出文件
)

# 时长配置（毫秒）
IN_DURATION = 500    # 入场时长
HOLD_DURATION = 3500 # Hold时长
OUT_DURATION = 500   # 出场时长
```

### 3. 修改图片数量

在 `main()` 函数中修改循环范围：

```python
# 修改 range(21) 为你的图片数量
for i in range(21):
    slide = Slide(...)
```

### 4. 运行

```bash
python main.py
```

## 🎨 自定义特效

### 修改转场特效

在 `main.py` 中修改特效注册表：

```python
# 使用旋转入场
from effects.transition import RotateEffect

effect_registry["my_rotate"] = RotateEffect(
    duration_ms=500,
    transition_type="in",
    angle_range=(0, 360)
)

# 在Slide中使用
slide.in_effect = SlideEffect(duration=500, effect="my_rotate", expr="")
```

### 修改Ken Burns参数

```python
kenburns_effects = create_kenburns_sequence(
    duration_ms=3500,
    num_slides=21,
    zoom_range=(1.0, 1.3),  # 修改缩放范围
    pan_intensity=0.15,     # 修改平移强度
    shuffle=True,
)
```

### 使用不同缓动函数

```python
effect_registry["fade_in"] = FadeEffect(
    duration_ms=500,
    direction="in",
    easing="ease-in-out"  # 修改缓动函数
)
```

可用的缓动函数：
- `"linear"` - 线性
- `"ease"` - 标准缓动
- `"ease-in"` - 缓入
- `"ease-out"` - 缓出
- `"ease-in-out"` - 缓入缓出
- `"cubic-bezier(x1,y1,x2,y2)"` - 自定义

## 📚 架构

```
slider/
├── main.py                    # 主入口（直接修改配置）
├── config.py                  # 极简配置类
├── video.py                   # 视频属性
├── sideshow.py                # 数据模型
├── easing.py                  # CSS3缓动函数
├── renderer.py                # 渲染引擎
├── video_writer.py            # FFmpeg管道
├── video_generator.py         # 视频生成器
└── effects/                   # 特效系统
    ├── base.py               # 特效基类
    ├── transition.py         # 转场特效
    └── kenburns.py           # Ken Burns
```

## 🔧 扩展特效

创建自定义特效：

```python
from effects.base import Effect
import numpy as np

class MyEffect(Effect):
    def apply(self, image, progress, canvas=None, **params):
        eased = self.get_eased_progress(progress)
        # 实现特效逻辑
        result = image * eased
        return result.astype(np.uint8)

# 在main.py中注册
effect_registry["my_effect"] = MyEffect(duration_ms=500)
```

## 📊 性能

- **21张图片** × 4.5秒 = 94.5秒视频
- **720x1280 @ 30fps** ≈ 2835帧
- **处理时间**: 取决于CPU，约实时的1-3倍

## ❓ 常见问题

**Q: 修改图片数量**
A: 修改 `main.py` 中的 `range(21)` 和 `num_slides=21`

**Q: 修改输出分辨率**
A: 修改 `VIDEO_CONFIG` 中的 `width` 和 `height`

**Q: 使用其他特效**
A: 修改 `effect_registry`，参考上面的"自定义特效"部分

**Q: FFmpeg错误**
A: 确保FFmpeg在PATH中：`ffmpeg -version`

## 📝 设计原则

- ✅ **YAGNI** - 只实现所需功能，不做过度设计
- ✅ **KISS** - 保持简单，配置直接写在代码中
- ✅ **DRY** - 避免重复，统一管理特效

---

**Happy Sliding! 🎬✨**
