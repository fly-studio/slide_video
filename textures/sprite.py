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



# ============ Taichi Kernels（模块级别，避免重复编译）============

@ti.kernel
def _render_sprite_no_mask(
        image: ti.template(),  # 纹理图像
        x: ti.f32, y: ti.f32,  # 精灵位置
        cx: ti.f32, cy: ti.f32,  # 纹理中心
        scale: ti.f32,  # 缩放
        rotation: ti.f32,  # 旋转
        alpha: ti.f32,  # 透明度
        width: ti.f32, height: ti.f32,  # 纹理尺寸
        min_x: ti.i32, max_x: ti.i32,  # 包围盒
        min_y: ti.i32, max_y: ti.i32,
        screen: ti.template(),  # 输出屏幕
):
    # 是否使用双线性插值采样（缩放比例不是1.0）
    use_bilinear = (ti.abs(scale - 1.0) > 1e-6)

    # 预计算逆旋转矩阵（用于从屏幕坐标反推纹理坐标）
    cos_rot = ti.cos(rotation)
    sin_rot = ti.sin(rotation)
    rot_matrix = ti.math.mat2(cos_rot, sin_rot, -sin_rot, cos_rot)

    # 只遍历包围盒区域
    for x_screen, y_screen in ti.ndrange((min_x, max_x + 1), (min_y, max_y + 1)):
        screen_color = screen[x_screen, y_screen]
        
        # 计算屏幕像素相对于精灵中心的偏移
        dx = x_screen - (x + cx)
        dy = y_screen - (y + cy)
        screen_offset = ti.math.vec2(dx, dy)

        # 逆变换：屏幕偏移 → 纹理本地坐标
        tex_offset = rot_matrix @ screen_offset / scale
        tex_x_f = cx + tex_offset.x
        tex_y_f = cy + tex_offset.y

        # 边界检查：纹理坐标越界则跳过
        if not (0 <= tex_x_f < width and 0 <= tex_y_f < height):
            continue

        # 双线性插值采样
        tex_color = bilinear_sample(image, tex_x_f, tex_y_f, width, height) if use_bilinear else image[ti.cast(tex_x_f, ti.i32), ti.cast(tex_y_f, ti.i32)]

        # Alpha混合
        final_alpha = ti.min(tex_color.w * alpha, 1.0)
        
        # 透明度过低则跳过
        if final_alpha <= 1e-6:
            continue
        
        # Alpha 混合
        new_color = ti.math.mix(screen_color, tex_color, final_alpha)
        new_color.w = 1.0
        screen[x_screen, y_screen] = new_color


@ti.kernel
def _render_sprite_with_mask(
        image: ti.template(),  # 纹理图像
        x: ti.f32, y: ti.f32,  # 精灵位置
        cx: ti.f32, cy: ti.f32,  # 纹理中心
        scale: ti.f32,  # 缩放
        rotation: ti.f32,  # 旋转
        alpha: ti.f32,  # 透明度
        width: ti.f32, height: ti.f32,  # 纹理尺寸
        min_x: ti.i32, max_x: ti.i32,  # 包围盒
        min_y: ti.i32, max_y: ti.i32,
        mask: ti.types.ndarray(dtype=ti.f32),  # 遮罩（mask2d.field，标量 f32）
        screen: ti.template(),  # 输出屏幕
):
    # 是否使用双线性插值采样（缩放比例不是1.0）
    use_bilinear = (ti.abs(scale - 1.0) > 1e-6)

    # 预计算逆旋转矩阵（用于从屏幕坐标反推纹理坐标）
    cos_rot = ti.cos(rotation)
    sin_rot = ti.sin(rotation)
    rot_matrix = ti.math.mat2(cos_rot, sin_rot, -sin_rot, cos_rot)

    # 只遍历包围盒区域
    for x_screen, y_screen in ti.ndrange((min_x, max_x + 1), (min_y, max_y + 1)):
        screen_color = screen[x_screen, y_screen]
        
        # 计算屏幕像素相对于精灵中心的偏移
        dx = x_screen - (x + cx)
        dy = y_screen - (y + cy)
        screen_offset = ti.math.vec2(dx, dy)

        # 逆变换：屏幕偏移 → 纹理本地坐标
        tex_offset = rot_matrix @ screen_offset / scale
        tex_x_f = cx + tex_offset.x
        tex_y_f = cy + tex_offset.y

        # 边界检查：纹理坐标越界则跳过
        if not (0 <= tex_x_f < width and 0 <= tex_y_f < height):
            continue

        tex_x_i = ti.cast(tex_x_f, ti.i32)
        tex_y_i = ti.cast(tex_y_f, ti.i32)

        # 双线性插值采样
        tex_color = bilinear_sample(image, tex_x_f, tex_y_f, width, height) if use_bilinear else image[tex_x_i, tex_y_i]

        # Alpha混合
        final_alpha = ti.min(tex_color.w * alpha, 1.0)

        # 应用 mask（mask2d 是标量 field，直接访问）
        mask_value = mask[tex_x_i, tex_y_i]
        final_alpha *= mask_value
        
        # 透明度过低则跳过
        if final_alpha <= 1e-6:
            continue
        
        # Alpha 混合
        new_color = ti.math.mix(screen_color, tex_color, final_alpha)
        new_color.w = 1.0
        screen[x_screen, y_screen] = new_color


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
        if min_x >= max_x or min_y >= max_y:
            return screen

        # 根据是否有 mask 选择不同的 kernel
        if self.mask is not None:
            _render_sprite_with_mask(
                self._image,
                float(self.x), float(self.y),
                float(self.cx), float(self.cy),
                float(self.scale),
                float(self.rotation),
                float(self.alpha),
                float(self.width), float(self.height),
                min_x, max_x,
                min_y, max_y,
                self.mask.data(),
                screen,
            )
        else:
            _render_sprite_no_mask(
                self._image,
                float(self.x), float(self.y),
                float(self.cx), float(self.cy),
                float(self.scale),
                float(self.rotation),
                float(self.alpha),
                float(self.width), float(self.height),
                min_x, max_x,
                min_y, max_y,
                screen,
            )

        return screen



