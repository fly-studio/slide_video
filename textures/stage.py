from dataclasses import dataclass, field

from misc.taichi import img2d, create_canvas, save_taichi_image, color_as_f32
from textures.sprite import Sprite


@dataclass
class Stage:
    width: int
    height: int

    _children: list[Sprite] = field(default_factory=list)
    canvas: img2d.field = None

    _default_color: tuple[int, int, int, int] = (255, 255, 255, 255)

    def _init_canvas(self):
        # 预先创建 canvas，避免每次 render 都重新分配
        self.canvas = create_canvas(self.width, self.height, self._default_color)

    def add_child(self, child: Sprite):
        """
        添加一个子精灵到舞台上
        """
        self._children.append(child)


    def render(self):
        """
        渲染舞台上的所有精灵
        """
        if self.canvas is None:
            self._init_canvas()

        # 清空 canvas（填充背景色）
        self.canvas.fill(color_as_f32(self._default_color))

        for child in self._children:
            child.render(self.canvas)

    def save(self, image_file: str):
        """
        保存舞台上的所有精灵到文件
        """
        if self.canvas is not None:
            save_taichi_image(self.canvas, image_file)

