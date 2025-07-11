# 微软 E5 订阅状态检测工具

![版本](https://img.shields.io/badge/版本-1.0-blue)
![Python](https://img.shields.io/badge/Python-3.6+-green)
![PHP](https://img.shields.io/badge/PHP-7.0+-orange)

## 项目简介

微软 E5 订阅状态检测工具是一个用于自动监控 Microsoft 365 E5 订阅状态的解决方案。通过 Microsoft Graph API 获取订阅信息，包括激活状态、许可证使用情况以及到期时间，并通过网页界面直观地展示这些数据。

### 主要功能

- 👀 **实时监控** - 自动检查 E5 订阅状态
- 📊 **数据可视化** - 通过网页界面直观展示订阅状态
- ⏰ **到期提醒** - 显示订阅剩余天数，及时预警
- 📈 **许可证管理** - 追踪许可证使用情况
- 🔄 **定时更新** - 支持设置自动刷新间隔

## 系统要求

### Python 环境

- Python 3.6+
- 依赖包：
  - requests
  - urllib3
  - argparse

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
pip install requests urllib3
```

### 3. 配置 Microsoft Graph API 凭据

1. 登录 [Azure 门户](https://portal.azure.com)
2. 注册新的应用程序
3. 获取以下信息：
   - 租户 ID (Tenant ID)
   - 客户端 ID (Client ID)
   - 客户端密钥 (Client Secret)
4. 在 `E5sub.py` 中填写这些信息：

```python
TENANT_ID = "你的租户ID"
CLIENT_ID = "你的应用ID"
CLIENT_SECRET = "你的应用密钥"
```

### 4. 配置 Web 服务器

将项目文件部署到 Web 服务器根目录，确保 PHP 能够访问并执行。

## 使用方法

### 脚本运行方式

#### 基本用法

```bash
python E5sub.py
```

后自动生成 json 文件

### Web 界面访问

1. 确保 Web 服务器正常运行
2. 确保生成的 json 文件存在
3. 修改 index.php 第三行 $jsonFile 变量为生成的 json
4. 访问 `http://your-server-address/index.php`
5. 查看 E5 订阅状态信息

## 配置选项

### E5sub.py 配置参数

```python
# 认证凭据
TENANT_ID = "你的租户ID"
CLIENT_ID = "你的应用ID"
CLIENT_SECRET = "你的应用密钥"

# 请求配置
VERIFY_SSL = True  # SSL验证
REQUEST_TIMEOUT = 30  # 请求超时（秒）
MAX_RETRIES = 3  # 最大重试次数

# 输出配置
JSON_FILENAME = "output.json"  # 输出文件名
DEFAULT_OUTPUT_DIR = "./E5Output"  # 默认输出目录
```

## 常见问题解答

### Q: 为什么无法获取访问令牌？

A: 请检查 Azure 应用程序注册的权限是否配置正确，以及租户 ID、客户端 ID 和客户端密钥是否正确填写。

### Q: 如何设置自动更新频率？

A: 修改 crontab 或计划任务的执行间隔。默认推荐 2 小时更新一次，可根据需要调整。

### Q: 数据文件显示"无法找到"错误怎么办？

A: 检查 Web 服务器对项目目录的读写权限，确保 Python 脚本能够正常生成 JSON 文件。

**注意**：本工具仅供学习和个人使用，请遵守 Microsoft 相关服务条款。
