import numpy as np
import matplotlib.pyplot as plt

# 设置中文字体（Mac/Win通用）
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'Microsoft YaHei'] 
plt.rcParams['axes.unicode_minus'] = False

# 1. 生成时间轴和原始高斯脉冲
t = np.linspace(-5, 5, 1000)
t0 = 0          # 峰值位置
sigma_in = 0.8  # 初始脉冲标准差（宽度小）

# 原始脉冲（展宽前）
pulse_in = np.exp(- (t - t0)**2 / (2 * sigma_in**2))

# 2. 模拟展宽后的脉冲（假设色散或低通滤波导致标准差变大）
sigma_out = 1.8  # 展宽后的标准差（宽度大）
pulse_out = np.exp(- (t - t0)**2 / (2 * sigma_out**2))

# 3. 绘制示意图
plt.figure(figsize=(10, 5))

# 绘制输入脉冲（窄，蓝色）
plt.plot(t, pulse_in, 'b-', linewidth=2.5, label='输入脉冲 (展宽前)')
# 绘制输出脉冲（宽，红色虚线）
plt.plot(t, pulse_out, 'r--', linewidth=2.5, label='输出脉冲 (展宽后)')

# 标记半高全宽（FWHM）示意（用箭头或垂直线简单表示，这里用水平线段示意）
# 计算原始脉冲的半高位置
half_max_in = 0.5
idx_half_left_in = np.where(pulse_in >= half_max_in)[0][0]
idx_half_right_in = np.where(pulse_in >= half_max_in)[0][-1]
fwhm_in = t[idx_half_right_in] - t[idx_half_left_in]

# 计算展宽脉冲的半高位置
idx_half_left_out = np.where(pulse_out >= half_max_in)[0][0]
idx_half_right_out = np.where(pulse_out >= half_max_in)[0][-1]
fwhm_out = t[idx_half_right_out] - t[idx_half_left_out]

# 添加标注和箭头，说明脉宽变宽
plt.annotate('', xy=(t[idx_half_right_out], 0.55), xytext=(t[idx_half_left_out], 0.55),
             arrowprops=dict(arrowstyle='<->', color='red', lw=2))
plt.text(0, 0.6, f'展宽后 FWHM ≈ {fwhm_out:.2f}', ha='center', color='red', fontsize=11)

plt.annotate('', xy=(t[idx_half_right_in], 0.45), xytext=(t[idx_half_left_in], 0.45),
             arrowprops=dict(arrowstyle='<->', color='blue', lw=2))
plt.text(0, 0.35, f'初始 FWHM ≈ {fwhm_in:.2f}', ha='center', color='blue', fontsize=11)

# 增加网格和图例
plt.xlabel('时间 (相对单位)', fontsize=12)
plt.ylabel('归一化幅度', fontsize=12)
plt.title('脉冲展宽 (Pulse Broadening) 对比示意图', fontsize=14)
plt.ylim(0, 1.1)
plt.legend(loc='upper right')
plt.grid(True, linestyle=':', alpha=0.7)
plt.tight_layout()
plt.show()