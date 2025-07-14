<?php
// 读取JSON文件
$jsonFile = 'Output/output.json';

// 读取JSON数据
if (file_exists($jsonFile)) {
    $jsonData = json_decode(file_get_contents($jsonFile), true);
    $lastCheck = $jsonData['check_time'] ?? '未知';
    $skuName = $jsonData['sku_name'] ?? '未知';
    $status = $jsonData['status'] ?? '未知';
    $consumedUnits = $jsonData['consumed_units'] ?? 0;
    $totalUnits = $jsonData['total_units'] ?? 0;
    $licensePercentage = ($totalUnits > 0) ? round(($consumedUnits / $totalUnits) * 100) : 0;

    // 获取到期信息
    $expiryInfo = $jsonData['expiry_info'] ?? [];
    $expiryDate = $expiryInfo['expiry_date'] ?? '未知';
    $daysLeft = $expiryInfo['days_left'] ?? '未知';
    $expiryStatus = $expiryInfo['status'] ?? '未知';

    // 根据剩余天数确定状态类型
    if ($daysLeft !== '未知') {
        if ($daysLeft <= 7) {
            $daysLeftClass = 'danger';
            $daysLeftIcon = 'exclamation-triangle';
        } elseif ($daysLeft <= 30) {
            $daysLeftClass = 'warning';
            $daysLeftIcon = 'exclamation-circle';
        } else {
            $daysLeftClass = 'success';
            $daysLeftIcon = 'check-circle';
        }
    } else {
        $daysLeftClass = 'secondary';
        $daysLeftIcon = 'question-circle';
    }

    // 根据订阅状态确定颜色
    if ($status === '活跃') {
        $statusClass = 'success';
        $statusIcon = 'check-circle';
    } else {
        $statusClass = 'danger';
        $statusIcon = 'times-circle';
    }

    // 根据许可证使用百分比确定颜色
    if ($licensePercentage < 50) {
        $licenseClass = 'success';
    } elseif ($licensePercentage < 80) {
        $licenseClass = 'warning';
    } else {
        $licenseClass = 'danger';
    }
    $error = "数据两小时更新一次，如果有订阅状态或到期时间异常，请立刻备份文件。";
} else {
    $error = "无法找到数据文件，可能数据更新出现问题，数据两小时更新一次，请稍后再试。";
}
?>
<!DOCTYPE html>
<html lang="zh-CN">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>微软E5订阅状态检测</title>
    <!-- Bootstrap 5 CSS -->
    <link href="https://s4.zstatic.net/ajax/libs/twitter-bootstrap/5.3.7/css/bootstrap.min.css" rel="stylesheet">
    <!-- Font Awesome -->
    <link rel="stylesheet" href="https://s4.zstatic.net/ajax/libs/font-awesome/6.7.2/css/all.min.css">
    <!-- Chart.js -->
    <script src="https://lf6-cdn-tos.bytecdntp.com/cdn/expire-1-M/Chart.js/3.7.1/chart.min.js"></script>
    <script async src="//busuanzi.ibruce.info/busuanzi/2.3/busuanzi.pure.mini.js"></script>
    <style>
        :root {
            --primary-color: #0078d4;
            --secondary-color: #50e6ff;
            --success-color: #107c10;
            --warning-color: #ff8c00;
            --danger-color: #d13438;
            --light-bg: #f9f9f9;
            --dark-bg: #1e1e1e;
            --light-card: #ffffff;
            --dark-card: #252526;
            --light-text: #323130;
            --dark-text: #f0f0f0;
        }

        body {
            transition: background-color 0.3s, color 0.3s;
            padding-top: 20px;
            padding-bottom: 20px;
            background-color: var(--light-bg);
            color: var(--light-text);
        }

        body.dark-mode {
            background-color: var(--dark-bg);
            color: var(--dark-text);
        }

        .card {
            transition: background-color 0.3s, color 0.3s, box-shadow 0.3s;
            border: none;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            margin-bottom: 20px;
            background-color: var(--light-card);
            overflow: hidden;
        }

        body.dark-mode .card {
            background-color: var(--dark-card);
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        }

        /* 确保卡片内所有文本元素在深色模式下可见 */
        body.dark-mode .card a:not(.btn):not(.badge) {
            color: var(--secondary-color);
        }

        body.dark-mode .alert-warning {
            background-color: rgba(255, 193, 7, 0.2);
            color: #f8d7a4;
        }

        .card-header {
            border-bottom: 1px solid rgba(0, 0, 0, 0.1);
            font-weight: 600;
            padding: 15px 20px;
        }

        body.dark-mode .card-header {
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            color: var(--dark-text);
        }

        .card-body {
            padding: 20px;
        }

        .status-icon {
            font-size: 3rem;
            margin-right: 15px;
        }

        .info-value {
            font-size: 1.5rem;
            font-weight: 600;
        }

        body.dark-mode .info-value {
            color: var(--dark-text);
        }

        .info-label {
            color: #666;
            font-size: 0.9rem;
        }

        body.dark-mode .info-label {
            color: #aaa;
        }

        .progress {
            height: 10px;
            margin-top: 15px;
            border-radius: 5px;
        }

        .theme-switch {
            cursor: pointer;
            padding: 5px 10px;
            border-radius: 20px;
            display: inline-flex;
            align-items: center;
            border: 1px solid #ccc;
            transition: all 0.3s;
        }

        body.dark-mode .theme-switch {
            border-color: #555;
        }

        .reset-button {
            cursor: pointer;
            padding: 5px 10px;
            border-radius: 20px;
            display: none;
            align-items: center;
            border: 1px solid #ccc;
            margin-left: 10px;
            font-size: 0.9rem;
            transition: all 0.3s;
            color: #666;
        }

        body.dark-mode .reset-button {
            border-color: #555;
            color: #aaa;
        }

        .reset-button:hover {
            background-color: rgba(0, 120, 212, 0.1);
        }

        body.dark-mode .reset-button:hover {
            background-color: rgba(80, 230, 255, 0.1);
        }

        .page-header {
            border-bottom: 1px solid rgba(0, 0, 0, 0.1);
            margin-bottom: 30px;
            padding-bottom: 20px;
        }

        body.dark-mode .page-header {
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }

        .license-chart-container {
            height: 250px;
        }

        .contact-info {
            margin-top: 25px;
            padding: 15px;
            border-radius: 10px;
            background-color: rgba(0, 120, 212, 0.1);
            transition: all 0.3s;
        }

        body.dark-mode .contact-info {
            background-color: rgba(80, 230, 255, 0.1);
        }

        .contact-info:hover {
            transform: translateY(-3px);
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
        }

        body.dark-mode .contact-info:hover {
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.3);
        }

        .contact-icon {
            font-size: 2rem;
            color: var(--primary-color);
            margin-right: 15px;
        }

        .footer {
            margin-top: 30px;
            padding: 25px 0 20px;
            border-top: 1px solid rgba(0, 0, 0, 0.1);
            text-align: center;
            font-size: 0.9rem;
            color: #666;
            position: relative;
            overflow: hidden;
        }

        .footer::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 1px;
            background: linear-gradient(90deg, transparent, var(--primary-color), transparent);
            animation: shimmer 4s infinite;
        }

        @keyframes shimmer {
            0% {
                transform: translateX(-100%);
            }

            100% {
                transform: translateX(100%);
            }
        }

        body.dark-mode .footer {
            border-top: 1px solid rgba(255, 255, 255, 0.1);
            color: #aaa;
        }

        .footer-content {
            display: flex;
            flex-wrap: wrap;
            justify-content: center;
            align-items: center;
            gap: 12px;
            position: relative;
            z-index: 1;
        }

        .footer-item {
            display: inline-flex;
            align-items: center;
            padding: 5px 10px;
            border-radius: 20px;
            background-color: rgba(0, 120, 212, 0.08);
            transition: all 0.3s;
            position: relative;
        }

        body.dark-mode .footer-item {
            background-color: rgba(80, 230, 255, 0.08);
        }

        .footer-item:hover {
            transform: translateY(-2px);
            background-color: rgba(0, 120, 212, 0.15);
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
        }

        .footer-item:hover::after {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            border-radius: 20px;
            border: 1px solid var(--primary-color);
            animation: pulse 1.5s infinite;
        }

        @keyframes pulse {
            0% {
                transform: scale(1);
                opacity: 1;
            }

            100% {
                transform: scale(1.2);
                opacity: 0;
            }
        }

        body.dark-mode .footer-item:hover {
            background-color: rgba(80, 230, 255, 0.15);
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3);
        }

        .footer-item i {
            margin-right: 6px;
            color: var(--primary-color);
        }

        .footer-item a {
            color: inherit;
            text-decoration: none;
            transition: color 0.2s;
        }

        .footer-item a:hover {
            color: var(--primary-color);
        }

        body.dark-mode .footer-item a:hover {
            color: var(--secondary-color);
        }

        .copyright {
            width: 100%;
            margin-top: 15px;
            opacity: 0.8;
            font-size: 0.85rem;
        }

        .auto-mode-info {
            font-size: 0.8rem;
            margin-top: 5px;
            opacity: 0.8;
        }

        .theme-controls {
            display: flex;
            flex-direction: column;
            align-items: flex-end;
        }

        .theme-buttons {
            display: flex;
            align-items: center;
        }
    </style>
</head>

<body class="<?php echo isset($_COOKIE['darkMode']) && $_COOKIE['darkMode'] === 'true' ? 'dark-mode' : ''; ?>">
    <div class="container">
        <!-- 页面头部 -->
        <div class="row page-header align-items-center">
            <div class="col-md-8">
                <h1><i class="fab fa-microsoft me-2 text-primary"></i>微软E5订阅状态检测</h1>
            </div>
            <div class="col-md-4 text-end">
                <div class="theme-controls">
                    <div class="theme-buttons">
                        <span class="theme-switch" id="themeSwitch">
                            <i class="fas fa-moon me-2"></i>
                            <span>切换主题</span>
                        </span>
                        <span class="reset-button" id="resetTheme">
                            <i class="fas fa-rotate-right me-2"></i>
                            <span>重置主题</span>
                        </span>
                    </div>
                    <div class="auto-mode-info" id="autoModeInfo"></div>
                </div>
            </div>
        </div>

        <div class="alert alert-warning" role="alert">
            <i class="fas fa-exclamation-triangle me-2"></i> <?php echo $error; ?>
        </div>
        <!-- 主要内容 -->
        <div class="row">
            <!-- 订阅状态卡片 -->
            <div class="col-md-4">
                <div class="card h-100">
                    <div class="card-header bg-transparent">
                        <i class="fas fa-info-circle me-2"></i> 订阅状态
                    </div>
                    <div class="card-body">
                        <div class="d-flex align-items-center mb-3">
                            <i class="fas fa-<?php echo $statusIcon; ?> status-icon text-<?php echo $statusClass; ?>"></i>
                            <div>
                                <div class="info-value"><?php echo $status; ?></div>
                                <div class="info-label">当前状态</div>
                            </div>
                        </div>
                        <div class="mt-4">
                            <div class="info-label">订阅类型</div>
                            <div class="info-value"><?php echo $skuName; ?></div>
                        </div>
                        <div class="mt-4">
                            <div class="info-label">上次检测时间</div>
                            <div class="info-value" style="font-size: 1.1rem;"><?php echo $lastCheck; ?></div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- 许可证使用卡片 -->
            <div class="col-md-4">
                <div class="card h-100">
                    <div class="card-header bg-transparent">
                        <i class="fas fa-id-card me-2"></i> 许可证使用
                    </div>
                    <div class="card-body">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <div class="info-value"><?php echo $consumedUnits; ?> / <?php echo $totalUnits; ?></div>
                            <div class="badge bg-<?php echo $licenseClass; ?>"><?php echo $licensePercentage; ?>%</div>
                        </div>
                        <div class="info-label mb-2">已使用许可证 / 总许可证</div>
                        <div class="progress">
                            <div class="progress-bar bg-<?php echo $licenseClass; ?>" role="progressbar" style="width: <?php echo $licensePercentage; ?>%" aria-valuenow="<?php echo $licensePercentage; ?>" aria-valuemin="0" aria-valuemax="100"></div>
                        </div>

                        <div class="license-chart-container mt-4">
                            <canvas id="licenseChart"></canvas>
                        </div>
                    </div>
                </div>
            </div>

            <!-- 到期信息卡片 -->
            <div class="col-md-4">
                <div class="card h-100">
                    <div class="card-header bg-transparent">
                        <i class="fas fa-calendar-alt me-2"></i> 到期信息
                    </div>
                    <div class="card-body">
                        <div class="d-flex align-items-center mb-3">
                            <i class="fas fa-<?php echo $daysLeftIcon; ?> status-icon text-<?php echo $daysLeftClass; ?>"></i>
                            <div>
                                <div class="info-value"><?php echo $daysLeft; ?> 天</div>
                                <div class="info-label">剩余时间</div>
                            </div>
                        </div>
                        <div class="mt-4">
                            <div class="info-label">到期日期</div>
                            <div class="info-value"><?php echo $expiryDate; ?></div>
                        </div>
                        <div class="mt-4">
                            <div class="info-label">状态</div>
                            <div class="info-value">
                                <span class="badge bg-<?php echo $daysLeftClass; ?>"><?php echo $expiryStatus; ?></span>
                            </div>
                        </div>

                        <!-- 联系信息 -->
                        <div class="contact-info mt-4">
                            <div class="d-flex align-items-center">
                                <i class="fas fa-envelope contact-icon"></i>
                                <div>
                                    <div class="info-label">点击联系我</div>
                                    <a href="mailto:nushen666@qq.com" class="info-value" style="font-size: 1.1rem; text-decoration: none;">
                                        nushen666@qq.com
                                    </a>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- 页脚 -->
        <div class="footer">
            <div class="footer-content">
                <div class="footer-item">
                    <i class="fas fa-chart-line"></i>
                    <span id="busuanzi_container_site_pv">访问量 <span id="busuanzi_value_site_pv"></span></span>
                </div>
                <div class="footer-item">
                    <i class="fas fa-heart"></i> Cursor真好用(bushi)
                </div>
                <div class="footer-item" onclick="window.location.href='mailto:nushen666@qq.com';" style="cursor: pointer;">
                    <i class="fas fa-envelope"></i> <a href="mailto:nushen666@qq.com">nushen666@qq.com</a>
                </div>
                <div class="footer-item" onclick="window.open('<?php echo $jsonFile; ?>', '_blank');" style="cursor: pointer;">
                    <i class="fas fa-file-code"></i> <a href="<?php echo $jsonFile; ?>" target="_blank">查看JSON数据</a>
                </div>
                <div class="footer-item" onclick="window.open('https://github.com/nushena/E5SubWatcher', '_blank');" style="cursor: pointer;">
                    <i class="fab fa-github"></i> <a href="https://github.com/nushena/E5SubWatcher" target="_blank">GitHub</a>
                </div>
            </div>
            <div class="copyright">
                &copy; <span id="current-year"><?php echo date('Y'); ?></span> 微软E5检测系统
            </div>
        </div>
    </div>

    <!-- Bootstrap JS Bundle -->
    <script src="https://s4.zstatic.net/ajax/libs/twitter-bootstrap/5.3.7/js/bootstrap.bundle.min.js"></script>

    <script>
        // 主题控制相关代码
        document.addEventListener('DOMContentLoaded', function() {
            // 获取DOM元素
            const themeSwitch = document.getElementById('themeSwitch');
            const resetBtn = document.getElementById('resetTheme');
            const infoDisplay = document.getElementById('autoModeInfo');
            const body = document.body;

            // 主题状态
            let manualMode = false;

            // 检查当前系统是否处于深色模式
            const prefersDark = () => window.matchMedia('(prefers-color-scheme: dark)').matches;

            // 检查当前时间是否在夜间时段(20:00-7:00)
            const isNightTime = () => {
                const now = new Date();
                const hour = now.getHours();
                const isNight = hour >= 20 || hour < 7;

                // 输出调试信息
                console.log('时间检测', {
                    当前时间: now.toLocaleTimeString(),
                    小时值: hour,
                    是否夜间: isNight
                });

                return isNight;
            };

            // 获取当前应该使用的主题模式
            const getPreferredTheme = () => {
                // 只根据时间判断，不考虑系统偏好
                return isNightTime();
            };

            // 设置Cookie
            const setCookie = (name, value, days = 365) => {
                const date = new Date();
                date.setTime(date.getTime() + (days * 24 * 60 * 60 * 1000));
                const expires = `; expires=${date.toUTCString()}`;
                document.cookie = `${name}=${value}${expires}; path=/`;
            };

            // 获取Cookie值
            const getCookie = (name) => {
                const cookies = document.cookie.split(';');
                for (let cookie of cookies) {
                    cookie = cookie.trim();
                    if (cookie.startsWith(name + '=')) {
                        return cookie.substring(name.length + 1);
                    }
                }
                return null;
            };

            // 删除Cookie
            const deleteCookie = (name) => {
                document.cookie = `${name}=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT`;
            };

            // 更新主题切换按钮图标
            const updateIcon = (isDark) => {
                const icon = themeSwitch.querySelector('i');
                if (isDark) {
                    icon.className = 'fas fa-sun me-2';
                } else {
                    icon.className = 'fas fa-moon me-2';
                }
            };

            // 更新图表颜色
            const updateChartColors = () => {
                // 确保图表存在且已正确初始化
                if (window.licenseChart && window.licenseChart.options &&
                    window.licenseChart.options.plugins &&
                    window.licenseChart.options.plugins.legend) {

                    const isDark = body.classList.contains('dark-mode');
                    const textColor = isDark ? '#f0f0f0' : '#323130';

                    window.licenseChart.options.plugins.legend.labels.color = textColor;
                    window.licenseChart.update();

                    console.log('图表颜色已更新', {
                        深色模式: isDark
                    });
                }
            };

            // 应用主题
            const applyTheme = (isDark) => {
                // 应用或移除深色模式类
                if (isDark) {
                    body.classList.add('dark-mode');
                } else {
                    body.classList.remove('dark-mode');
                }

                // 更新图标
                updateIcon(isDark);

                // 延迟更新图表颜色，确保在图表初始化后执行
                setTimeout(() => {
                    updateChartColors();
                }, 100); // 短暂延迟，确保在图表初始化后执行
            };

            // 更新状态信息显示
            const updateStatusInfo = () => {
                if (!infoDisplay) return;

                // 显示/隐藏重置按钮
                if (resetBtn) {
                    resetBtn.style.display = manualMode ? 'inline-flex' : 'none';
                }

                if (manualMode) {
                    infoDisplay.textContent = "手动模式已激活";
                    return;
                }

                const night = isNightTime();
                // 简化状态信息显示逻辑
                if (night) {
                    infoDisplay.textContent = "自动模式：夜间(20:00-7:00)";
                } else {
                    infoDisplay.textContent = "自动模式：白天(7:00-20:00)";
                }
            };

            // 更新主题
            const updateTheme = () => {
                // 如果是手动模式，不自动更新
                if (manualMode) return;

                const isDark = getPreferredTheme();
                applyTheme(isDark);
                updateStatusInfo();
            };

            // 初始化主题
            const initTheme = () => {
                const darkModeCookie = getCookie('darkMode');

                // 检查是否有用户设置的偏好
                if (darkModeCookie !== null) {
                    manualMode = true;
                    const isDark = darkModeCookie === 'true';
                    applyTheme(isDark);
                    console.log('加载手动模式', {
                        当前主题: isDark ? '深色' : '浅色'
                    });
                } else {
                    // 使用自动模式
                    manualMode = false;
                    const isDark = isNightTime();
                    applyTheme(isDark);
                    console.log('加载自动模式', {
                        时间: new Date().toLocaleTimeString(),
                        是否夜间模式: isDark,
                        当前小时: new Date().getHours()
                    });
                }

                updateStatusInfo();
            };

            // 重置为自动模式
            const resetToAuto = () => {
                // 先删除Cookie
                deleteCookie('darkMode');

                // 重置手动模式标志
                manualMode = false;

                // 立即强制重新计算并应用主题
                const isDark = isNightTime();
                applyTheme(isDark);

                // 更新状态信息
                updateStatusInfo();

                // 输出调试信息到控制台
                console.log('重置为自动模式', {
                    时间: new Date().toLocaleTimeString(),
                    是否夜间模式: isDark,
                    当前小时: new Date().getHours()
                });
            };

            // 监听主题切换按钮点击
            if (themeSwitch) {
                themeSwitch.addEventListener('click', () => {
                    const isDark = !body.classList.contains('dark-mode');
                    applyTheme(isDark);

                    // 设置手动模式
                    manualMode = true;
                    setCookie('darkMode', isDark);

                    // 输出调试信息
                    console.log('手动切换主题', {
                        新主题: isDark ? '深色' : '浅色',
                        时间: new Date().toLocaleTimeString()
                    });

                    updateStatusInfo();
                });
            }

            // 监听重置按钮点击
            if (resetBtn) {
                resetBtn.addEventListener('click', resetToAuto);
            }

            // 监听系统主题变化
            window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
                if (!manualMode) {
                    updateTheme();
                }
            });

            // 初始化主题
            initTheme();

            // 每10分钟检查一次时间变化（时间段判断）
            setInterval(updateTheme, 600000);
        });

        // 确保在DOM完全加载后初始化图表
        document.addEventListener('DOMContentLoaded', function() {
            // 初始化图表
            console.log('DOM完全加载，开始初始化图表');
            setTimeout(initLicenseChart, 200); // 给其他DOM操作一些时间

            // 为页脚年份添加动画效果
            const yearElement = document.getElementById('current-year');
            if (yearElement) {
                const currentYear = new Date().getFullYear();
                const yearAnimation = setInterval(() => {
                    const randomYear = Math.floor(Math.random() * 30) + (currentYear - 20);
                    yearElement.textContent = randomYear;
                }, 50);

                setTimeout(() => {
                    clearInterval(yearAnimation);
                    yearElement.textContent = currentYear;
                }, 1000);
            }
        });

        // 初始化许可证图表
        function initLicenseChart() {
            try {
                <?php if (isset($consumedUnits) && isset($totalUnits)): ?>
                    console.log('准备初始化图表...');

                    const ctx = document.getElementById('licenseChart');
                    if (!ctx) {
                        console.error('未找到图表容器元素');
                        return;
                    }

                    console.log('找到图表容器，开始创建图表实例');
                    const isDarkMode = document.body.classList.contains('dark-mode');
                    const textColor = isDarkMode ? '#f0f0f0' : '#323130';
                    const gridColor = isDarkMode ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)';
                    const unusedColor = isDarkMode ? '#555555' : '#dddddd';

                    const licenseChart = new Chart(ctx, {
                        type: 'doughnut',
                        data: {
                            labels: ['已使用', '未使用'],
                            datasets: [{
                                data: [<?php echo $consumedUnits; ?>, <?php echo $totalUnits - $consumedUnits; ?>],
                                backgroundColor: [
                                    '#0078d4',
                                    unusedColor
                                ],
                                borderWidth: 0
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            cutout: '70%',
                            plugins: {
                                legend: {
                                    position: 'bottom',
                                    labels: {
                                        color: textColor
                                    }
                                },
                                tooltip: {
                                    callbacks: {
                                        label: function(context) {
                                            return context.label + ': ' + context.raw + ' (' + Math.round((context.raw / <?php echo $totalUnits; ?> * 100)) + '%)';
                                        }
                                    }
                                }
                            }
                        }
                    });

                    // 保存图表实例到全局
                    window.licenseChart = licenseChart;
                    console.log('图表实例已成功创建并存储到全局变量');
                <?php endif; ?>
            } catch (error) {
                console.error('图表初始化失败:', error);
            }
        }
    </script>
</body>

</html>