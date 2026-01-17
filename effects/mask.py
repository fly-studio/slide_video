from abc import ABC, abstractmethod

import numpy as np
from PIL import Image, ImageDraw, ImageFont  # 假设你有PIL库可用，用于文字形状

from effects.base import Direction
from numba import njit, float32, prange


# ─────────────── 策略基类 ───────────────
class ShapeMaskStrategy(ABC):
    """
    形状遮罩策略基类
    每个形状实现自己的 compute 方法
    """

    @abstractmethod
    def compute(self, dx: np.ndarray, dy: np.ndarray, t: float, **kwargs) -> np.ndarray:
        """
        计算形状遮罩

        Args:
            dx, dy: 归一化坐标网格 (-0.5 ~ 0.5 或类似)
            t: 进度 [0,1]
            **kwargs: 形状特定参数（如 text= 对于 TEXT）

        Returns:
            mask: [0,1] 浮点数组
        """
        pass


# ─────────────── 各个形状策略实现 ───────────────
@njit(cache=True, fastmath=True)
def circle(dx: np.ndarray, dy: np.ndarray, t: float) -> np.ndarray:
    # 预计算半径平方（只算1次，避免重复计算）
    radius_sq = (t * np.sqrt(2.0)) ** 2
    result = np.empty(dx.shape, dtype=np.float32)
    # njit对显式循环的优化是核心（无临时数组，直接操作内存）
    for i in prange(dx.shape[0]):
        for j in range(dx.shape[1]):
            dist_sq = dx[i,j] * dx[i,j] + dy[i,j] * dy[i,j]
            result[i,j] = 1.0 if dist_sq <= radius_sq else 0.0
    return result


class CircleMask(ShapeMaskStrategy):
    """
    圆形
    """
    def compute(self, dx: np.ndarray, dy: np.ndarray, t: float, **kwargs) -> np.ndarray:
        return circle(dx, dy, t)
        radius_sq = (t * np.sqrt(2)) ** 2
        return (dx * dx + dy * dy <= radius_sq).astype(np.float32)


class DiamondMask(ShapeMaskStrategy):
    """
    菱形
    """
    def compute(self, dx: np.ndarray, dy: np.ndarray, t: float, **kwargs) -> np.ndarray:
        return (np.abs(dx) + np.abs(dy) <= t).astype(np.float32)  # 曼哈顿距离（正菱形）


class RectMask(ShapeMaskStrategy):
    """
    IN 上 -> 下
    OUT 下 -> 上
    """
    def compute(self, dx: np.ndarray, dy: np.ndarray, t: float, **kwargs) -> np.ndarray:
        if kwargs["direction"] == Direction.TOP:
            # 从上到下放大（假设中心开始，但矩形更适合线性擦除）
            return (dy + 0.5 <= t)
        elif kwargs["direction"] == Direction.BOTTOM:
            # 从下到往放大（假设中心开始，但矩形更适合线性擦除）
            return dy + 0.5 >= (1 - t)
        elif kwargs["direction"] == Direction.LEFT:
            return dx + 0.5 <= t
        else:
            return dx + 0.5 >= (1 - t)

class TriangleUpMask(ShapeMaskStrategy):
    """
    等边三角形
    """
    def compute(self, dx: np.ndarray, dy: np.ndarray, t: float, **kwargs) -> np.ndarray:
        # 等边三角形，尖端向上，从中心放大
        scaled_t = t * 1.2  # 调整覆盖
        return ((dy + 0.5) <= scaled_t) & (np.abs(dx) <= scaled_t - (dy + 0.5)).astype(np.float32)


class Star5Mask(ShapeMaskStrategy):
    """
    五角星
    """
    def compute(self, dx: np.ndarray, dy: np.ndarray, t: float, **kwargs) -> np.ndarray:
        r = np.sqrt(dx ** 2 + dy ** 2)
        theta = np.arctan2(dy, dx)
        # 五角星参数（黄金比例近似）
        inner_ratio = 0.381966  # (√5 - 1)/2 的补
        angle = 5 * theta
        star_r = t * (inner_ratio + (1 - inner_ratio) * (np.cos(angle) * 0.5 + 0.5))
        return (r <= star_r).astype(np.float32)


class HeartMask(ShapeMaskStrategy):
    """
    爱心
    """
    def compute(self, dx: np.ndarray, dy: np.ndarray, t: float, **kwargs) -> np.ndarray:
        # 心形公式（卡迪奥德变体）
        x = dx * 2.0
        y = (dy * 1.5 + 0.3)  # 偏移让心形居中
        term1 = (x ** 2 + y ** 2 - 1) ** 3
        term2 = x ** 2 * y ** 3
        heart_shape = term1 - term2 <= 0
        bounded = np.sqrt(dx ** 2 + dy ** 2) <= t * 1.3
        return (heart_shape & bounded).astype(np.float32)


class CrossMask(ShapeMaskStrategy):
    """
    十字
    """
    def compute(self, dx: np.ndarray, dy: np.ndarray, t: float, **kwargs) -> np.ndarray:
        arm_width = 0.1  # 臂宽
        scaled_t = t * 1.2
        horizontal = np.abs(dy) <= arm_width * scaled_t
        vertical = np.abs(dx) <= arm_width * scaled_t
        return ((horizontal | vertical) & (np.sqrt(dx ** 2 + dy ** 2) <= scaled_t)).astype(np.float32)


class TextMask(ShapeMaskStrategy):
    """
    自定义字
    """
    def compute(self, dx: np.ndarray, dy: np.ndarray, t: float, **kwargs) -> np.ndarray:
        """
        文字形状遮罩
        需要额外参数：text=str, font_size=float (归一化), font_path=str (可选)
        """
        text = kwargs.get('text', 'Text')  # 默认文字
        font_size = kwargs.get('font_size', 0.2)  # 归一化大小
        font_path = kwargs.get('font_path', None)  # 系统字体或路径

        h, w = dy.shape  # 从dy取形状
        # 创建PIL图像来绘制文字
        mask_img = Image.new('L', (w, h), 0)  # 黑底
        draw = ImageDraw.Draw(mask_img)

        # 加载字体
        try:
            font = ImageFont.truetype(font_path, int(font_size * min(h, w))) if font_path else ImageFont.load_default()
        except:
            font = ImageFont.load_default()

        # 计算文字边界并居中
        text_bbox = draw.textbbox((0, 0), text, font=font)
        text_w, text_h = text_bbox[2] - text_bbox[0], text_bbox[3] - text_bbox[1]
        pos_x = (w - text_w) // 2
        pos_y = (h - text_h) // 2

        # 绘制文字（白）
        draw.text((pos_x, pos_y), text, fill=255, font=font)

        # 转为numpy
        text_mask = np.array(mask_img) / 255.0  # [0,1]

        # 根据t放大（简单径向放大模拟）
        dist = np.sqrt(dx ** 2 + dy ** 2)
        scale_factor = t * 1.5  # 放大倍数
        bounded = dist <= scale_factor

        # 结合文字mask和边界
        return (text_mask * bounded).clip(0, 1)

