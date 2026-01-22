from abc import ABC, abstractmethod
from dataclasses import dataclass

import taichi as ti

from misc.taichi import read_image_to_taichi, img2d, bilinear_sample



@dataclass
class Sprite(ABC):
    # 起点坐标
    x: int = 0
    y: int = 0

    rotation: float = 0  # 旋转弧度
    scale: float = 1  # 缩放比例，1为无缩放
    alpha: float = 1  # 0-1 不透明度，0为完全透明，1为完全不透明

    # 大小，暂时不支持修改
    width: int = 0
    height: int = 0

    mask: 'textures.mask.Mask' = None


    def reset_property(self):
        self.x = 0
        self.y = 0
        self.rotation = 0.0
        self.scale = 1.0
        self.alpha = 1.0


    @abstractmethod
    def render(self, screen: img2d.field) -> img2d.field:
        """
        绘制精灵（优化版：只遍历包围盒区域）

        :param screen: 目标显示区域，用于绘制精灵
        :param t: 时间参数，用于计算（0-1）

        加入alpha=0.3，档t=0.5时，此时渲染的其实是0.3*0.5=0.15的透明度
        """
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

    def calculate_bounding_box(self, parent_width: int, parent_height: int) -> tuple[int, int, int, int]:
        """
        计算旋转+缩放后的精灵包围盒，并与父级显示区域求交集
        返回：(min_x, max_x, min_y, max_y) 父级显示区域坐标范围

        清查看 bounding_box_visualize.png 以查看原理
        """
        import math

        # 精灵中心在父级显示区域上的真实位置
        center_x = self.x + self.cx
        center_y = self.y + self.cy

        # 缩放后的半宽和半高
        half_w = self.cx * self.scale
        half_h = self.cy * self.scale

        # 计算旋转后的四个角点（相对于中心）
        cos_r = math.cos(self.rotation)
        sin_r = math.sin(self.rotation)

        """
        假设中心点为(0,0)，原始精灵的四个角点为：
          (-half_w, -half_h) ●────────● (half_w, -half_h)
                             │        │
                             │   ●    │  ← 中心点 (0, 0)
                             │        │
          (-half_w, half_h)  ●────────● (half_w, half_h)
          
          所以真实的坐标需要加上中心点的偏移量，即center_x，center_y
          可以看到rx，ry就加上了center_x，center_y，即旋转后的真实坐标
        """
        corners = [
            (-half_w, -half_h),  # 左上
            ( half_w, -half_h),  # 右上
            ( half_w,  half_h),  # 右下
            (-half_w,  half_h),  # 左下
        ]

        # 旋转所有角点并找到边界
        rotated_xs = []
        rotated_ys = []
        for dx, dy in corners:
            rx = dx * cos_r - dy * sin_r + center_x
            ry = dx * sin_r + dy * cos_r + center_y
            rotated_xs.append(rx)
            rotated_ys.append(ry)

        # 包围盒边界
        min_x = max(0, int(min(rotated_xs)))
        max_x = min(parent_width - 1, int(max(rotated_xs)) + 1)
        min_y = max(0, int(min(rotated_ys)))
        max_y = min(parent_height - 1, int(max(rotated_ys)) + 1)

        return min_x, max_x, min_y, max_y



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
        绘制精灵（优化版：只遍历包围盒区域）
        """
        if self._image is None:
            self._load_image()

        # 如果缩放比例或透明度为0，直接返回
        if self.scale <= 1e-6 or self.alpha <= 1e-6:
            return screen

        # 计算裁剪后的包围盒
        screen_width, screen_height = screen.shape[0], screen.shape[1]
        min_x, max_x, min_y, max_y = self.calculate_bounding_box(screen_width, screen_height)

        # 如果包围盒无效（完全在屏幕外），直接返回
        if min_x >= max_x or min_y >= max_y :
            return screen

        @ti.kernel
        def render_sprite(
                cx: ti.f32,  # 纹理自身的中心x坐标（纹理本地坐标）
                cy: ti.f32,  # 纹理自身的中心y坐标（纹理本地坐标）
                min_x: ti.i32,  # 包围盒最小x
                max_x: ti.i32,  # 包围盒最大x
                min_y: ti.i32,  # 包围盒最小y
                max_y: ti.i32,  # 包围盒最大y
                mask: ti.template(),  # 输入遮罩数组（shape=(width, height), dtype=ti.f32）
                use_mask: ti.template(),  # 是否使用 mask（编译时常量）
                mask_alpha: ti.u1, # 遮罩是否使用alpha通道
                screen: ti.template(),  # 输出屏幕数组（RGBA格式，shape=(width, height, 4)）
        ):
            x = ti.cast(self.x, ti.f32)
            y = ti.cast(self.y, ti.f32)
            scale = ti.cast(self.scale, ti.f32)
            rotation = ti.cast(self.rotation, ti.f32)
            alpha = ti.cast(self.alpha, ti.f32)

            width = ti.cast(self.width, ti.f32) # 原始的宽度、高度，用于限制self.image[x,y]的范围。不会影响scale之后的宽高
            height = ti.cast(self.height, ti.f32) # 也就是scale之后，仍然会显示缩放之后的高度

            # 是否使用双线性插值采样（缩放比例不是1.0）
            use_bilinear = (ti.abs(scale - 1.0) > 1e-6)

            # 预计算逆旋转矩阵（用于从屏幕坐标反推纹理坐标）
            cos_rot = ti.cos(rotation)
            sin_rot = ti.sin(rotation)
            rot_matrix = ti.math.mat2(cos_rot, sin_rot, -sin_rot, cos_rot)

            # 只遍历包围盒区域（优化核心！）
            for x_screen, y_screen in ti.ndrange((min_x, max_x + 1), (min_y, max_y + 1)):
                screen_color = screen[x_screen, y_screen]
                
                # 计算屏幕像素相对于精灵中心的偏移（精灵中心 = 左上角 + 中心偏移）
                # dx,dy得到的结果是假设中心点为(0,0)，下文中加上cx,cy才是精灵的真实坐标
                dx = x_screen - (x + cx)  # x对应w维度
                dy = y_screen - (y + cy)  # y对应h维度
                screen_offset = ti.math.vec2(dx, dy)

                # 逆变换：屏幕偏移 → 纹理本地坐标（浮点数）
                tex_offset = rot_matrix @ screen_offset / scale
                tex_x_f = cx + tex_offset.x
                tex_y_f = cy + tex_offset.y

                # 边界检查：纹理坐标越界则跳过
                if not (0 <= tex_x_f < width and 0 <= tex_y_f < height):
                    continue

                tex_x_i = ti.cast(tex_x_f, ti.i32)
                tex_y_i = ti.cast(tex_y_f, ti.i32)

                # 双线性插值采样，用于放大、缩小
                tex_color = bilinear_sample(self._image, tex_x_f, tex_y_f, width, height) if use_bilinear else self._image[tex_x_i, tex_y_i]

                # Alpha混合，不透明度
                final_alpha = ti.min(tex_color.w * alpha, 1.0)
                
                # 应用 mask（如果存在）
                if ti.static(use_mask):
                    # 从 mask 中采样（使用纹理坐标）

                    if ti.static(mask_alpha):
                        # 使用 mask 的 alpha 通道
                        mask_value = mask[tex_x_i, tex_y_i].w
                    else:
                        # 使用 mask 的灰度值（r通道）
                        mask_value = mask[tex_x_i, tex_y_i].x
                    final_alpha *= mask_value
                
                # 透明度过低则跳过
                if final_alpha <= 1e-6:
                    continue
                
                # Alpha 混合
                new_color = ti.math.mix(screen_color, tex_color, final_alpha)
                new_color.w = 1.0
                screen[x_screen, y_screen] = new_color

        # 判断是否使用 mask
        has_mask = self.mask is not None
        
        render_sprite(
            float(self.cx),
            float(self.cy),
            min_x, max_x,
            min_y, max_y,
            self.mask.data() if has_mask else self._image,  # 如果没有 mask，传递一个有效的 field（不会被使用）
            ti.static(has_mask),  # 编译时常量
            1 if has_mask and self.mask.enabled_alpha() else 0,
            screen,
        )

        return screen



