# 系统架构设计摘要

## 核心模块

### 1. 缓动函数模块 (easing.py)
- CSS3标准缓动曲线实现
- 支持: ease, ease-in, ease-out, ease-in-out, linear
- cubic-bezier自定义函数生成器
- 与前端完全一致的算法

### 2. 特效系统 (effects/)
**基类设计** (effects/base.py):
```python
class Effect(ABC):
    def apply(self, image, progress, **params) -> np.ndarray
    def get_eased_progress(self, progress) -> float
```

**转场特效** (effects/transition.py):
- FadeEffect - 淡入淡出
- RotateEffect - 旋转
- SlideEffect - 4方向移动
- ZoomEffect - 缩放
- BlindsEffect - 百叶窗
- PushEffect - 推送

**Ken Burns** (effects/kenburns.py):
- 8方向平移: TOP, BOTTOM, LEFT, RIGHT, TOP_LEFT, TOP_RIGHT, BOTTOM_LEFT, BOTTOM_RIGHT
- 可配置缩放范围

### 3. 渲染引擎 (renderer.py)
- 加载和预处理图像
- 应用特效生成帧
- 分辨率转换 (1152x2048 → 720x1280)
- 使用生成器逐帧yield，优化内存

### 4. 视频输出 (video_writer.py)
- FFmpeg进程管道管理
- Context manager模式
- 支持自定义编码参数

### 5. 视频生成器 (video_generator.py)
- 协调所有模块
- 特效注册表管理
- 进度回调支持

### 6. 配置管理 (config.py)
- VideoConfig: FPS、分辨率、输出路径
- SlideTimingConfig: 入场/Hold/出场时长
- 统一配置入口

## 设计原则应用

### SOLID
- **S**: 每个模块单一职责
- **O**: 新增特效无需修改现有代码
- **L**: 所有Effect子类可互换
- **I**: 接口最小化
- **D**: 依赖抽象而非实现

### DRY/KISS/YAGNI
- 缓动函数统一管理，避免重复
- 接口简洁明了
- 只实现需求中的功能

## 数据流

```
图片 → 加载预处理 → 应用入场特效(0.5s) → 应用Ken Burns(3.5s) 
     → 应用出场特效(0.5s) → 逐帧生成 → FFmpeg管道 → H.264视频
```

## 扩展性

1. **新增特效**: 继承Effect基类，实现apply方法
2. **新增缓动**: 在easing.py添加函数
3. **前端同步**: 算法可直接转换为JavaScript

## 实现优先级

**Phase 1**: 核心框架 (easing.py, config.py, effects/base.py)
**Phase 2**: 基础特效 (Fade, KenBurns, renderer, video_writer)
**Phase 3**: 高级特效 (Rotate, Slide, Zoom, Blinds, Push)
**Phase 4**: 集成优化 (video_generator, main.py)

## 文件结构

```
slider/
├── main.py
├── config.py
├── sideshow.py (已实现)
├── easing.py
├── renderer.py
├── video_writer.py
├── video_generator.py
└── effects/
    ├── __init__.py
    ├── base.py
    ├── transition.py
    └── kenburns.py
```

详细设计请参考: ARCHITECTURE.md
