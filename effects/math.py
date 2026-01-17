import cv2
import numpy as np
from numba import njit, prange, float32


@njit(parallel=True, fastmath=True, cache=True)
def merge_mask_with_alpha(
    fg,  # 前景 (h,w,3) 或 (h,w,4)
    bg,  # 背景 (h,w,3) 或 (h,w,4)
    mask: np.ndarray            # (h,w) float32, 0~1
) -> np.ndarray:
    """
    支持带 alpha 的 mask，也就是羽化的 mask。
    并自动识别图片是否带alpha
    """
    h, w = fg.shape[:2]

    fg_has_alpha = fg.shape[2] == 4
    bg_has_alpha = bg.shape[2] == 4

    # 決定輸出通道數
    out_channels = 4 if fg_has_alpha or bg_has_alpha else 3

    # 预分配数组时指定内存布局（C_CONTIGUOUS）
    result = np.empty((h, w, out_channels), dtype=np.uint8, order='C')

    # 优化2：将fg_a/bg_a的计算提到分支外（减少重复判断）
    for y in prange(h):
        # 优化3：按行取指针，减少索引开销（Numba对连续内存更友好）
        fg_row = fg[y]
        bg_row = bg[y]
        mask_row = mask[y]
        res_row = result[y]

        for x in range(w):  # x方向无需parallel，避免过度并行开销
            a_mask = mask_row[x]
            ia = 1.0 - a_mask

            if a_mask >= 0.999: # 转录fg
                res_row[x, :3] = fg_row[x, :3]
                if out_channels == 4:
                    res_row[x, 3] = fg_row[x, 3] if fg_has_alpha else 255
            elif a_mask <= 0.001: # 转录bg
                res_row[x, :3] = bg_row[x, :3]
                if out_channels == 4:
                    res_row[x, 3] = bg_row[x, 3] if bg_has_alpha else 255
            else:
                # 预计算fg_a/bg_a，减少重复索引
                fg_a = fg_row[x, 3] / 255.0 if fg_has_alpha else 1.0
                bg_a = bg_row[x, 3] / 255.0 if bg_has_alpha else 1.0
                out_a = a_mask * fg_a + ia * bg_a

                # 向量化赋值，减少循环
                res_row[x, 0] = np.uint8((a_mask * fg_a * fg_row[x, 0] + ia * bg_a * bg_row[x, 0]) + 0.5)
                res_row[x, 1] = np.uint8((a_mask * fg_a * fg_row[x, 1] + ia * bg_a * bg_row[x, 1]) + 0.5)
                res_row[x, 2] = np.uint8((a_mask * fg_a * fg_row[x, 2] + ia * bg_a * bg_row[x, 2]) + 0.5)

                if out_channels == 4:
                    res_row[x, 3] = np.uint8(out_a * 255 + 0.5)

    return result

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
    return merge_mask_with_alpha(foreground, background, mask_feather)

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


@njit('(int32, int32, float32, float32)', cache=True)
def create_normalized_dx_dy(height: int, width: int, cy_ratio: float, cx_ratio: float):
    """
    返回 (dy, dx) 两个 float32 数组，值域大约 -0.5 ~ 0.5
    """

    dy = np.empty((height, width), dtype=float32)
    dx = np.empty((height, width), dtype=float32)

    cy = height * cy_ratio
    cx = width  * cx_ratio

    for y in prange(height):
        for x in prange(width):
            dy[y, x] = (y - cy) / max(height, 1)
            dx[y, x] = (x - cx) / max(width, 1)

    return dy, dx