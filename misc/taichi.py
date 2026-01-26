import cv2
import numpy as np
import taichi as ti

from misc.image import load_image

img2d = ti.types.vector(4, ti.f32)
mask2d = ti.types.ndarray(ti.f32)

def color_as_f32(color: tuple[int, int, int, int]) -> ti.types.vector(4, ti.f32):
    """
    将u8颜色转换为f32颜色
    """
    return ti.types.vector(4, ti.u8)(*color) / 255.0


@ti.kernel
def fill_image_with_color(img: ti.template(), color: ti.types.vector(4, ti.f32)):
    """
    使用u8颜色填充图像
    """
    w, h = img.shape
    for i, j in ti.ndrange(w, h):
        img[i, j] = color


def create_canvas(width: int, height: int, color: tuple[int, int, int, int] = None) -> img2d.field:
    """
    创建一个指定宽度和高度的图像，并使用u8颜色填充

    :param width: 图像宽度
    :param height: 图像高度
    :param color: u8颜色元组（r, g, b, a），0~255。a为透明度，0为完全透明，255为完全不透明。
    :return: 填充好颜色的图像字段
    """

    canvas = img2d.field(shape=(width, height))
    if color is None:
        return canvas
    canvas.fill(color_as_f32(color))
    # fill_image_with_color(canvas, color_as_f32(color))
    return canvas



@ti.kernel
def cv_image_to_taichi(img: ti.types.ndarray(dtype=ti.u8, ndim=3), out: ti.template()):
    """
    将OpenCV图像转换为Taichi图像

    :param img: 输入OpenCV图像（NumPy数组），shape=(height, width, channels)，channels为3或4。
    :param out: 输出Taichi图像字段，shape=(height, width, 4)。
    """
    a = ti.cast(0xff, ti.u8)
    channels = img.shape[-1]
    for i, j in ti.ndrange(img.shape[0], img.shape[1]):
        r = img[i, j, 2]
        g = img[i, j, 1]
        b = img[i, j, 0]
        if channels == 4:
            a = img[i, j, 3]

        out[j, i] = ti.types.vector(4, ti.u8)(r, g, b, a) / 255.


def read_image_to_taichi(image_file: str, width: int = None, height: int = None) -> img2d.field:
    """
    从文件读取图像并转换为Taichi图像

    :param image_file: 图像文件路径
    :param width: 目标宽度
    :param height: 目标高度
    :return: 转换后的Taichi图像字段
    """
    img = load_image(image_file, width, height)
    if width is None:
        # opencv 的图像默认是 (height, width, color)
        width = img.shape[1]
    if height is None:
        height = img.shape[0]

    out = img2d.field(shape=(width, height))

    cv_image_to_taichi(img, out)
    return out

@ti.kernel
def taichi_image_to_bgra(data: ti.template(), out: ti.types.ndarray(dtype=ti.u8, ndim=3)):
    """
    将Taichi图像转换为BGRA图像
    """

    w, h = out.shape[0], out.shape[1]
    for i, j in ti.ndrange(w, h):
        r, g, b, a = data[j, i]
        out[i, j, 0] = ti.cast(b * 255., ti.u8)
        out[i, j, 1] = ti.cast(g * 255., ti.u8)
        out[i, j, 2] = ti.cast(r * 255., ti.u8)
        out[i, j, 3] = ti.cast(a * 255., ti.u8)


@ti.kernel
def taichi_image_to_bgr(data: ti.template(), out: ti.types.ndarray(dtype=ti.u8, ndim=3)):
    """
    将Taichi图像转换为BGR图像，没有alpha通道
    """
    w, h = out.shape[0], out.shape[1]
    for i, j in ti.ndrange(w, h):
        r, g, b, _ = data[j, i]
        out[i, j, 0] = ti.cast(b * 255., ti.u8)
        out[i, j, 1] = ti.cast(g * 255., ti.u8)
        out[i, j, 2] = ti.cast(r * 255., ti.u8)


def save_taichi_image(image: img2d.field, image_file: str, output_image: ti.types.ndarray(dtype=ti.u8) = None):
    """
    保存Taichi图像到文件

    :param image_file: 图像文件路径
    :param image: 输入Taichi图像字段
    :param output_image: 输出OpenCV图像（NumPy数组），shape=(height, width, channels)，channels为4。如果为None，则会创建一个新的数组。
    """

    width, height = image.shape
    output_image = np.empty((height, width, 4), dtype=np.uint8) if output_image is None else output_image
    taichi_image_to_bgra(image, output_image)
    cv2.imwrite(image_file, output_image)


@ti.func
def lanczos_weight(x: ti.f32, a: ti.i32) -> ti.f32:
    """
    Lanczos 窗口函数
    a: 窗口大小（通常为 2, 3, 或 4）
    """
    result = 0.0
    x_abs = ti.abs(x)
    if x_abs < 1e-6:
        result = 1.0
    elif x_abs < a:
        pi_x = 3.14159265359 * x_abs
        result = a * ti.sin(pi_x) * ti.sin(pi_x / a) / (pi_x * pi_x)
    return result


@ti.func
def lanczos4_sample(image: ti.template(), x: ti.f32, y: ti.f32, width: ti.f32, height: ti.f32) -> ti.math.vec4:
    """
    Lanczos4 插值采样（质量最高，适合高质量放大）

    :param image: 图像字段
    :param x: 浮点x坐标
    :param y: 浮点y坐标
    :param width: 图像宽度
    :param height: 图像高度
    :return: 插值后的颜色
    """
    result = ti.math.vec4(0.0, 0.0, 0.0, 0.0)

    # 中心像素坐标
    x_center = ti.floor(x)
    y_center = ti.floor(y)

    # 采样 8x8 邻域（Lanczos4 需要 a=4）
    for dy in ti.static(range(-3, 5)):
        for dx in ti.static(range(-3, 5)):
            # 邻近像素坐标
            px = ti.cast(x_center + dx, ti.i32)
            py = ti.cast(y_center + dy, ti.i32)

            # 边界检查
            if 0 <= px < width and 0 <= py < height:
                # 计算权重
                wx = lanczos_weight(x - (x_center + dx), 4)
                wy = lanczos_weight(y - (y_center + dy), 4)
                weight = wx * wy

                # 累加加权颜色
                result += image[px, py] * weight

    return result


@ti.func
def cubic_weight(t: ti.f32) -> ti.f32:
    """
    三次插值权重函数（Catmull-Rom）
    """
    t_abs = ti.abs(t)
    result = 0.0
    if t_abs <= 1.0:
        result = 1.5 * t_abs * t_abs * t_abs - 2.5 * t_abs * t_abs + 1.0
    elif t_abs <= 2.0:
        result = -0.5 * t_abs * t_abs * t_abs + 2.5 * t_abs * t_abs - 4.0 * t_abs + 2.0
    return result


@ti.func
def bicubic_sample(image: ti.template(), x: ti.f32, y: ti.f32, width: ti.f32, height: ti.f32) -> ti.math.vec4:
    """
    双三次插值采样（Bicubic Interpolation）
    质量远超双线性插值，适合图像放大

    :param image: 图像字段
    :param x: 浮点x坐标
    :param y: 浮点y坐标
    :param width: 图像宽度
    :param height: 图像高度
    :return: 插值后的颜色
    """
    result = ti.math.vec4(0.0, 0.0, 0.0, 0.0)

    # 中心像素坐标
    x_center = ti.floor(x)
    y_center = ti.floor(y)

    # 采样 4x4 邻域
    for dy in ti.static(range(-1, 3)):
        for dx in ti.static(range(-1, 3)):
            # 邻近像素坐标
            px = ti.cast(x_center + dx, ti.i32)
            py = ti.cast(y_center + dy, ti.i32)

            # 边界检查
            if 0 <= px < width and 0 <= py < height:
                # 计算权重
                wx = cubic_weight(x - (x_center + dx))
                wy = cubic_weight(y - (y_center + dy))
                weight = wx * wy

                # 累加加权颜色
                result += image[px, py] * weight

    return result


@ti.func
def bilinear_sample(image: ti.template(), x: ti.f32, y: ti.f32, width: ti.f32, height: ti.f32) -> ti.math.vec4:
    """
    双线性插值采样

    :param image: 图像字段
    :param x: 浮点x坐标
    :param y: 浮点y坐标
    :param width: 图像宽度
    :param height: 图像高度
    :return: 插值后的颜色
    """
    result = ti.math.vec4(0.0, 0.0, 0.0, 0.0)

    # 获取四个邻近像素的坐标
    # Bottom-left corner
    x1 = ti.cast(ti.floor(x), ti.i32)
    y1 = ti.cast(ti.floor(y), ti.i32)
    # Top-right corner
    x2 = ti.min(x1 + 1, ti.cast(width - 1, ti.i32))
    y2 = ti.min(y1 + 1, ti.cast(height - 1, ti.i32))

    # 边界检查
    if 0 <= x1 < width and 0 <= y1 < height:
        # 获取四个角点的颜色
        Q11 = image[x1, y1]
        Q21 = image[x2, y1]
        Q12 = image[x1, y2]
        Q22 = image[x2, y2]

        # 计算插值权重
        fx = x - x1
        fy = y - y1

        # 双线性插值
        R1 = Q11 * (1.0 - fx) + Q21 * fx
        R2 = Q12 * (1.0 - fx) + Q22 * fx
        result = R1 * (1.0 - fy) + R2 * fy

    return result


@ti.kernel
def compute_distance_field(mask: ti.template(), dist: ti.template()):
    """
    计算距离场（简化版，使用多次迭代）
    mask: 二值遮罩（0或1）
    dist: 输出距离场
    """
    w, h = mask.shape
    INF = 999999.0

    # 初始化：mask=1的地方距离为0，否则为无穷大
    for i, j in ti.ndrange(w, h):
        dist[i, j] = 0.0 if mask[i, j] > 0.5 else INF

    # 多次迭代扩散（简化的距离变换）
    for _ in range(8):  # 迭代次数
        for i, j in ti.ndrange(w, h):
            if dist[i, j] > 0:
                min_dist = dist[i, j]
                # 检查8邻域
                for di, dj in ti.static([(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]):
                    ni, nj = i + di, j + dj
                    if 0 <= ni < w and 0 <= nj < h:
                        neighbor_dist = dist[ni, nj] + ti.sqrt(ti.cast(di*di + dj*dj, ti.f32))
                        min_dist = ti.min(min_dist, neighbor_dist)
                dist[i, j] = min_dist

@ti.kernel
def apply_feather_linear(dist: ti.template(), output: ti.template(), feather_radius: ti.f32):
    """
    应用线性羽化效果

    :param dist: 距离场
    :param output: 输出遮罩（0-1）
    :param feather_radius: 羽化半径
    """
    w, h = dist.shape
    for i, j in ti.ndrange(w, h):

        alpha = ti.min(dist[i, j] / feather_radius, 1.0)
        output[i, j] = ti.clamp(alpha, 0.0, 1.0)

@ti.kernel
def apply_feather_conic(dist: ti.template(), output: ti.template(), feather_radius: ti.f32):
    """
    应用圆锥羽化效果

    :param dist: 距离场
    :param output: 输出遮罩（0-1）
    :param feather_radius: 羽化半径
    """
    w, h = dist.shape
    for i, j in ti.ndrange(w, h):
        norm_dist = ti.min(dist[i, j] / feather_radius, 1.0)

        alpha = ti.pow(norm_dist, 1.6)
        output[i, j] = ti.clamp(alpha, 0.0, 1.0)

@ti.kernel
def apply_feather_smoothstep(dist: ti.template(), output: ti.template(), feather_radius: ti.f32):
    """
    应用平滑步函数羽化效果

    :param dist: 距离场
    :param output: 输出遮罩（0-1）
    :param feather_radius: 羽化半径
    """
    w, h = dist.shape
    for i, j in ti.ndrange(w, h):
        norm_dist = ti.min(dist[i, j] / feather_radius, 1.0)

        alpha = norm_dist * norm_dist * (3.0 - 2.0 * norm_dist)
        output[i, j] = ti.clamp(alpha, 0.0, 1.0)

@ti.kernel
def apply_feather_sigmoid(dist: ti.template(), output: ti.template(), feather_radius: ti.f32):
    """
    应用 sigmoid 函数羽化效果

    :param dist: 距离场
    :param output: 输出遮罩（0-1）
    :param feather_radius: 羽化半径
    """
    w, h = dist.shape
    for i, j in ti.ndrange(w, h):
        norm_dist = ti.min(dist[i, j] / feather_radius, 1.0)

        k = 6.0
        alpha = 1.0 / (1.0 + ti.exp(-k * (norm_dist - 0.5)))
        output[i, j] = ti.clamp(alpha, 0.0, 1.0)


@ti.kernel
def apply_mask_kernel(canvas: ti.template(), mask: ti.template(), multiply_alpha: ti.u1):
    """
    应用遮罩到图像上

    :param canvas: 输入图像字段（RGBA）
    :param mask: 遮罩字段（0-1，单通道）
    :param multiply_alpha: 0=直接替换 alpha，1=与原 alpha 相乘
    """
    canvas_w, canvas_h = canvas.shape
    mask_w, mask_h = mask.shape
    w = ti.min(canvas_w, mask_w)
    h = ti.min(canvas_h, mask_h)

    for x, y in ti.ndrange(w, h):
        color = canvas[x, y]
        mask_val = mask[x, y]

        # 使用 ti.static 在编译时优化分支（零开销）
        if ti.static(multiply_alpha == 1):
            color.w = color.w * mask_val  # 与原 alpha 相乘
        else:
            color.w = mask_val  # 直接替换 alpha

        canvas[x, y] = color


def apply_mask(canvas: img2d.field, mask: mask2d, enabled_alpha: bool):
    """
    应用遮罩到图像上

    :param canvas: 输入图像字段
    :param mask: 遮罩字段（0-1）
    :param enabled_alpha: 是否启用原 alpha 通道（False=直接替换，True=相乘）
    """
    apply_mask_kernel(canvas, mask, 1 if enabled_alpha else 0)
