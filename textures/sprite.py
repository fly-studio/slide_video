from abc import ABC, abstractmethod
from dataclasses import dataclass

import taichi as ti

from misc.taichi import read_image_to_taichi, img2d


@dataclass
class Sprite(ABC):
    # 起点坐标
    x: int = 0
    y: int = 0

    # 大小
    width: int = 0
    height: int = 0

    rotation: float = 0 # 旋转弧度
    scale: float = 1 # 缩放比例，1为无缩放
    alpha: float = 1 # 0-1 透明度，0为完全透明，1为完全不透明

    @abstractmethod
    def render(self, screen: img2d.field) -> img2d.field:
        pass

    @property
    def cx(self) -> float:
        """
        获取纹理中心x本地坐标
        """
        return self.width // 2

    @property
    def cy(self) -> float:
        """
        获取纹理中心y本地坐标
        """
        return self.height // 2



@dataclass
class ImageSprite(Sprite):
    image_file: str = None
    _image: img2d.field = None


    def _load_image(self):
        if self.width > 0 and self.height > 0:
            # 已指定大小，根据指定大小加载图像
            self._image = read_image_to_taichi(self.image_file, self.width, self.height)
        else:
            # 未指定大小，根据图像实际大小初始化
            self._image = read_image_to_taichi(self.image_file)

        self.width, self.height = self._image.shape


    def render(self, screen: img2d.field) -> img2d.field:
        """
        绘制精灵
        """
        if self._image is None:
            self._load_image()

        @ti.kernel
        def render_sprite(
                cx: ti.f32,  # 纹理自身的中心x坐标（纹理本地坐标）
                cy: ti.f32,  # 纹理自身的中心y坐标（纹理本地坐标）
                screen: ti.template(),  # 输出屏幕数组（RGBA格式，shape=(width, height, 4)）
        ):
            x = ti.cast(self.x, ti.f32)
            y = ti.cast(self.y, ti.f32)
            scale = ti.cast(self.scale, ti.f32)
            rotation = ti.cast(self.rotation, ti.f32)
            width = ti.cast(self.width, ti.f32)
            height = ti.cast(self.height, ti.f32)
            alpha = ti.cast(self.alpha, ti.f32)

            # 预计算逆旋转矩阵（用于从屏幕坐标反推纹理坐标）
            cos_rot = ti.cos(rotation)
            sin_rot = ti.sin(rotation)
            rot_matrix = ti.math.mat2(cos_rot, sin_rot, -sin_rot, cos_rot)

            # 遍历屏幕
            for x_screen, y_screen in screen:
                screen_color = screen[x_screen, y_screen]
                # 4. 计算屏幕像素相对于精灵中心的偏移（精灵中心 = 左上角 + 中心偏移）
                dx = x_screen - (x + cx)  # x对应w维度
                dy = y_screen - (y + cy)  # y对应h维度
                screen_offset = ti.math.vec2(dx, dy)

                # 5. 逆变换：屏幕偏移 → 纹理本地坐标
                tex_offset = rot_matrix @ screen_offset / scale
                tex_x = ti.cast(cx + tex_offset.x, ti.i32)  # 纹理x → 对应tex_w维度
                tex_y = ti.cast(cy + tex_offset.y, ti.i32)  # 纹理y → 对应tex_h维度

                # 6. 边界检查（纹理坐标需在有效范围）
                if 0 <= tex_x < width and 0 <= tex_y < height:
                    # 7. 纹理采样：归一化坐标要匹配纹理shape=(h,w)
                    # 注意：tex.sample的输入是 (u, v) → (x/tex_w, y/tex_h)，和shape顺序无关！
                    tex_color = self._image[tex_x, tex_y]

                    # 8. Alpha混合（逻辑不变）
                    final_alpha = tex_color.w * alpha
                    if final_alpha > 1e-6:
                        new_color = ti.math.vec4(
                            tex_color.x * final_alpha + screen_color.x * (1 - final_alpha),
                            tex_color.y * final_alpha + screen_color.y * (1 - final_alpha),
                            tex_color.z * final_alpha + screen_color.z * (1 - final_alpha),
                            1.0
                        )
                        screen[x_screen, y_screen] = new_color

        render_sprite(
            float(self.cx),
            float(self.cy),
            screen,
        )

        return screen

