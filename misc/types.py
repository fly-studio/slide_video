from enum import Enum


class TransitionType(Enum):
    """转场枚举"""

    IN = "in"  # 入场
    OUT = "out"  # 出场

class Direction(Enum):
    """移动方向枚举"""

    TOP = "top"  # 从上往下
    BOTTOM = "bottom"  # 从下往上
    LEFT = "left"  # 从左往右
    RIGHT = "right"  # 从右往左
