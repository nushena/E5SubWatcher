# 微软 E5 订阅状态检测工具

![版本](https://img.shields.io/badge/版本-2.0-blue)
![Python](https://img.shields.io/badge/Python-3.6+-green)
![PHP](https://img.shields.io/badge/PHP-7.0+-orange)
![许可证](https://img.shields.io/badge/许可证-MIT-yellow)

## 项目简介

微软 E5 订阅状态检测工具是一个用于自动监控 Microsoft 365 E5 订阅状态的解决方案。通过 Microsoft Graph API 获取订阅信息，包括激活状态、许可证使用情况以及到期时间，并通过精美的网页界面直观地展示这些数据。

### 主要功能

- 👀 **实时监控** - 自动检查 E5 订阅状态
- 📊 **数据可视化** - 通过网页界面直观展示订阅状态
- ⏰ **到期提醒** - 显示订阅剩余天数，及时预警
- 📈 **许可证管理** - 追踪许可证使用情况
- 🔄 **定时更新** - 支持设置自动刷新间隔
- 🌙 **主题切换** - 支持明暗主题自动切换
- 📧 **邮件通知** - 订阅状态变化时自动发送邮件提醒
- 🔒 **安全配置** - 支持环境变量配置敏感信息

## 截图

### 白天模式

![白天模式图片](https://s21.ax1x.com/2025/07/11/pVlVRuq.png)

### 夜间模式

![夜间模式图片](https://s21.ax1x.com/2025/07/11/pVlVgvn.png)

## 系统要求

### Python 环境

- Python 3.6+
- 依赖包：
  - requests
  - urllib3
  - python-dotenv
  - pytz

### Web 环境

- PHP 7.0+
- Web 服务器（Apache/Nginx）
- 支持读写文件权限

## 安装指南

### 1. 获取项目代码

```bash
git clone https://github.com/nushena/E5SubWatcher.git
cd E5SubWatcher
```

### 2. 安装 Python 依赖

```bash
pip install requests urllib3 python-dotenv pytz
```

### 3. 配置环境变量

1. 复制环境变量模板文件：

```bash
cp .env.example .env
```

2. 编辑 `.env` 文件，填写以下信息：

```bash
# ========================================
# Microsoft Azure 认证配置
# ========================================
# Azure Active Directory 租户 ID
TENANT_ID=your_tenant_id_here

# Azure 应用程序 (客户端) ID
CLIENT_ID=your_client_id_here

# Azure 应用程序客户端密钥
CLIENT_SECRET=your_client_secret_here

# ========================================
# 邮件SMTP配置 (可选)
# ========================================
SMTP_SERVER=your_smtp_server_here
SMTP_PORT=465
SENDER_EMAIL=your_sender_email_here
SENDER_PASSWORD=your_sender_password_here

# ========================================
# 其他配置
# ========================================
VERIFY_SSL=True
REQUEST_TIMEOUT=30
MAX_RETRIES=3
JSON_FILENAME=e5_sub.json
EMAIL_LOG_FILE=email_sent_log.json
USERS_CONFIG_FILE=users.json
```

### 4. 配置 Microsoft Graph API 凭据

1. 登录 [Azure 门户](https://portal.azure.com)
2. 注册新的应用程序
3. 获取以下信息：
   - 租户 ID (Tenant ID)
   - 客户端 ID (Client ID)
   - 客户端密钥 (Client Secret)
4. 将这些信息填入 `.env` 文件中

### 5. 配置 Web 服务器

将项目文件部署到 Web 服务器根目录，确保 PHP 能够访问并执行。

## 使用方法

### 脚本运行方式

#### 基本用法

```bash
python E5sub.py
```

脚本将自动生成 JSON 文件，默认为 `e5_sub.json`。

#### 定时任务设置

##### Linux/Mac (使用 crontab)

```bash
# 编辑 crontab
crontab -e

# 添加每两小时运行一次的任务
0 */2 * * * /usr/bin/python3 /path/to/E5SubWatcher/E5sub.py
```

##### Windows (使用任务计划程序)

1. 打开"任务计划程序"
2. 创建基本任务
3. 设置触发器为"每天"，重复任务间隔为 2 小时
4. 操作设置为启动程序，程序路径为 Python，参数为脚本路径

### Web 界面访问

1. 确保 Web 服务器正常运行
2. 确保生成的 JSON 文件存在
3. 修改 `index.php` 第三行 `$jsonFile` 变量为生成的 JSON 文件路径
4. 访问 `http://your-server-address/index.php`
5. 查看 E5 订阅状态信息

## 高级功能

### 邮件通知配置

1. 在 `.env` 文件中配置 SMTP 服务器信息
2. 创建 `users.json` 文件，配置需要通知的用户：

字段说明：

- `url`: 用户主页链接
- `username`: 用户名
- `ms_e5_email`: E5 订阅邮箱
- `real_email`: 接收通知的邮箱

```json
[
  {
    "url": "https://xxxxxxx/xxxx",
    "username": "nushen",
    "ms_e5_email": "xxxxxxx@xxxx.xxx",
    "real_email": "xxxx@xx.xxx"
  }
]
```

### 多用户监控

支持同时监控多个 E5 订阅账户，只需在 `users.json` 中添加多个用户配置即可。

## 项目结构

```
E5SubWatcher/
├── .env.example              # 环境变量模板
├── .gitignore               # Git 忽略文件
├── E5sub.py                 # Python 主脚本
├── README.md                # 项目说明文档
├── index.php                # PHP 网页界面
├── e5_sub.json              # 订阅数据文件 (由脚本生成)
├── date/                    # 数据存储目录
├── templates/               # 邮件模板目录
│   ├── notice_template.html         # 通知邮件模板
│   └── renewal_success_template.html # 续期成功邮件模板
└── users.json               # 用户配置文件 (需自行创建)
```

## 配置选项

### E5sub.py 配置参数

#### 认证凭据

- `TENANT_ID`: Azure 租户 ID
- `CLIENT_ID`: Azure 应用程序 ID
- `CLIENT_SECRET`: Azure 应用程序密钥

#### 请求配置

- `VERIFY_SSL`: SSL 验证 (推荐 True)
- `REQUEST_TIMEOUT`: 请求超时时间 (秒)
- `MAX_RETRIES`: 最大重试次数

#### 文件路径配置

- `JSON_FILENAME`: JSON 输出文件名
- `EMAIL_LOG_FILE`: 邮件发送记录文件名
- `USERS_CONFIG_FILE`: 用户配置文件名

### 邮件通知配置

#### 警告级别设置

- **紧急**: 剩余 ≤ 1 天
- **严重**: 剩余 ≤ 5 天
- **警告**: 剩余 ≤ 10 天
- **早期警告**: 剩余 ≤ 15 天

#### 邮件模板

- `notice_template.html`: 订阅状态通知模板
- `renewal_success_template.html`: 续期成功通知模板

## 常见问题解答

### Q: 为什么无法获取访问令牌？

A: 请检查以下项目：

1. Azure 应用程序注册的权限是否配置正确
2. 租户 ID、客户端 ID 和客户端密钥是否正确填写
3. 应用程序是否有 Microsoft Graph API 的访问权限

### Q: 如何设置自动更新频率？

A: 修改 crontab 或计划任务的执行间隔。默认推荐 2 小时更新一次，可根据需要调整。

### Q: 数据文件显示"无法找到"错误怎么办？

A: 检查以下项目：

1. Web 服务器对项目目录的读写权限
2. Python 脚本是否能够正常生成 JSON 文件
3. `index.php` 中的 `$jsonFile` 路径是否正确

### Q: 邮件通知不工作怎么办？

A: 检查以下项目：

1. `.env` 文件中的 SMTP 配置是否正确
2. 发件人邮箱是否开启了 SMTP 服务
3. `users.json` 文件是否存在且格式正确
4. 检查 `date/` 目录是否存在且有写入权限

### Q: 如何添加多个监控账户？

A: 在 `users.json` 文件中添加多个用户配置，每个用户包含 url、username、ms_e5_email 和 real_email 字段。

## 更新日志

### v2.0 (2025-07-11)

- ✨ 新增邮件通知功能
- ✨ 新增多用户支持
- ✨ 新增环境变量配置
- 🎨 优化网页界面设计
- 🌙 新增明暗主题自动切换
- 🔒 增强安全性配置

### v1.0 (2025-06-20)

- 🎉 初始版本发布
- ✨ 基本订阅状态检测功能
- ✨ Web 界面展示
- ✨ 许可证使用情况统计

## 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 联系方式

- 项目主页: [https://github.com/nushena/E5SubWatcher](https://github.com/nushena/E5SubWatcher)
- 问题反馈: [Issues](https://github.com/nushena/E5SubWatcher/issues)
- 邮箱: nushen666@qq.com

## 免责声明

**注意**：本工具仅供学习和个人使用，请遵守 Microsoft 相关服务条款。使用本工具所产生的任何后果由用户自行承担。
