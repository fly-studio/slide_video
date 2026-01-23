from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

import taichi as ti

from misc.taichi import mask2d, compute_distance_field, apply_feather
from misc import types


class FeatherCurve(Enum):
    """羽化曲线类型"""
    LINEAR = 0
    CONIC = 1
    SMOOTHSTEP = 2
    SIGMOID = 3


@dataclass
class Mask(ABC):
    """
    遮罩类，用于在渲染时屏蔽某些区域
    """
    width: int = 0
    height: int = 0

    feather_radius: int = 0 # 羽化半径（像素）
    feather_mode: FeatherCurve = FeatherCurve.LINEAR

    _data: mask2d = None  # mask2d，值范围 0-1

    def render(self) -> mask2d:
        """
        渲染遮罩，计算并应用羽化效果

        :param t: 时间参数，用于计算动态遮罩（0-1）
        :return: 渲染后的遮罩字段
        """
        if self._data is None:
            self._data = ti.ndarray(dtype=ti.f32, shape=(self.width, self.height))

        # 清空数据
        self._data.fill(0.0)

        # 计算遮罩
        self._compute()

        # 应用羽化
        if self.feather_radius > 0:
            self._apply_feather(self.feather_mode)

        return self._data

    @abstractmethod
    def _compute(self):
        """
        计算遮罩数据
        """
        pass


    def _apply_feather(self, curve: FeatherCurve = FeatherCurve.LINEAR):
        """
        对遮罩应用羽化效果

        :param curve: 羽化曲线类型
        :return: 羽化后的新 Mask 实例
        """

        # 创建距离场
        dist_field = ti.ndarray(dtype=ti.f32, shape=(self.width, self.height))
        compute_distance_field(self._data, dist_field)

        # 应用羽化
        apply_feather(dist_field, self._data, float(self.feather_radius), curve.value)

    def enabled_alpha(self):
        return self.feather_radius > 0

    def data(self) -> mask2d:
        return self._data


# ============ Taichi Kernels（模块级别，避免重复编译）============

@ti.kernel
def compute_normalized_coords(
    dx: ti.types.ndarray(dtype=ti.f32),
    dy: ti.types.ndarray(dtype=ti.f32),
    w: ti.i32,
    h: ti.i32,
    cx_ratio: ti.f32,
    cy_ratio: ti.f32
):
    # 计算中心坐标
    cx = cx_ratio * w
    cy = cy_ratio * h

    # 计算从中心点到四个角的距离，取最大值作为归一化基准
    # 这样无论中心点在哪里，t=1 时都能覆盖整个屏幕
    dist_to_top_left = ti.sqrt(cx * cx + cy * cy)
    dist_to_top_right = ti.sqrt((w - cx) * (w - cx) + cy * cy)
    dist_to_bottom_left = ti.sqrt(cx * cx + (h - cy) * (h - cy))
    dist_to_bottom_right = ti.sqrt((w - cx) * (w - cx) + (h - cy) * (h - cy))

    max_dist = ti.max(
        ti.max(dist_to_top_left, dist_to_top_right),
        ti.max(dist_to_bottom_left, dist_to_bottom_right)
    )
    scale = ti.max(max_dist, 1.0)

    # 归一化坐标网格（从中心到最远角的距离归一化为 1.0）
    for i, j in ti.ndrange(w, h):
        dx[i, j] = (i - cx) / scale
        dy[i, j] = (j - cy) / scale


@ti.kernel
def compute_circle_mask(
    data: ti.types.ndarray(dtype=ti.f32),
    dx: ti.types.ndarray(dtype=ti.f32),
    dy: ti.types.ndarray(dtype=ti.f32),
    t_val: ti.f32
):
    # 归一化半径（从中心到角的距离已归一化为 1.0）
    # t=1 时，radius=1.0，刚好覆盖整个屏幕（屏幕内切于圆）
    radius = t_val
    radius_sq = radius * radius

    for i, j in ti.ndrange(data.shape[0], data.shape[1]):
        dist_sq = dx[i, j] * dx[i, j] + dy[i, j] * dy[i, j]
        if dist_sq <= radius_sq:
            data[i, j] = 1.0


@ti.kernel
def compute_diamond_mask(
    data: ti.types.ndarray(dtype=ti.f32),
    dx: ti.types.ndarray(dtype=ti.f32),
    dy: ti.types.ndarray(dtype=ti.f32),
    t_val: ti.f32
):
    for i, j in ti.ndrange(data.shape[0], data.shape[1]):
        manhattan_dist = ti.abs(dx[i, j]) + ti.abs(dy[i, j])
        if manhattan_dist <= t_val:
            data[i, j] = 1.0


@ti.kernel
def compute_rect_mask(
    data: ti.types.ndarray(dtype=ti.f32),
    dx: ti.types.ndarray(dtype=ti.f32),
    dy: ti.types.ndarray(dtype=ti.f32),
    t_val: ti.f32,
    dir_val: ti.i32
):
    for i, j in ti.ndrange(data.shape[0], data.shape[1]):
        show = False
        if ti.static(dir_val == 0):  # Direction.TOP
            show = dy[i, j] + 0.5 <= t_val
        elif ti.static(dir_val == 1):  # Direction.BOTTOM
            show = dy[i, j] + 0.5 >= (1.0 - t_val)
        elif ti.static(dir_val == 2):  # Direction.LEFT
            show = dx[i, j] + 0.5 <= t_val
        elif ti.static(dir_val == 3):  # Direction.RIGHT
            show = dx[i, j] + 0.5 >= (1.0 - t_val)

        if show:
            data[i, j] = 1.0


@ti.kernel
def compute_triangle_mask(
    data: ti.types.ndarray(dtype=ti.f32),
    dx: ti.types.ndarray(dtype=ti.f32),
    dy: ti.types.ndarray(dtype=ti.f32),
    t_val: ti.f32
):
    scaled_t = t_val * 1.2
    for i, j in ti.ndrange(data.shape[0], data.shape[1]):
        dy_val = dy[i, j] + 0.5
        dx_abs = ti.abs(dx[i, j])
        if dy_val <= scaled_t and dx_abs <= scaled_t - dy_val:
            data[i, j] = 1.0


@ti.kernel
def compute_star_mask(
    data: ti.types.ndarray(dtype=ti.f32),
    dx: ti.types.ndarray(dtype=ti.f32),
    dy: ti.types.ndarray(dtype=ti.f32),
    t_val: ti.f32
):
    inner_ratio = 0.381966  # (√5 - 1)/2 的补
    for i, j in ti.ndrange(data.shape[0], data.shape[1]):
        r = ti.sqrt(dx[i, j] * dx[i, j] + dy[i, j] * dy[i, j])
        theta = ti.atan2(dy[i, j], dx[i, j])
        angle = 5.0 * theta
        star_r = t_val * (inner_ratio + (1.0 - inner_ratio) * (ti.cos(angle) * 0.5 + 0.5))
        if r <= star_r:
            data[i, j] = 1.0


@ti.kernel
def compute_heart_mask(
    data: ti.types.ndarray(dtype=ti.f32),
    dx: ti.types.ndarray(dtype=ti.f32),
    dy: ti.types.ndarray(dtype=ti.f32),
    t_val: ti.f32
):
    for i, j in ti.ndrange(data.shape[0], data.shape[1]):
        x = dx[i, j] * 2.0
        y = dy[i, j] * 1.5 + 0.3
        term1 = ti.pow(x * x + y * y - 1.0, 3.0)
        term2 = x * x * y * y * y
        heart_shape = term1 - term2 <= 0.0

        r = ti.sqrt(dx[i, j] * dx[i, j] + dy[i, j] * dy[i, j])
        bounded = r <= t_val * 1.3

        if heart_shape and bounded:
            data[i, j] = 1.0


@ti.kernel
def compute_cross_mask(
    data: ti.types.ndarray(dtype=ti.f32),
    dx: ti.types.ndarray(dtype=ti.f32),
    dy: ti.types.ndarray(dtype=ti.f32),
    t_val: ti.f32
):
    arm_width = 0.1
    scaled_t = t_val * 1.2
    for i, j in ti.ndrange(data.shape[0], data.shape[1]):
        horizontal = ti.abs(dy[i, j]) <= arm_width * scaled_t
        vertical = ti.abs(dx[i, j]) <= arm_width * scaled_t
        r = ti.sqrt(dx[i, j] * dx[i, j] + dy[i, j] * dy[i, j])
        bounded = r <= scaled_t

        if (horizontal or vertical) and bounded:
            data[i, j] = 1.0


# ============ Mask Classes ============

@dataclass
class ShapeMask(Mask):
    t: float = 0  # 0-1，形状大小的百分比
    cx: float = None  # 0-1，表示相对于width的中心 x 坐标的比例
    cy: float = None  # 0-1，表示相对于height的中心 y 坐标的比例

    _dx: mask2d = None  # 归一化 x 坐标网格，无中心时为 None
    _dy: mask2d = None  # 归一化 y 坐标网格，无中心时为 None

    def __post_init__(self):
        if self.cx is not None and self.cy is not None:
            self._calc_center_coordinate()

    def _calc_center_coordinate(self):
        """
        填充中心区域到遮罩，创建归一化坐标网格
        """
        # 创建归一化坐标网格
        self._dx = ti.ndarray(dtype=ti.f32, shape=(self.width, self.height))
        self._dy = ti.ndarray(dtype=ti.f32, shape=(self.width, self.height))

        compute_normalized_coords(
            self._dx, self._dy,
            self.width, self.height,
            self.cx, self.cy
        )


@dataclass
class CircleMask(ShapeMask):
    """
    圆形遮罩类
    """
    def _compute(self):
        """
        计算圆形遮罩数据

        :param t: 时间参数（0-1），t=1时圆形覆盖整个对角线
        """
        if self._dx is None or self._dy is None:
            raise ValueError("CircleMask requires center coordinates (cx, cy) to be set.")

        compute_circle_mask(self._data, self._dx, self._dy, self.t)


@dataclass
class DiamondMask(ShapeMask):
    """
    菱形遮罩类（曼哈顿距离）
    """
    def _compute(self):
        """
        计算菱形遮罩数据

        :param t: 时间参数（0-1）
        """
        if self._dx is None or self._dy is None:
            raise ValueError("DiamondMask requires center coordinates (cx, cy) to be set.")

        compute_diamond_mask(self._data, self._dx, self._dy, self.t)


@dataclass
class RectMask(ShapeMask):
    """
    矩形遮罩类（支持4个方向）
    """
    direction: types.Direction = types.Direction.TOP

    def _compute(self):
        """
        计算矩形遮罩数据

        :param t: 时间参数（0-1）
        """
        if self._dx is None or self._dy is None:
            raise ValueError("RectMask requires center coordinates (cx, cy) to be set.")

        direction_value = self.direction.value
        compute_rect_mask(self._data, self._dx, self._dy, self.t, direction_value)


class TriangleUpMask(ShapeMask):
    """
    等边三角形遮罩类（尖端向上）
    """
    def _compute(self):
        """
        计算三角形遮罩数据

        :param t: 时间参数（0-1）
        """
        if self._dx is None or self._dy is None:
            raise ValueError("TriangleUpMask requires center coordinates (cx, cy) to be set.")

        compute_triangle_mask(self._data, self._dx, self._dy, self.t)


@dataclass
class Star5Mask(ShapeMask):
    """
    五角星遮罩类
    """
    def _compute(self):
        """
        计算五角星遮罩数据

        :param t: 时间参数（0-1）
        """
        if self._dx is None or self._dy is None:
            raise ValueError("Star5Mask requires center coordinates (cx, cy) to be set.")

        compute_star_mask(self._data, self._dx, self._dy, self.t)


@dataclass
class HeartMask(ShapeMask):
    """
    爱心遮罩类
    """
    def _compute(self):
        """
        计算爱心遮罩数据

        :param t: 时间参数（0-1）
        """
        if self._dx is None or self._dy is None:
            raise ValueError("HeartMask requires center coordinates (cx, cy) to be set.")

        compute_heart_mask(self._data, self._dx, self._dy, self.t)


@dataclass
class CrossMask(ShapeMask):
    """
    十字遮罩类
    """
    def _compute(self):
        """
        计算十字遮罩数据

        :param t: 时间参数（0-1）
        """
        if self._dx is None or self._dy is None:
            raise ValueError("CrossMask requires center coordinates (cx, cy) to be set.")

        compute_cross_mask(self._data, self._dx, self._dy, self.t)
