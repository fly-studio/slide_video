from abc import ABC, abstractclassmethod, abstractmethod
from dataclasses import dataclass
from enum import Enum

import taichi as ti
import numpy as np

from misc.taichi import mask2d, compute_distance_field, apply_feather


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
    cx: float = None # 0-1，表示相对于width的中心 x 坐标的比例
    cy: float = None # 0-1，表示相对于height的中心 y 坐标的比例
    feather_radius: int = 0 # 羽化半径（像素）
    feather_mode: FeatherCurve = FeatherCurve.LINEAR

    _data: mask2d.field = None  # mask2d.field，值范围 0-1
    _dx: mask2d.field = None  # 归一化 x 坐标网格，无中心时为 None
    _dy: mask2d.field = None  # 归一化 y 坐标网格，无中心时为 None

    def __post_init__(self):
        """
        创建一个新的遮罩
        """
        if self._data is None:
            self._data = mask2d.field(shape=(self.width, self.height))
        if self.cx is not None and self.cy is not None:
            self._calc_center_coordinate()


    def _calc_center_coordinate(self):
        """
        填充中心区域到遮罩，创建归一化坐标网格
        """
        # 创建归一化坐标网格
        self._dx = mask2d.field(shape=(self.width, self.height))
        self._dy = mask2d.field(shape=(self.width, self.height))

        @ti.kernel
        def compute_normalized_coords(
            dx: ti.template(),
            dy: ti.template(),
            w: ti.i32,
            h: ti.i32,
            cx_ratio: ti.f32,
            cy_ratio: ti.f32
        ):
            # 计算中心坐标
            cx = cx_ratio * w
            cy = cy_ratio * h
            scale = ti.cast(ti.min(w, h), ti.f32)

            # 归一化坐标网格（-0.5 ~ 0.5）
            for i, j in ti.ndrange(w, h):
                dx[i, j] = (i - cx) / ti.max(scale, 1.0)
                dy[i, j] = (j - cy) / ti.max(scale, 1.0)

        compute_normalized_coords(
            self._dx, self._dy,
            self.width, self.height,
            self.cx, self.cy
        )

    def render(self, t: float = 1) -> mask2d.field:
        """
        渲染遮罩，计算并应用羽化效果

        :param t: 时间参数，用于计算动态遮罩（0-）
        :return: 渲染后的遮罩字段
        """
        # 清空数据
        self._data.fill(0.0)

        # 计算遮罩
        self._compute(t)

        # 应用羽化
        if self.feather_radius > 0:
            self._apply_feather(self.feather_mode)

        return self._data

    @abstractmethod
    def _compute(self, t: float):
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
        dist_field = mask2d.field(shape=(self.width, self.height))
        compute_distance_field(self._data, dist_field)

        # 应用羽化
        apply_feather(dist_field, self._data, float(self.feather_radius), curve.value)

    def enabled_alpha(self):
        return self.feather_radius > 0


class CircleMask(Mask):
    """
    圆形遮罩类
    """
    def _compute(self, t: float):
        """
        计算圆形遮罩数据

        :param t: 时间参数（0-1），t=1时圆形覆盖整个对角线
        """
        if self._dx is None or self._dy is None:
            raise ValueError("CircleMask requires center coordinates (cx, cy) to be set.")

        @ti.kernel
        def compute_circle_mask(
            data: ti.template(),
            dx: ti.template(),
            dy: ti.template(),
            t_val: ti.f32
        ):
            # 归一化半径（dx/dy已经归一化，范围约-0.5到0.5）
            # t=1时，radius=sqrt(2)，可以覆盖对角线
            radius = t_val * ti.sqrt(2.0)
            radius_sq = radius * radius

            for i, j in ti.ndrange(data.shape[0], data.shape[1]):
                dist_sq = dx[i, j] * dx[i, j] + dy[i, j] * dy[i, j]
                if dist_sq <= radius_sq:
                    data[i, j] = 1.0

        compute_circle_mask(self._data, self._dx, self._dy, t)
