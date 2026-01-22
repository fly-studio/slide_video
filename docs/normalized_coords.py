"""
可视化归一化坐标系统
"""
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

# 配置中文字体
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False


def normalized_coordinates():
    """
    可视化归一化坐标的概念和应用
    """
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    fig.suptitle('归一化坐标系统可视化', fontsize=16, weight='bold')

    # ========== 示例1：原始像素坐标 ==========
    ax1 = axes[0, 0]
    width, height = 200, 100

    # 绘制网格
    for i in range(0, width+1, 50):
        ax1.axvline(i, color='gray', alpha=0.3, linewidth=0.5)
    for j in range(0, height+1, 25):
        ax1.axhline(j, color='gray', alpha=0.3, linewidth=0.5)

    # 标注关键点
    ax1.plot(0, 0, 'ro', markersize=10, label='原点 (0, 0)')
    ax1.plot(width, height, 'bo', markersize=10, label=f'右下角 ({width}, {height})')
    ax1.plot(width//2, height//2, 'go', markersize=10, label=f'中心 ({width//2}, {height//2})')

    ax1.set_xlim(-10, width+10)
    ax1.set_ylim(-10, height+10)
    ax1.set_xlabel('X 像素坐标')
    ax1.set_ylabel('Y 像素坐标')
    ax1.set_title('原始像素坐标系\n(分辨率相关)', fontsize=12, weight='bold')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    ax1.set_aspect('equal')

    # ========== 示例2：归一化坐标 ==========
    ax2 = axes[0, 1]

    # 创建归一化坐标网格
    cx_ratio, cy_ratio = 0.5, 0.5
    cx, cy = cx_ratio * width, cy_ratio * height
    scale = min(width, height)

    xx, yy = np.meshgrid(np.arange(width), np.arange(height))
    dx = (xx - cx) / scale
    dy = (yy - cy) / scale

    # 绘制归一化坐标的热力图
    im = ax2.imshow(np.sqrt(dx**2 + dy**2), extent=[0, width, height, 0],
                    cmap='viridis', alpha=0.6)
    plt.colorbar(im, ax=ax2, label='距离中心的归一化距离')

    # 标注关键点
    ax2.plot(cx, cy, 'ro', markersize=10, label='中心 (0, 0) 归一化')
    ax2.plot(0, 0, 'wo', markersize=8, label=f'左上角 ({dx[0,0]:.2f}, {dy[0,0]:.2f})')
    ax2.plot(width, height, 'wo', markersize=8, label=f'右下角 ({dx[-1,-1]:.2f}, {dy[-1,-1]:.2f})')

    ax2.set_xlim(0, width)
    ax2.set_ylim(height, 0)
    ax2.set_xlabel('X 像素坐标')
    ax2.set_ylabel('Y 像素坐标')
    ax2.set_title('归一化坐标系\n(距离中心的归一化距离)', fontsize=12, weight='bold')
    ax2.legend()
    ax2.set_aspect('equal')

    # ========== 示例3：圆形遮罩（归一化半径） ==========
    ax3 = axes[0, 2]

    # 不同半径的圆形
    radii = [0.3, 0.5, 0.707]  # 0.707 ≈ sqrt(2)/2
    colors = ['red', 'green', 'blue']
    labels = ['r=0.3', 'r=0.5', 'r=0.707 (覆盖对角线)']

    for radius, color, label in zip(radii, colors, labels):
        mask = (dx**2 + dy**2) <= radius**2
        ax3.contour(xx, yy, mask, levels=[0.5], colors=color, linewidths=2)
        # 添加图例（使用线条）
        ax3.plot([], [], color=color, linewidth=2, label=label)

    ax3.plot(cx, cy, 'ko', markersize=8, label='中心')
    ax3.set_xlim(0, width)
    ax3.set_ylim(height, 0)
    ax3.set_xlabel('X 像素坐标')
    ax3.set_ylabel('Y 像素坐标')
    ax3.set_title('圆形遮罩（归一化半径）\n统一参数，自动适配', fontsize=12, weight='bold')
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    ax3.set_aspect('equal')

    # ========== 示例4：不同分辨率对比（100×100） ==========
    ax4 = axes[1, 0]
    size1 = 100
    xx1, yy1 = np.meshgrid(np.arange(size1), np.arange(size1))
    cx1, cy1 = size1 * 0.5, size1 * 0.5
    scale1 = min(size1, size1)
    dx1 = (xx1 - cx1) / scale1
    dy1 = (yy1 - cy1) / scale1

    radius_norm = 0.5
    mask1 = (dx1**2 + dy1**2) <= radius_norm**2
    ax4.imshow(mask1, extent=[0, size1, size1, 0], cmap='gray')
    ax4.set_title(f'100×100 图像\n归一化半径 r={radius_norm}', fontsize=12, weight='bold')
    ax4.set_xlabel('X 像素')
    ax4.set_ylabel('Y 像素')
    ax4.set_aspect('equal')

    # ========== 示例5：不同分辨率对比（200×100） ==========
    ax5 = axes[1, 1]
    size2_w, size2_h = 200, 100
    xx2, yy2 = np.meshgrid(np.arange(size2_w), np.arange(size2_h))
    cx2, cy2 = size2_w * 0.5, size2_h * 0.5
    scale2 = min(size2_w, size2_h)
    dx2 = (xx2 - cx2) / scale2
    dy2 = (yy2 - cy2) / scale2

    mask2 = (dx2**2 + dy2**2) <= radius_norm**2
    ax5.imshow(mask2, extent=[0, size2_w, size2_h, 0], cmap='gray')
    ax5.set_title(f'200×100 图像\n归一化半径 r={radius_norm}（相同参数）', fontsize=12, weight='bold')
    ax5.set_xlabel('X 像素')
    ax5.set_ylabel('Y 像素')
    ax5.set_aspect('equal')

    # ========== 示例6：不同分辨率对比（300×300） ==========
    ax6 = axes[1, 2]
    size3 = 300
    xx3, yy3 = np.meshgrid(np.arange(size3), np.arange(size3))
    cx3, cy3 = size3 * 0.5, size3 * 0.5
    scale3 = min(size3, size3)
    dx3 = (xx3 - cx3) / scale3
    dy3 = (yy3 - cy3) / scale3

    mask3 = (dx3**2 + dy3**2) <= radius_norm**2
    ax6.imshow(mask3, extent=[0, size3, size3, 0], cmap='gray')
    ax6.set_title(f'300×300 图像\n归一化半径 r={radius_norm}（相同参数）', fontsize=12, weight='bold')
    ax6.set_xlabel('X 像素')
    ax6.set_ylabel('Y 像素')
    ax6.set_aspect('equal')

    # 添加总体说明
    fig.text(0.5, 0.02,
             '关键优势：使用归一化坐标后，相同的半径参数（如 r=0.5）在不同分辨率下产生视觉一致的效果',
             ha='center', fontsize=11, style='italic',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

    plt.tight_layout(rect=[0, 0.03, 1, 0.98])
    plt.savefig('normalized_coords_visualization.png', dpi=150, bbox_inches='tight')
    print("Visualization saved to: normalized_coords_visualization.png")
    plt.show()


if __name__ == '__main__':
    normalized_coordinates()

    print("\n" + "="*70)
    print("归一化坐标的核心优势")
    print("="*70)
    print("1. 分辨率无关性：")
    print("   - 相同参数在不同分辨率下产生一致的视觉效果")
    print("   - 无需为每个分辨率重新计算参数")
    print()
    print("2. 数学简化：")
    print("   - 圆形：sqrt(dx² + dy²) <= radius")
    print("   - 菱形：|dx| + |dy| <= radius")
    print("   - 统一的数学公式，易于实现和理解")
    print()
    print("3. 应用场景：")
    print("   - 转场效果（圆形擦除、菱形展开）")
    print("   - 遮罩动画（从中心扩散）")
    print("   - 滤镜效果（径向模糊、晕影）")
    print("   - 粒子系统（极坐标计算）")
    print("="*70)
