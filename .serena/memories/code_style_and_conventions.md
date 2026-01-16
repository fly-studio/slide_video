# 代码风格与约定

## 编程语言
- Python 3.12.11

## 代码风格

### 1. 类型注解
- 使用类型提示（Type Hints）
- 示例：`duration: int`, `file_path: str`, `slides: list[Slide]`
- 函数返回值类型：`def duration_seconds(self) -> float:`

### 2. 数据类
- 使用 `@dataclass` 装饰器定义数据模型
- 简洁清晰的字段定义

### 3. 注释语言
- **中文注释**（项目当前使用中文）
- 示例：
  ```python
  # 持续时长（ms）
  duration: int
  # 特效类型
  effect: str
  ```

### 4. 命名规范
- **类名**: PascalCase (如 `SlideEffect`, `Sideshow`)
- **方法/函数名**: snake_case (如 `duration_seconds`, `file_path`)
- **变量名**: snake_case
- **常量**: UPPER_CASE (如需要)

### 5. 代码组织
- 相关功能分模块组织
- 数据模型与业务逻辑分离
- 保持简洁（KISS原则）
- 避免代码重复（DRY原则）

## 文档字符串
- 使用中文编写docstring（保持与注释风格一致）
- 对复杂函数和类提供说明

## 时间单位约定
- 内部使用**毫秒(ms)**作为时间单位
- 提供 `duration_seconds()` 方法转换为秒
