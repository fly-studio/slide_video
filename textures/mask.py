from abc import ABC, abstractmethod
from dataclasses import dataclass

import taichi as ti

from misc.taichi import mask2d, compute_distance_field, apply_feather_linear, apply_feather_conic, \
    apply_feather_smoothstep, apply_feather_sigmoid
from misc import types

static_apply_feather = {
    types.FeatherCurve.LINEAR: apply_feather_linear,
    types.FeatherCurve.CONIC: apply_feather_conic,
    types.FeatherCurve.SMOOTHSTEP: apply_feather_smoothstep,
    types.FeatherCurve.SIGMOID: apply_feather_sigmoid,
}

# ============ 方向向量常量 ============
# 用于 compute_directional_mask 的方向参数

# 4个基本方向


# 4个对角线方向
SQRT2_INV = 0.7071067811865476  # 1/√2
static_directions = {
    types.Direction.TOP: (0.0, -1.0),      # 从上到下
    types.Direction.BOTTOM: (0.0, 1.0),    # 从下到上
    types.Direction.LEFT: (-1.0, 0.0),     # 从左到右
    types.Direction.RIGHT: (1.0, 0.0),     # 从右到左

    types.Direction.TOP_LEFT: (-SQRT2_INV, -SQRT2_INV),      # 从左上到右下
    types.Direction.TOP_RIGHT: (SQRT2_INV, -SQRT2_INV),      # 从右上到左下
    types.Direction.BOTTOM_LEFT: (-SQRT2_INV, SQRT2_INV),    # 从左下到右上
    types.Direction.BOTTOM_RIGHT: (SQRT2_INV, SQRT2_INV),    # 从右下到左上
}

static_shapes = {
    # 线性方向性（8方向）
    # use_radial=0.0 表示使用线性投影
    types.ShapeMode.LINEAR: {
        "use_radial": 0.0,
        "manhattan_weight": 0.0,
        "chebyshev_weight": 0.0
    },

    # 圆形（欧几里得距离）
    # use_radial=1.0, manhattan=0, chebyshev=0
    types.ShapeMode.CIRCLE: {
        "use_radial": 1.0,
        "manhattan_weight": 0.0,
        "chebyshev_weight": 0.0
    },

    # 菱形（曼哈顿距离）
    # use_radial=1.0, manhattan=1, chebyshev=0
    types.ShapeMode.DIAMOND: {
        "use_radial": 1.0,
        "manhattan_weight": 1.0,
        "chebyshev_weight": 0.0
    },

    # 矩形（切比雪夫距离）
    # use_radial=1.0, manhattan=0, chebyshev=1
    types.ShapeMode.RECT: {
        "use_radial": 1.0,
        "manhattan_weight": 0.0,
        "chebyshev_weight": 1.0
    }
}

@dataclass
class Mask(ABC):
    """
    遮罩类，用于在渲染时屏蔽某些区域
    """
    width: int = 0
    height: int = 0

    feather_radius: int = 0 # 羽化半径（像素）
    feather_mode: types.FeatherCurve = types.FeatherCurve.LINEAR

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


    def _apply_feather(self, curve: types.FeatherCurve = types.FeatherCurve.LINEAR):
        """
        对遮罩应用羽化效果

        :param curve: 羽化曲线类型
        :return: 羽化后的新 Mask 实例
        """

        # 创建距离场
        dist_field = ti.ndarray(dtype=ti.f32, shape=(self.width, self.height))
        compute_distance_field(self._data, dist_field)

        # 应用羽化
        static_apply_feather[curve](dist_field, self._data, float(self.feather_radius))

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
    dir_val: ti.i8
):
    for i, j in ti.ndrange(data.shape[0], data.shape[1]):
        show = False
        if (dir_val == 0):  # Direction.TOP
            show = dy[i, j] + 0.5 <= t_val
        elif (dir_val == 1):  # Direction.BOTTOM
            show = dy[i, j] + 0.5 >= (1.0 - t_val)
        elif (dir_val == 2):  # Direction.LEFT
            show = dx[i, j] + 0.5 <= t_val
        elif (dir_val == 3):  # Direction.RIGHT
            show = dx[i, j] + 0.5 >= (1.0 - t_val)

        if show:
            data[i, j] = 1.0


@ti.kernel
def compute_directional_mask(
    data: ti.types.ndarray(dtype=ti.f32),
    dx: ti.types.ndarray(dtype=ti.f32),
    dy: ti.types.ndarray(dtype=ti.f32),
    t_val: ti.f32,
    dir_x: ti.f32,
    dir_y: ti.f32,
    use_radial: ti.f32,        # 0.0=线性, 1.0=径向
    manhattan_weight: ti.f32,  # 0.0=欧几里得, 1.0=曼哈顿
    chebyshev_weight: ti.f32   # 0.0=不使用, 1.0=切比雪夫
):
    """
    通用方向性遮罩计算（完全无条件判断优化版本）
    
    参数说明：
    - dir_x, dir_y: 方向向量（use_radial=0.0 时使用）
        使用 static_directions 字典获取预定义方向
        
    - use_radial: 模式选择
        0.0 = 线性方向性（沿方向向量扩散）
        1.0 = 径向扩散（从中心向外）
        
    - manhattan_weight: 距离度量混合（use_radial=1.0 时使用）
        0.0 = 欧几里得距离（圆形）
        1.0 = 曼哈顿距离（菱形）
        
    - chebyshev_weight: 切比雪夫距离混合（use_radial=1.0 时使用）
        0.0 = 不使用切比雪夫
        1.0 = 切比雪夫距离（矩形）
    
    使用 static_shapes 字典获取预定义形状配置：
    - types.ShapeMode.LINEAR: 线性方向性（8方向）
    - types.ShapeMode.CIRCLE: 圆形扩散
    - types.ShapeMode.DIAMOND: 菱形扩散
    - types.ShapeMode.RECT: 矩形扩散
    
    实现原理：
    通过数学运算混合不同距离度量，完全避免条件判断，GPU性能最优
    """
    for i, j in ti.ndrange(data.shape[0], data.shape[1]):
        # 线性投影距离（用于方向性扩散）
        projection = dx[i, j] * dir_x + dy[i, j] * dir_y
        linear_dist = (projection + 1.0) * 0.5
        
        # 三种径向距离度量
        euclidean_dist = ti.sqrt(dx[i, j] * dx[i, j] + dy[i, j] * dy[i, j])
        manhattan_dist = ti.abs(dx[i, j]) + ti.abs(dy[i, j])
        chebyshev_dist = ti.max(ti.abs(dx[i, j]), ti.abs(dy[i, j]))
        
        # 混合径向距离（支持三种距离度量的混合）
        # 先混合欧几里得和曼哈顿
        mixed_dist = euclidean_dist * (1.0 - manhattan_weight) + manhattan_dist * manhattan_weight
        # 再混合切比雪夫
        radial_dist = mixed_dist * (1.0 - chebyshev_weight) + chebyshev_dist * chebyshev_weight
        
        # 最终距离：线性 vs 径向
        final_dist = linear_dist * (1.0 - use_radial) + radial_dist * use_radial
        
        if final_dist <= t_val:
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

        # 使用新的通用函数
        config = static_shapes[types.ShapeMode.CIRCLE]
        compute_directional_mask(
            self._data, self._dx, self._dy, self.t,
            0.0, 0.0,  # 径向模式不使用方向向量
            config["use_radial"],
            config["manhattan_weight"],
            config["chebyshev_weight"]
        )


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

        # 使用新的通用函数
        config = static_shapes[types.ShapeMode.DIAMOND]
        compute_directional_mask(
            self._data, self._dx, self._dy, self.t,
            0.0, 0.0,  # 径向模式不使用方向向量
            config["use_radial"],
            config["manhattan_weight"],
            config["chebyshev_weight"]
        )


@dataclass
class RectMask(ShapeMask):
    """
    矩形遮罩类（支持4个方向）
    """
    direction: types.Direction = types.Direction.TOP

    def _compute(self):
        """
        计算矩形遮罩数据（方向性扩散）
        
        支持8个方向：
        - 4个基本方向：TOP, BOTTOM, LEFT, RIGHT
        - 4个对角线方向：TOP_LEFT, TOP_RIGHT, BOTTOM_LEFT, BOTTOM_RIGHT

        :param t: 时间参数（0-1）
        """
        if self._dx is None or self._dy is None:
            raise ValueError("RectMask requires center coordinates (cx, cy) to be set.")

        # 使用新的通用函数
        config = static_shapes[types.ShapeMode.LINEAR]
        dir_x, dir_y = static_directions[self.direction]
        
        compute_directional_mask(
            self._data, self._dx, self._dy, self.t,
            dir_x, dir_y,
            config["use_radial"],
            config["manhattan_weight"],
            config["chebyshev_weight"]
        )


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


@dataclass
class RectExpandMask(ShapeMask):
    """
    矩形扩散遮罩类（从中心向外矩形扩散）
    
    使用切比雪夫距离（Chebyshev distance），从中心向外呈矩形边界扩散
    与 RectMask 的区别：
    - RectMask: 方向性扩散（从某个方向推进）
    - RectExpandMask: 从中心向外矩形扩散
    """
    def _compute(self):
        """
        计算矩形扩散遮罩数据

        :param t: 时间参数（0-1）
        """
        if self._dx is None or self._dy is None:
            raise ValueError("RectExpandMask requires center coordinates (cx, cy) to be set.")

        # 使用新的通用函数
        config = static_shapes[types.ShapeMode.RECT]
        compute_directional_mask(
            self._data, self._dx, self._dy, self.t,
            0.0, 0.0,  # 径向模式不使用方向向量
            config["use_radial"],
            config["manhattan_weight"],
            config["chebyshev_weight"]
        )
