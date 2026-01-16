# 代码简化记录

## 简化日期
2026-01-16

## 简化原因
根据用户反馈，原始设计过度复杂，不符合YAGNI原则：
1. 配置系统过于复杂 - 图片、特效、时长都由用户直接定义，不需要复杂的配置类
2. FFmpeg检查多余 - 这是服务端程序，环境已准备好
3. 图片扫描多余 - 不需要自动扫描，直接在main中写死数据

## 简化内容

### 1. config.py - 大幅简化
**简化前**: ~170行
- VideoConfig
- SlideTimingConfig  
- EffectConfig
- 各种验证和预设配置

**简化后**: 34行
- 只保留 Config 类
- 只包含 video 属性（VideoProperties）
- 保留必要的工具方法：output_size, get_frame_count

**代码减少**: ~136行（减少80%）

### 2. video_generator.py - 移除自动构建逻辑
**简化前**: ~250行
- 自动构建特效注册表
- 自动更新sideshow特效引用
- 输出信息估算
- 复杂的progress_callback

**简化后**: 63行
- 构造函数接收用户提供的effect_registry
- 简单的generate方法
- 简化的progress_callback

**代码减少**: ~187行（减少75%）

### 3. main.py - 去掉检查，直接写死数据
**简化前**: ~240行
- FFmpeg检查和版本获取
- 图片扫描和排序
- 动态创建sideshow
- 复杂的进度条和信息打印
- 各种工具函数

**简化后**: 101行
- 顶部直接定义配置常量
- 在main中写死21张图片的循环
- 直接定义特效注册表
- 简化的进度显示

**代码减少**: ~139行（减少58%）

## 总计

**总代码行数减少**: ~462行
**简化比例**: 约60%

## 简化后的使用方式

### 修改配置
直接修改 main.py 顶部：
```python
VIDEO_CONFIG = VideoProperties(
    fps=30,
    width=720,
    height=1280,
    file_path="output.mp4",
)

IN_DURATION = 500
HOLD_DURATION = 3500
OUT_DURATION = 500
```

### 修改图片数量
修改 main() 中的循环：
```python
for i in range(21):  # 修改这里
    slide = Slide(...)
```

### 自定义特效
修改 main() 中的特效注册表：
```python
effect_registry["my_effect"] = MyEffect(...)
```

## 优点

✅ **YAGNI原则** - 只保留真正需要的代码
✅ **KISS原则** - 代码更简单直接
✅ **易于修改** - 所有配置在一处
✅ **减少维护** - 更少的代码意味着更少的bug

## 保留的核心功能

所有核心功能都保留：
- ✅ 6种转场特效
- ✅ Ken Burns效果
- ✅ CSS3缓动函数
- ✅ 分辨率转换
- ✅ 逐帧生成
- ✅ FFmpeg管道输出

## 架构优势

更清晰的职责分离：
- **main.py** - 用户配置和数据定义
- **config.py** - 极简配置容器
- **video_generator.py** - 纯粹的生成逻辑
- **renderer.py** - 渲染引擎（无需修改）
- **effects/** - 特效库（无需修改）

## 总结

通过遵循YAGNI原则，代码简化了60%，同时保留了所有核心功能。
现在的设计更适合服务端程序：配置直接写在代码中，出错直接抛异常，无需友好的用户界面。
