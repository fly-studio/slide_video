from pathlib import Path

import cv2
import numpy as np


def load_image(image_path: str | Path) -> np.ndarray:
    """加载并缓存图像"""
    image_path_obj = Path(image_path)
    if not image_path_obj.exists():
        raise FileNotFoundError(f"图像文件不存在: {image_path}")

    image = cv2.imread(str(image_path_obj))
    if image is None:
        raise ValueError(f"无法加载图像: {image_path}")

    return image


def resize_image(image: np.ndarray, width: int, height: int, keep_aspect_ratio: bool = True) -> np.ndarray:
    """调整图像到目标分辨率"""
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