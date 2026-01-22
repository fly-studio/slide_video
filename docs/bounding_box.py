"""
可视化精灵旋转和包围盒计算


原理讲解用，不会被调用
"""
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

# 配置中文字体
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

def sprite_rotation(width=200, height=100, rotation_deg=30, scale=1.5):
    """
    可视化精灵旋转和包围盒计算过程

    Args:
        width: 精灵宽度
        height: 精灵高度
        rotation_deg: 旋转角度（度）
        scale: 缩放比例
    """
    fig, ax = plt.subplots(1, 1, figsize=(12, 10))

    # 精灵中心位置（假设在屏幕中央）
    center_x, center_y = 400, 300

    # 计算半宽和半高
    cx = width // 2
    cy = height // 2
    half_w = cx * scale
    half_h = cy * scale

    # 原始四个角点（相对于中心）
    corners_local = [
        (-half_w, -half_h),  # 左上
        ( half_w, -half_h),  # 右上
        ( half_w,  half_h),  # 右下
        (-half_w,  half_h),  # 左下
    ]

    # 旋转角度（转为弧度）
    rotation_rad = np.deg2rad(rotation_deg)
    cos_r = np.cos(rotation_rad)
    sin_r = np.sin(rotation_rad)

    # 1. 绘制原始矩形（未旋转，缩放后）
    original_rect = patches.Rectangle(
        (center_x - half_w, center_y - half_h),
        half_w * 2, half_h * 2,
        linewidth=2, edgecolor='blue', facecolor='lightblue', alpha=0.3,
        label='原始矩形（缩放后）'
    )
    ax.add_patch(original_rect)

    # 2. 旋转后的角点
    rotated_corners = []
    for dx, dy in corners_local:
        # 旋转公式：
        # x' = x*cos(θ) - y*sin(θ)
        # y' = x*sin(θ) + y*cos(θ)
        rx = dx * cos_r - dy * sin_r + center_x
        ry = dx * sin_r + dy * cos_r + center_y
        rotated_corners.append((rx, ry))

    # 3. 绘制旋转后的矩形
    rotated_polygon = patches.Polygon(
        rotated_corners,
        linewidth=3, edgecolor='red', facecolor='lightcoral', alpha=0.5,
        label=f'旋转后矩形（{rotation_deg}°）'
    )
    ax.add_patch(rotated_polygon)

    # 4. 标注四个角点
    corner_labels = ['左上', '右上', '右下', '左下']
    for i, (x, y) in enumerate(rotated_corners):
        ax.plot(x, y, 'ro', markersize=10)
        ax.annotate(
            f'{corner_labels[i]}\n({x:.0f}, {y:.0f})',
            (x, y), xytext=(10, 10), textcoords='offset points',
            fontsize=9, color='darkred',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.7)
        )

    # 5. 计算包围盒
    xs = [c[0] for c in rotated_corners]
    ys = [c[1] for c in rotated_corners]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    # 6. 绘制包围盒
    bbox_rect = patches.Rectangle(
        (min_x, min_y),
        max_x - min_x, max_y - min_y,
        linewidth=3, edgecolor='green', facecolor='none',
        linestyle='--', label='包围盒（Bounding Box）'
    )
    ax.add_patch(bbox_rect)

    # 7. 标注包围盒边界
    ax.axvline(min_x, color='green', linestyle=':', alpha=0.5)
    ax.axvline(max_x, color='green', linestyle=':', alpha=0.5)
    ax.axhline(min_y, color='green', linestyle=':', alpha=0.5)
    ax.axhline(max_y, color='green', linestyle=':', alpha=0.5)

    ax.text(min_x, min_y - 20, f'min_x={min_x:.0f}', ha='center', fontsize=10, color='green', weight='bold')
    ax.text(max_x, min_y - 20, f'max_x={max_x:.0f}', ha='center', fontsize=10, color='green', weight='bold')
    ax.text(min_x - 30, min_y, f'min_y={min_y:.0f}', ha='right', fontsize=10, color='green', weight='bold')
    ax.text(min_x - 30, max_y, f'max_y={max_y:.0f}', ha='right', fontsize=10, color='green', weight='bold')

    # 8. 绘制中心点
    ax.plot(center_x, center_y, 'ko', markersize=12, label='精灵中心')
    ax.annotate(
        f'中心\n({center_x}, {center_y})',
        (center_x, center_y), xytext=(20, -30), textcoords='offset points',
        fontsize=10, color='black', weight='bold',
        arrowprops=dict(arrowstyle='->', color='black', lw=2)
    )

    # 设置图形属性
    ax.set_xlim(200, 600)
    ax.set_ylim(100, 500)
    ax.set_aspect('equal')
    ax.grid(True, alpha=0.3)
    ax.legend(loc='upper right', fontsize=11)
    ax.set_xlabel('X 坐标（像素）', fontsize=12)
    ax.set_ylabel('Y 坐标（像素）', fontsize=12)
    ax.set_title(
        f'精灵旋转和包围盒计算可视化\n'
        f'原始大小: {width}×{height} | 缩放: {scale}x | 旋转: {rotation_deg}°',
        fontsize=14, weight='bold'
    )

    # 添加说明文字
    explanation = (
        "计算步骤：\n"
        "1. 蓝色矩形：缩放后的原始矩形\n"
        "2. 红色矩形：旋转后的实际精灵\n"
        "3. 绿色虚线框：包围盒（最小矩形）\n"
        "4. 只需遍历绿色框内的像素！"
    )
    ax.text(
        0.02, 0.98, explanation,
        transform=ax.transAxes,
        fontsize=10,
        verticalalignment='top',
        bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8)
    )

    plt.tight_layout()
    plt.savefig('bounding_box_visualization.png', dpi=150, bbox_inches='tight')
    print("Visualization saved to: bounding_box_visualization.png")
    plt.show()


if __name__ == '__main__':
    # 示例：200×100的精灵，旋转30度，放大1.5倍
    sprite_rotation(width=200, height=100, rotation_deg=30, scale=1.5)

    print("\n" + "="*60)
    print("旋转公式说明：")
    print("="*60)
    print("对于角点 (dx, dy) 相对于中心的偏移：")
    print("  旋转后的 x' = dx * cos(θ) - dy * sin(θ) + center_x")
    print("  旋转后的 y' = dx * sin(θ) + dy * cos(θ) + center_y")
    print("\n包围盒计算：")
    print("  min_x = min(所有旋转后角点的 x 坐标)")
    print("  max_x = max(所有旋转后角点的 x 坐标)")
    print("  min_y = min(所有旋转后角点的 y 坐标)")
    print("  max_y = max(所有旋转后角点的 y 坐标)")
    print("="*60)
