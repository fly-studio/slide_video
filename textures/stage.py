from dataclasses import dataclass, field

import numpy as np

from misc.taichi import img2d, create_canvas, save_taichi_image, color_as_f32
from textures.sprite import Sprite


@dataclass
class Stage:
    width: int
    height: int

    _children: list[Sprite] = field(default_factory=list)
    _canvas: img2d.field = None # 绘制区域：shape=(width, height, channels)，channels为4
    _output: np.ndarray = None # 输出图像，shape=(height, width, channels)，channels为4，注意：坐标系是反的，并且是BGRA格式

    _default_color: tuple[int, int, int, int] = (255, 255, 255, 255)

    def _init_canvas(self):
        # 预先创建 canvas，避免每次 render 都重新分配
        self._canvas = create_canvas(self.width, self.height, self._default_color)

    def add_child(self, child: Sprite):
        """
        添加一个子精灵到舞台上
        """
        self._children.append(child)


    def render(self):
        """
        渲染舞台上的所有精灵
        """
        if self._canvas is None:
            self._init_canvas()

        # 清空 canvas（填充背景色）
        self._canvas.fill(color_as_f32(self._default_color))

        for child in self._children:
            child.render(self._canvas)

    def save(self, image_file: str):
        """
        保存舞台上的所有精灵到文件
        """
        if self._output is None and self._canvas is not None:
            self._output = np.empty((self.height, self.width, 4), dtype=np.uint8)
        if self._canvas is not None:
            save_taichi_image(self._canvas, image_file, self._output)

