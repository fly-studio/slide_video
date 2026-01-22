import cv2
import numpy as np
import taichi as ti

from misc.image import load_image

img2d = ti.types.vector(4, ti.f32)

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

    image = img2d.field(shape=(width, height))
    if color is None:
        return image
    fill_image_with_color(image, color_as_f32(color))
    return image



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
def taichi_image_to_cv2(data: ti.template(), out: ti.types.ndarray(dtype=ti.u8, ndim=3)):
    """
    将Taichi图像转换为OpenCV图像
    """

    for i, j in ti.ndrange(out.shape[0], out.shape[1]):
        r, g, b, a = data[j, i]
        ti.static_print(data[j, i])
        out[i, j, 0] = ti.cast(b * 255., ti.u8)
        out[i, j, 1] = ti.cast(g * 255., ti.u8)
        out[i, j, 2] = ti.cast(r * 255., ti.u8)
        out[i, j, 3] = ti.cast(a * 255., ti.u8)


def save_taichi_image(image: img2d.field, image_file: str, output_image: np.ndarray = None):
    """
    保存Taichi图像到文件

    :param image_file: 图像文件路径
    :param image: 输入Taichi图像字段
    :param output_image: 输出OpenCV图像（NumPy数组），shape=(height, width, channels)，channels为4。如果为None，则会创建一个新的数组。
    """

    width, height = image.shape
    output_image = np.empty((height, width, 4), dtype=np.uint8) if output_image is None else output_image
    taichi_image_to_cv2(image, output_image)
    cv2.imwrite(image_file, output_image)


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
