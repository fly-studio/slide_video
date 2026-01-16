# 常用命令参考

## 环境管理

### 激活虚拟环境
```bash
# Windows
.venv\Scripts\activate

# Git Bash / WSL
source .venv/Scripts/activate
```

### 包管理（使用uv）
```bash
# 安装依赖
uv pip install opencv-python numpy

# 查看已安装包
uv pip list

# 添加新依赖
uv pip install <package-name>
```

## 运行项目

### 主程序运行
```bash
python main.py
```

### Python解释器
```bash
python  # 启动Python REPL
```

## 开发工具命令（待配置）

### 代码格式化（建议配置）
```bash
# 推荐使用 ruff 或 black
ruff format .
# 或
black .
```

### 代码检查（建议配置）
```bash
# 类型检查
mypy .

# Linting
ruff check .
```

### 测试（待实现）
```bash
pytest
# 或
python -m unittest discover
```

## FFmpeg命令（核心依赖）

### 检查FFmpeg安装
```bash
ffmpeg -version
```

### 基本视频生成示例
```bash
# 从图片序列生成视频
ffmpeg -framerate 30 -i frame_%04d.png -c:v libx264 -pix_fmt yuv420p output.mp4
```

## Windows特定命令

### 文件操作
```bash
dir              # 列出目录
type <file>      # 查看文件内容
del <file>       # 删除文件
mkdir <dir>      # 创建目录
```

### 路径注意事项
- 使用正斜杠 `/` 或双反斜杠 `\\`
- 包含空格的路径用双引号包裹：`"D:/path with spaces/file.py"`
