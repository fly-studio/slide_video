# Slider - 内部开发文档

> 本文档面向项目开发者，包含架构设计、实现细节、开发指南等内容

**最后更新**: 2026-01-26

---

## 📋 目录

- [项目概述](#项目概述)
- [架构设计](#架构设计)
- [核心概念](#核心概念)
- [技术栈](#技术栈)
- [开发指南](#开发指南)
- [性能优化](#性能优化)
- [设计原则](#设计原则)
- [常见问题](#常见问题)

---

## 项目概述

### 设计目标

1. **高性能** - 利用 GPU 加速实现实时渲染
2. **易用性** - 简单的 API，通过 `SlideEffect` 统一接口
3. **可扩展** - 易于添加新效果和新遮罩
4. **内存优化** - 流式生成，避免一次性加载所有帧

### 核心特性

- **GPU 加速渲染** - Taichi 驱动的 GPU 内核
- **效果系统** - 转场效果、Ken Burns 效果
- **遮罩系统** - 多种形状遮罩，支持羽化
- **FFmpeg 集成** - 硬件加速视频编码

---

## 架构设计

### 整体架构

```
┌─────────────────────────────────────────────────────────┐
│                        main.py                          │
│                    (用户入口)                            │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│                   video/sideshow.py                     │
│              (Slide, SlideEffect, Sideshow)             │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│              render/video_generator.py                  │
│                  (视频生成器)                            │
└────────┬────────────────────────────┬───────────────────┘
         │                            │
         ▼                            ▼
┌──────────────────┐        ┌──────────────────┐
│ render/renderer  │        │ render/video_    │
│     .py          │        │   writer.py      │
│  (帧渲染器)      │        │ (FFmpeg 管道)    │
└────────┬─────────┘        └──────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│                   textures/stage.py                     │
│                  (舞台 - 合成层)                         │
└────────┬────────────────────────────┬───────────────────┘
         │                            │
         ▼                            ▼
┌──────────────────┐        ┌──────────────────┐
│ textures/sprite  │        │ textures/mask    │
│     .py          │        │     .py          │
│  (精灵 - 图像)   │        │  (遮罩系统)      │
└──────────────────┘        └──────────────────┘
         │                            │
         └────────────┬───────────────┘
                      ▼
         ┌─────────────────────────┐
         │    misc/taichi.py       │
         │   (Taichi GPU 内核)     │
         └─────────────────────────┘
```

### 模块职责

#### 0. `main.py` - CLI 入口层
- **ConfigLoader**: YAML 配置文件加载和验证
- **ImageDownloader**: 异步并发图片下载（httpx + Semaphore）
- **SliderCLI**: CLI 主流程控制，参数解析

#### 1. `video/` - 数据模型层
- **sideshow.py**: 定义 `Slide`, `SlideEffect`, `Sideshow` 数据结构
- **video.py**: 视频属性配置 (`VideoProperties`)

#### 2. `render/` - 渲染层
- **video_generator.py**: 视频生成主流程，协调各模块
- **renderer.py**: 单帧渲染逻辑
- **video_writer.py**: FFmpeg 管道封装

#### 3. `textures/` - 纹理与合成层
- **stage.py**: 舞台（Stage），负责图层合成
- **sprite.py**: 精灵（Sprite），表示单个图像及其变换
- **mask.py**: 遮罩系统，各种形状遮罩的实现

#### 4. `effects/` - 效果系统
- **base.py**: 效果基类 (`Effect`, `TransitionEffect`)
- **transition.py**: 转场效果实现和注册表
- **kenburns.py**: Ken Burns 效果实现

#### 5. `misc/` - 工具模块
- **taichi.py**: Taichi GPU 内核（采样、混合、遮罩计算等）
- **easing.py**: CSS3 缓动函数实现
- **image.py**: 图像加载和预处理
- **types.py**: 类型定义和枚举

#### 6. `config.yaml` - 配置文件
- 视频输出配置（分辨率、帧率、编码器）
- 音频和字幕配置（可选）
- 幻灯片配置（图片、效果、时长）

---

## 核心概念

### 1. Sprite（精灵）

**定义**: 表示一个图像及其变换属性

**核心属性**:
```python
class Sprite:
    image: np.ndarray      # 原始图像数据
    width: int             # 宽度
    height: int            # 高度
    x: int                 # X 偏移
    y: int                 # Y 偏移
    rotation: float        # 旋转角度（弧度）
    scale: float           # 缩放比例
    alpha: float           # 透明度 (0-1)
    mask: Mask | None      # 遮罩对象
```

**设计思路**:
- Sprite 只负责存储状态，不负责渲染
- 变换属性由 Effect 修改
- 渲染由 Stage 统一处理

### 2. Stage（舞台）

**定义**: 负责将 Sprite 合成到画布上

**核心方法**:
```python
def composite(self, sprite: Sprite, canvas: np.ndarray) -> np.ndarray:
    """将 Sprite 合成到 canvas 上"""
    # 1. 应用变换（旋转、缩放、平移）
    # 2. 应用遮罩
    # 3. 应用透明度
    # 4. 混合到 canvas
```

**GPU 加速**:
- 使用 Taichi 内核进行像素级并行计算
- 支持双线性插值、Lanczos 采样
- 遮罩计算完全在 GPU 上

### 3. Mask（遮罩）

**定义**: 控制 Sprite 的可见区域

**类型**:
- **ShapeMask**: 形状遮罩基类（Circle, Star, Heart 等）
- **DirectionalMask**: 方向性遮罩（Rectangle 的 8 方向）

**核心属性**:
```python
class ShapeMask:
    width: int                      # 遮罩宽度
    height: int                     # 遮罩高度
    cx: float                       # 中心 X (0-1)
    cy: float                       # 中心 Y (0-1)
    t: float                        # 进度 (0-1)
    feather_radius: int             # 羽化半径
    feather_mode: FeatherCurve      # 羽化曲线
    _data: ti.ndarray               # GPU 数据
```

**渲染流程**:
1. `_compute()` - 计算遮罩形状（GPU 内核）
2. `_apply_feather()` - 应用羽化效果（GPU 内核）
3. 返回 `_data` 供 Stage 使用

**关键设计**:
- 遮罩数据存储在 GPU 上（`ti.ndarray`）
- 使用归一化坐标系（`dx`, `dy`）
- 支持任意中心点和缩放

### 4. Effect（效果）

**定义**: 修改 Sprite 属性以实现动画效果

**类型**:
- **TransitionEffect**: 转场效果（Fade, Rotate, Slide, Zoom, Wipe）
- **KenBurnsEffect**: Ken Burns 效果（Pan, Zoom）

**核心方法**:
```python
def apply(self, sprite: Sprite, progress: float):
    """
    应用效果到 Sprite

    Args:
        sprite: 目标精灵
        progress: 进度 (0-1)
    """
    eased = self.get_eased_progress(progress)
    # 修改 sprite 的属性
    sprite.alpha = eased
    sprite.scale = 1.0 + eased * 0.3
    # ...
```

**设计原则**:
- Effect 只修改 Sprite 属性，不直接渲染
- 支持缓动函数（easing）
- 可组合（一个 Sprite 可以应用多个 Effect）

---

## 技术栈

### Taichi GPU 编程

#### 为什么选择 Taichi？

1. **跨平台 GPU 支持** - CUDA, Metal, Vulkan 统一接口
2. **Python 友好** - 使用 Python 语法编写 GPU 内核
3. **高性能** - 接近手写 CUDA 的性能
4. **易于调试** - 支持 CPU 后端调试

#### Taichi 内核示例

```python
@ti.kernel
def compute_circle_mask(
    data: ti.types.ndarray(dtype=ti.f32),
    dx: ti.types.ndarray(dtype=ti.f32),
    dy: ti.types.ndarray(dtype=ti.f32),
    t_val: ti.f32
):
    """圆形遮罩计算（GPU 并行）"""
    radius = t_val
    radius_sq = radius * radius

    for i, j in ti.ndrange(data.shape[0], data.shape[1]):
        dist_sq = dx[i, j] * dx[i, j] + dy[i, j] * dy[i, j]
        if dist_sq <= radius_sq:
            data[i, j] = 1.0
```

**关键点**:
- `@ti.kernel` 装饰器标记 GPU 内核
- `ti.ndarray` 用于 GPU 数组
- `ti.ndrange` 实现并行循环
- 避免条件分支以提高性能

#### 性能优化技巧

1. **避免条件判断** - 使用数学运算代替 if-else
   ```python
   # 不好
   if condition:
       result = a
   else:
       result = b

   # 好
   result = a * condition + b * (1.0 - condition)
   ```

2. **使用局部变量** - 减少内存访问
   ```python
   # 不好
   for i, j in ti.ndrange(w, h):
       data[i, j] = dx[i, j] * dx[i, j] + dy[i, j] * dy[i, j]

   # 好
   for i, j in ti.ndrange(w, h):
       x = dx[i, j]
       y = dy[i, j]
       data[i, j] = x * x + y * y
   ```

3. **预计算常量** - 在循环外计算
   ```python
   @ti.kernel
   def compute(data: ti.types.ndarray(), t: ti.f32):
       # 预计算
       radius = t * 2.7
       radius_sq = radius * radius

       for i, j in ti.ndrange(data.shape[0], data.shape[1]):
           # 使用预计算的值
           if dist_sq <= radius_sq:
               data[i, j] = 1.0
   ```

### OpenCV 图像处理

**用途**:
- 图像加载和解码
- 颜色空间转换（BGR ↔ RGB）
- 图像缩放和裁剪

**注意事项**:
- OpenCV 使用 BGR 格式，需要转换为 RGB
- 图像数据类型为 `uint8`，计算时需要转换为 `float32`

### httpx 异步 HTTP 客户端

**用途**:
- 异步并发下载网络图片
- 支持 HTTP/2 和连接池
- 超时控制和错误处理

**并发控制**:
```python
class ImageDownloader:
    def __init__(self, temp_dir: Path, max_concurrent: int = 5):
        self.semaphore = asyncio.Semaphore(max_concurrent)

    async def download_image(self, url: str, client: httpx.AsyncClient):
        async with self.semaphore:  # 限制并发数
            response = await client.get(url, timeout=30.0)
            # 处理响应
```

**优势**:
- 使用 `asyncio.Semaphore` 控制并发数
- 避免同时打开过多连接
- 对服务器友好，防止被限流

### PyYAML 配置解析

**用途**:
- 解析 YAML 配置文件
- 支持复杂数据结构
- 易于人工编辑

**示例**:
```python
import yaml

with open("config.yaml", "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)
```

### FFmpeg 视频编码

**集成方式**: 通过管道（pipe）传输帧数据

```python
ffmpeg_cmd = [
    'ffmpeg',
    '-y',                          # 覆盖输出文件
    '-f', 'rawvideo',              # 输入格式
    '-vcodec', 'rawvideo',
    '-s', f'{width}x{height}',     # 分辨率
    '-pix_fmt', 'rgb24',           # 像素格式
    '-r', str(fps),                # 帧率
    '-i', '-',                     # 从 stdin 读取
    '-c:v', 'libx264',             # 编码器
    '-preset', 'medium',           # 编码预设
    '-crf', '23',                  # 质量
    output_path
]
```

**优势**:
- 无需保存中间帧到磁盘
- 支持硬件加速编码
- 内存占用低

---

## 开发指南

### 添加新的转场效果

#### 1. 创建效果类

在 `effects/transition.py` 中：

```python
class MyNewEffect(TransitionEffect):
    """我的新效果"""

    def __init__(
        self,
        duration_ms: int,
        transition_type: types.TransitionType = types.TransitionType.IN,
        easing: str = "ease-in-out",
        # 添加自定义参数
        my_param: float = 1.0,
    ):
        super().__init__(duration_ms, transition_type, easing)
        self.my_param = my_param

    def apply(self, sprite, progress: float):
        """应用效果"""
        eased = self.get_eased_progress(progress)

        # 根据 transition_type 调整进度
        if self.transition_type == types.TransitionType.OUT:
            eased = 1.0 - eased

        # 修改 sprite 属性
        sprite.alpha = eased
        sprite.scale = 1.0 + eased * self.my_param

        return None  # 不使用遮罩
```

#### 2. 注册效果

在 `effect_registry` 中注册：

```python
effect_registry = {
    # ... 现有效果
    "my_new_effect": transition_effect(MyNewEffect),
}
```

#### 3. 使用效果

在 `main.py` 中：

```python
Slide(
    file_path="0.jpg",
    in_effect=SlideEffect(500, "my_new_effect", {}),
    # ...
)
```

### 添加新的遮罩形状

#### 1. 创建 Taichi 内核

在 `textures/mask.py` 中：

```python
@ti.kernel
def compute_my_shape_mask(
    data: ti.types.ndarray(dtype=ti.f32),
    dx: ti.types.ndarray(dtype=ti.f32),
    dy: ti.types.ndarray(dtype=ti.f32),
    t_val: ti.f32
):
    """我的形状遮罩计算"""
    scaled_t = t_val * 1.5  # 缩放因子

    for i, j in ti.ndrange(data.shape[0], data.shape[1]):
        x = dx[i, j]
        y = dy[i, j]

        # 实现形状判断逻辑
        # 例如：椭圆
        if (x*x)/(scaled_t*scaled_t) + (y*y)/(scaled_t*0.5*scaled_t*0.5) <= 1.0:
            data[i, j] = 1.0
```

#### 2. 创建遮罩类

```python
@dataclass
class MyShapeMask(ShapeMask):
    """我的形状遮罩"""

    def _compute(self):
        """计算遮罩"""
        if self._dx is None or self._dy is None:
            raise ValueError("MyShapeMask requires center coordinates")

        compute_my_shape_mask(self._data, self._dx, self._dy, self.t)
```

#### 3. 注册遮罩

在 `effects/transition.py` 的 `effect_registry` 中：

```python
effect_registry = {
    # ... 现有效果
    "my_shape": wipe_effect(mask.MyShapeMask),
}
```

### 添加新的 Ken Burns 方向

在 `effects/kenburns.py` 中：

```python
def _calculate_pan(self, w: int, h: int, progress: float) -> tuple[int, int]:
    """计算平移量"""
    pan_amount = self.pan_intensity

    if self.direction == types.Direction.MY_NEW_DIRECTION:
        # 实现新方向的平移逻辑
        pan_x = int(w * pan_amount * progress)
        pan_y = int(h * pan_amount * progress * 0.5)
        return pan_x, pan_y

    # ... 其他方向
```

---

## 性能优化

### GPU 内存管理

**原则**:
1. **复用数组** - 避免频繁创建和销毁 `ti.ndarray`
2. **延迟初始化** - 只在需要时创建 GPU 数组
3. **及时释放** - 不再使用的数组应该释放

**示例**:
```python
class Mask:
    _data: ti.ndarray = None

    def render(self):
        # 延迟初始化
        if self._data is None:
            self._data = ti.ndarray(dtype=ti.f32, shape=(self.width, self.height))

        # 清空并重新计算
        self._data.fill(0.0)
        self._compute()

        return self._data
```

### 渲染优化

**瓶颈分析**:
1. **图像采样** - 使用 Lanczos 或双线性插值
2. **遮罩计算** - 复杂形状（如五角星）使用射线法
3. **羽化计算** - 距离场计算 + 羽化曲线

**优化策略**:
1. **减少羽化半径** - 羽化半径越大，计算量越大
2. **使用简单形状** - Circle 比 Star 快
3. **降低分辨率** - 测试时使用较低分辨率

### 内存优化

**流式生成**:
```python
def generate_frames():
    """逐帧生成，避免一次性加载所有帧"""
    for frame_idx in range(total_frames):
        frame = render_frame(frame_idx)
        yield frame  # 生成器，节省内存
```

**图像缓存**:
```python
class ImageCache:
    """图像缓存，避免重复加载"""
    _cache: dict[str, np.ndarray] = {}

    def load(self, path: str) -> np.ndarray:
        if path not in self._cache:
            self._cache[path] = cv2.imread(path)
        return self._cache[path]
```

---

## 设计原则

### SOLID 原则应用

#### 1. 单一职责原则 (SRP)
- **Sprite**: 只负责存储图像和变换属性
- **Stage**: 只负责合成
- **Effect**: 只负责修改 Sprite 属性
- **Mask**: 只负责计算遮罩数据

#### 2. 开闭原则 (OCP)
- 通过继承 `Effect` 添加新效果，无需修改现有代码
- 通过继承 `ShapeMask` 添加新遮罩，无需修改现有代码

#### 3. 里氏替换原则 (LSP)
- 所有 `TransitionEffect` 子类可以互换使用
- 所有 `ShapeMask` 子类可以互换使用

#### 4. 接口隔离原则 (ISP)
- `Effect.apply()` 接口简单明确
- `Mask.render()` 接口独立

#### 5. 依赖倒置原则 (DIP)
- `Stage` 依赖 `Sprite` 和 `Mask` 抽象，而非具体实现
- `VideoGenerator` 依赖 `Effect` 抽象

### KISS 原则

**保持简单**:
- API 设计简单：`SlideEffect(duration, effect_name, params)`
- 配置直接写在代码中，无需复杂的配置文件
- 效果注册表使用简单的字典

### DRY 原则

**避免重复**:
- 缓动函数统一在 `misc/easing.py`
- GPU 内核统一在 `misc/taichi.py`
- 效果工厂函数 `transition_effect()` 和 `wipe_effect()`

### YAGNI 原则

**只实现需要的功能**:
- 不支持音频（暂时不需要）
- 不支持实时预览（暂时不需要）
- 不支持配置文件（直接修改代码更简单）

---

## 常见问题

### Q: 如何调试 Taichi 内核？

**A**: 使用 CPU 后端

```python
# 在 gpu.py 中
ti.init(
    arch=ti.cpu,  # 使用 CPU 后端
    debug=True,   # 启用调试
    log_level=ti.TRACE,
)
```

然后可以在内核中使用 `print()`:

```python
@ti.kernel
def my_kernel(data: ti.types.ndarray()):
    for i, j in ti.ndrange(data.shape[0], data.shape[1]):
        print(f"i={i}, j={j}, value={data[i, j]}")  # 调试输出
```

### Q: 为什么五角星边缘是直线而不是弧线？

**A**: 使用射线法（Ray Casting）判断点是否在多边形内

五角星是一个 10 边形（5 个外顶点 + 5 个内顶点），使用射线法：
1. 从点向右发出射线
2. 计算射线与 10 条边的交点数
3. 交点数为奇数 → 点在多边形内

这样可以保证边缘是直线。

### Q: 如何让形状在 t=1.0 时完全覆盖屏幕？

**A**: 调整缩放因子

对于不同形状，需要不同的缩放因子：
- **Circle**: `t * 1.0` （欧几里得距离）
- **Diamond**: `t * 1.414` （曼哈顿距离，需要 √2 倍）
- **Star**: `t * 2.7` （内半径需要 >= 1.0）
- **Triangle**: `t * 2.5` （三角形的内切圆半径较小）

### Q: 羽化效果如何实现？

**A**: 距离场 + 羽化曲线

1. **计算距离场**: 对于遮罩边界的每个像素，计算到最近边界的距离
2. **应用羽化曲线**: 根据距离和羽化半径，使用羽化曲线（Linear, Conic, Smoothstep, Sigmoid）计算透明度

```python
def apply_feather_smoothstep(dist_field, mask, feather_radius):
    """Smoothstep 羽化"""
    for i, j in ti.ndrange(mask.shape[0], mask.shape[1]):
        d = dist_field[i, j]
        if d < feather_radius:
            t = d / feather_radius
            # Smoothstep: 3t² - 2t³
            alpha = 3.0 * t * t - 2.0 * t * t * t
            mask[i, j] *= alpha
```

### Q: 如何优化大分辨率视频的性能？

**A**: 多方面优化

1. **GPU 内存**: 增加 `device_memory_GB`
2. **降低羽化**: 减小 `feather_radius`
3. **简化效果**: 使用简单形状（Circle 而非 Star）
4. **批量处理**: 一次性处理多个视频
5. **硬件编码**: 使用 FFmpeg 硬件加速（`-c:v h264_nvenc`）

### Q: 为什么不使用配置文件？

**A**: KISS 原则

对于这个项目：
- 配置项不多（时长、分辨率、效果）
- 直接修改代码更直观
- 避免引入配置文件解析的复杂性
- 更容易版本控制和代码审查

如果未来需要支持大量配置，可以考虑添加配置文件支持。

---

## 开发路线图

### 短期目标

- [ ] 添加更多形状遮罩（六边形、八边形）
- [ ] 优化五角星渲染性能
- [ ] 添加更多缓动函数
- [ ] 改进错误处理和日志

### 中期目标

- [ ] 音频支持
- [ ] 实时预览
- [ ] CLI 命令行界面
- [ ] 配置文件支持

### 长期目标

- [ ] 插件系统
- [ ] Web UI
- [ ] 分布式渲染
- [ ] 云端处理

---

## 贡献指南

### 代码风格

- 遵循 PEP 8
- 使用类型注解
- 添加文档字符串
- 保持函数简短（< 50 行）

### 提交规范

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Type**:
- `feat`: 新功能
- `fix`: 修复 bug
- `docs`: 文档更新
- `style`: 代码格式
- `refactor`: 重构
- `perf`: 性能优化
- `test`: 测试

**示例**:
```
feat(mask): add hexagon mask

- Implement hexagon shape using 6-sided polygon
- Add GPU kernel for hexagon computation
- Register in effect_registry

Closes #123
```

### 测试

添加新功能时，请添加相应的测试：

```python
# test_my_feature.py
def test_my_new_effect():
    effect = MyNewEffect(duration_ms=500)
    sprite = Sprite(...)

    effect.apply(sprite, progress=0.5)

    assert sprite.alpha == 0.5
    assert sprite.scale == 1.15
```

---

## 参考资料

### Taichi 文档
- [Taichi 官方文档](https://docs.taichi-lang.org/)
- [Taichi GPU 编程指南](https://docs.taichi-lang.org/docs/gpu_programming)

### 图形学资源
- [Signed Distance Functions](https://iquilezles.org/articles/distfunctions2d/)
- [Easing Functions](https://easings.net/)
- [Ken Burns Effect](https://en.wikipedia.org/wiki/Ken_Burns_effect)

### FFmpeg 文档
- [FFmpeg 官方文档](https://ffmpeg.org/documentation.html)
- [FFmpeg 硬件加速](https://trac.ffmpeg.org/wiki/HWAccelIntro)

---

**最后更新**: 2026-01-26
**维护者**: Slider Team
