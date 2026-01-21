import numpy as np
from numba import njit, float32, prange


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

@njit('(int32, int32, float32, float32)', cache=True)
def create_normalized_dx_dy(height: int, width: int, cy_ratio: float, cx_ratio: float):
    """
    返回 (dy, dx) 两个 float32 数组，值域大约 -0.5 ~ 0.5
    """

    dy = np.empty((height, width), dtype=np.float32)
    dx = np.empty((height, width), dtype=np.float32)

    cy = height * cy_ratio
    cx = width  * cx_ratio

    for y in prange(height):
        for x in prange(width):
            dy[y, x] = (y - cy) / max(height, 1)
            dx[y, x] = (x - cx) / max(width, 1)

    return dy, dx


@njit(parallel=True, cache=True)  # parallel开启多线程
def alpha_blend(foreground, background, alpha):
    alpha = np.clip(alpha, 0.0, 1.0)
    beta = 1.0 - alpha
    # 预分配结果数组（避免临时数组）
    result = np.empty_like(foreground, dtype=np.float64)

    H, W, C = foreground.shape
    # 并行遍历每个通道和像素
    for c in prange(C):
        for i in range(H):
            for j in range(W):
                result[i, j, c] = foreground[i, j, c] * alpha + background[i, j, c] * beta
    return result.astype(np.uint8)
