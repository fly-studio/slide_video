from enum import Enum


class TransitionType(Enum):
    """转场枚举"""

    IN = "in"  # 入场
    OUT = "out"  # 出场
    HOLD = "hold"  # 保持

class Direction(Enum):
    """移动方向枚举"""

    TOP = "top"  # 从上往下
    BOTTOM = "bottom"  # 从下往上
    LEFT = "left"  # 从左往右
    RIGHT = "right"  # 从右往左
    
    # 对角线方向
    TOP_LEFT = "top_left"  # 从左上到右下
    TOP_RIGHT = "top_right"  # 从右上到左下
    BOTTOM_LEFT = "bottom_left"  # 从左下到右上
    BOTTOM_RIGHT = "bottom_right"  # 从右下到左上  # 从右下到左上

    CENTER = "center"

class ShapeMode(Enum):
    """形状模式枚举"""
    LINEAR = 0      # 线性方向性（8方向）
    CIRCLE = 1      # 圆形（欧几里得距离）
    DIAMOND = 2     # 菱形（曼哈顿距离）
    RECT = 3        # 矩形（切比雪夫距离）

class FeatherCurve(Enum):
    """羽化曲线类型"""
    LINEAR = 0
    CONIC = 1
    SMOOTHSTEP = 2
    SIGMOID = 3
