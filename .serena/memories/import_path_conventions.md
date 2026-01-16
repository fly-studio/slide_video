# 导入路径规范

## 项目根目录结构

```
slider/
├── main.py
├── effects/
├── render/
└── video/
```

## 正确的导入路径

### 从项目根目录导入

所有 Python 文件都应该使用从项目根目录开始的绝对导入路径：

```python
# ✅ 正确
from video.sideshow import Slide, SlideEffect, Sideshow
from video.video_generator import VideoGenerator
from video.video_writer import VideoWriter
from render.renderer import FrameRenderer
from effects import effect_registry
from effects.base import Effect, create_canvas

# ❌ 错误（旧的导入路径）
from sideshow import Slide  # 缺少 video 前缀
from video_generator import VideoGenerator  # 缺少 video 前缀
from renderer import FrameRenderer  # 缺少 render 前缀
```

## 各模块的正确导入

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
```

### effects/kenburns.py
```python
from effects.base import Effect
```

### effects/transition.py
```python
from effects.base import Effect, TransitionEffect, create_canvas, blend_images
```

## 导入路径检查命令

搜索是否有旧的导入路径：
```bash
grep -r "from sideshow import\|from video_writer import\|from renderer import" --include="*.py" .
```

## 注意事项

1. **始终使用绝对导入**: 不要使用相对导入（如 `from . import`）
2. **包前缀必须包含**: video/、render/、effects/ 等目录都必须作为包前缀
3. **跨包导入**: 任何跨包导入都要从项目根目录开始写完整路径
4. **标准库和第三方库**: 无需前缀（如 `import cv2`, `from pathlib import Path`）
