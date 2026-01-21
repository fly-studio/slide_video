from pathlib import Path

import cv2
import numpy as np


def bgr2rgb(image: np.ndarray) -> np.ndarray:
    """处理图像，将CV2默认的BGR格式转换为RGB格式"""
    if image is None:
        raise ValueError("输入图像为空")

    channels = image.shape[-1]

    # 根据通道数选择对应的转换方式
    if channels == 3:
        # BGR -> RGB
        return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    elif channels == 4:
        # BGRA -> RGBA（保留alpha通道）
        return cv2.cvtColor(image, cv2.COLOR_BGRA2RGBA)

    return image


def load_image(image_path: str | Path, width: int = None, height: int = None, keep_aspect_ratio: bool = True) -> np.ndarray:
    """
    加载并缓存图像

    :param image_path: 图像文件路径
    :param width: 目标宽度（默认None）
    :param height: 目标高度（默认None）
    :param keep_aspect_ratio: 是否保持宽高比（默认True）
    :return: 加载并处理后的图像（NumPy数组）
    """
    image_path_obj = Path(image_path)
    if not image_path_obj.exists():
        raise FileNotFoundError(f"图像文件不存在: {image_path}")

    image = cv2.imread(str(image_path_obj))
    if image is None:
        raise ValueError(f"无法加载图像: {image_path}")


    if width is not None and height is not None:
        image = resize_image(image, width, height, keep_aspect_ratio)

    return image


def resize_image(image: np.ndarray, width: int, height: int, keep_aspect_ratio: bool = True) -> np.ndarray:
    """
    调整图像到目标分辨率

    :param image: 输入图像（NumPy数组）
    :param width: 目标宽度
    :param height: 目标高度
    :param keep_aspect_ratio: 是否保持宽高比（默认True）
    :return: 调整后的图像（NumPy数组）
    """
    h, w = image.shape[:2]

    if not keep_aspect_ratio:
        return cv2.resize(image, (width, height), interpolation=cv2.INTER_LINEAR)

    # 保持宽高比，裁剪
    scale = max(width / w, height / h)
    new_w = int(w * scale)
    new_h = int(h * scale)

    resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

    # 居中裁剪
    crop_x = (new_w - width) // 2
    crop_y = (new_h - height) // 2

    cropped = resized[crop_y: crop_y + height, crop_x: crop_x + width]
    return cropped

def create_canvas(width: int, height: int, color: tuple[int, int, int] = (0, 0, 0)) -> np.ndarray:
    """
    创建空白画布

    Args:
        width: 宽度
        height: 高度
        color: 背景颜色 (B, G, R)

    Returns:
        numpy数组 (H, W, C)
    """
    return np.full((height, width, 3), color, dtype=np.uint8)
    # canvas = np.zeros((height, width, 3), dtype=np.uint8)
    # canvas[:, :] = color
    # return canvas


def resize_to_fit(
    image: np.ndarray, target_size: tuple[int, int], keep_aspect_ratio: bool = True
) -> np.ndarray:
    """
    调整图像大小以适应目标尺寸

    Args:
        image: 输入图像
        target_size: 目标尺寸 (width, height)
        keep_aspect_ratio: 是否保持宽高比

    Returns:
        调整后的图像
    """
    import cv2

    target_width, target_height = target_size
    h, w = image.shape[:2]

    if not keep_aspect_ratio:
        return cv2.resize(image, (target_width, target_height), interpolation=cv2.INTER_LINEAR)

    # 计算缩放比例
    scale = min(target_width / w, target_height / h)
    new_w = int(w * scale)
    new_h = int(h * scale)

    # 缩放
    resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

    # 居中放置
    canvas = create_canvas(target_width, target_height)
    x_offset = (target_width - new_w) // 2
    y_offset = (target_height - new_h) // 2
    canvas[y_offset : y_offset + new_h, x_offset : x_offset + new_w] = resized

    return canvas