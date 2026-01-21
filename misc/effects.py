import cv2
import numpy as np

from misc import numba


def merge_mask(foreground: np.ndarray, background: np.ndarray, mask: np.ndarray, feather_pixel: int = 0) -> np.ndarray:
    """
    遮罩合并前景+背景，支持羽化

    :param foreground: 前景图
    :param background: 后景图
    :param mask: 支持 [0-255, ...]或[true, false, ...]，0表示不复制fg的像素到bg
    :param feather_pixel: 羽化边沿的像素
    """

    if mask.dtype != bool:
        mask = mask.astype(np.uint8) * 255

    h, w = foreground.shape[:2]

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:  # mask 为空，也就无前景
        return background

    if feather_pixel == 0:
        # 将foreground 中掩码 mask 非 0 的像素复制到 background 中，掩码 0 的区域不会被复制（目标图像对应位置保持原有值，若dst初始为空则置 0）。
        # cv2.copyTo会修改 #3参数，所以得copy一份新的
        result = background.copy()

        # 计算 bounding box
        bx, by, bw, bh = cv2.boundingRect(contours[0])

        if bw > w/2 or bh > h/2: # mask 太大，就不 crop 了
            cv2.copyTo(foreground, mask, result)
            return result

        # 裁剪 foreground 和 mask 到 bounding box
        cv2.copyTo(foreground[by:by+bh, bx:bx+bw], mask[by:by+bh, bx:bx+bw], result[by:by+bh, bx:bx+bw])

        return result


    mask_feather = feather_mask(mask, feather_pixel)

    # mask=1 → 显示前景；
    # mask=0.5 → 50% 前景 + 50% 背景；
    # mask=0 → 显示背景；
    return numba.merge_mask_with_alpha(foreground, background, mask_feather)

def feather_mask(mask: np.ndarray, feather_pixel: int, curve: str = 'linear') -> np.ndarray:
    """
    mask边沿羽化

    :param mask 支持[0-255, ...], [true, false, ...]
    :param feather_pixel 羽化半径，即从边沿往内多少像素
    :param curve 曲线方程，支持：conic, sigmoid, smoothstep, linear(默认），羽化的平滑程度
    """
    # 羽化半径小于等于0，直接返回原始mask
    if feather_pixel <= 0:
        return mask.astype(np.float32) / 255.0 if mask.dtype != bool else mask.astype(np.float32)

    # bool 或 uint8(0/255)
    if mask.dtype == bool:
        mask = mask.astype(np.uint8) * 255

    # 找 bounding box
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return np.zeros_like(mask, dtype=np.float32)

    mask_h, mask_w = mask.shape
    x, y, w, h = cv2.boundingRect(contours[0])
    # 动态扩展pad
    pad = feather_pixel // 2 + 2  # 足够避免截断，且更小
    x1 = max(0, x - pad)
    y1 = max(0, y - pad)
    x2 = min(mask_w, x + w + pad)
    y2 = min(mask_h, y + h + pad)

    # 裁剪，并计算真实距离
    mask_crop = mask[y1:y2, x1:x2]
    # 从中心往边沿，转为距离图，中心数字大，边缘距离小
    # 二值图（0 和 255），255 的地方是前景（物体），0 是背景,
    # 距离类型：cv2.DIST_L2 欧几里得距离（直线距离，最自然的人眼感觉）
    # 掩码大小：使用 5×5 的邻域模板 来做精确近似计算
    dist = cv2.distanceTransform(mask_crop, cv2.DIST_L2, 5)

    # 将距离图 / feather_radius 得到 羽化透明度，得到0~1.0的值
    # 比如feather_radius=10像素，则mask边沿往内部0-10px的alpha 0-1
    norm_dist = dist / feather_pixel

    if curve == 'conic':
        # 更柔和 - 二次曲线
        alpha_crop = norm_dist ** 1.6   # 1.3~2.0 之间调
    elif curve == 'sigmoid':
        # sigmoid 风格（非常柔和，电影特效常用）
        k = 6.0  # 越大越陡
        alpha_crop = 1 / (1 + np.exp(-k * (norm_dist - 0.5)))
    elif curve == 'smoothstep':
        # 经典 smoothstep (3t^2 - 2t^3)，更自然
        t = np.clip(norm_dist, 0, 1)
        alpha_crop = t * t * (3 - 2 * t)
    else: # linear
        alpha_crop = norm_dist

    # 确保alpha值在0-1之间
    alpha_crop = np.clip(alpha_crop, 0.0, 1.0)

    alpha = np.zeros((mask_h, mask_w), dtype=np.float32)
    alpha[y1:y2, x1:x2] = alpha_crop
    return alpha


def create_mask_with_center(width: int, height: int, center: tuple[float, float]) -> tuple[np.ndarray, np.ndarray]:
    """
    创建一个有中心的 mask

    :param height: mask 高度
    :param width: mask 宽度
    :param center: mask 中心坐标，(cx_ratio, cy_ratio)，范围 0~1，比如(0.5, 0.5)表示中心
    :return: (dy, dx) 两个 float32 数组，值域大约 -0.5 ~ 0.5
    """
    yy = np.tile(np.arange(height, dtype=np.float32).reshape(-1, 1), (1, width))
    xx = np.tile(np.arange(width, dtype=np.float32).reshape(1, -1), (height, 1))
    cy, cx = (center[1] * height), (center[0] * width)
    #yy, xx = np.mgrid[0:height, 0:width]
    scale = min(width, height)
    dy = (yy - cy) / max(scale, 1)  # 归一化 -0.5 ~ 0.5 左右
    dx = (xx - cx) / max(scale, 1)
    return dy.astype(np.float32), dx.astype(np.float32)



def alpha_blend(
    foreground: np.ndarray,
    background: np.ndarray,
    alpha: float
) -> np.ndarray:
    """
    混合两个图像，根据alpha系数进行线性插值

    :param foreground: 前景图像
    :param background: 背景图像
    :param alpha: 混合系数 [0.0, 1.0]，0表示完全背景，1表示完全前景

    :return: 混合后的图像
    """
    # 将alpha限制在0-1之间
    alpha = max(0.0, min(1.0, alpha))
    beta = 1.0 - alpha
    # OpenCV的addWeighted是高度优化的C++实现
    # 公式：dst = src1*alpha + src2*beta + gamma
    return cv2.addWeighted(foreground, alpha, background, beta, 0.0)

    return (foreground * alpha + background * beta).astype(np.uint8)