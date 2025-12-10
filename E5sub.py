import requests
import json
import time
import os
from datetime import datetime, timedelta
import urllib3
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
import pytz
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 禁用不安全连接警告（仅在verify=False时需要）
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# 常量定义 - 消除魔法数字
class Constants:
    """应用程序常量定义"""

    # 订阅到期提醒天数
    EXPIRY_WARNING_DAYS = {
        "CRITICAL": 1,
        "URGENT": 5,
        "WARNING": 10,
        "EARLY_WARNING": 15,
    }

    # 邮件主题模板
    EMAIL_SUBJECTS = {
        "WARNING": "【注意】微软E5订阅{status}提醒",
        "NOTICE": "【注意】微软E5订阅{status}通知",
        "RENEWAL_SUCCESS": "【续期成功】微软E5订阅{status}通知",
        "NORMAL": "微软E5订阅状态通知",
    }

    # 状态颜色配置
    COLORS = {
        "danger": {
            "status_color": "#dc3545",
            "expiry_bg": "#f8d7da",
            "expiry_border": "#f5c6cb",
        },
        "warning": {
            "status_color": "#ffc107",
            "expiry_bg": "#fff3cd",
            "expiry_border": "#ffeaa7",
        },
        "normal": {
            "status_color": "#28a745",
            "expiry_bg": "#d4edda",
            "expiry_border": "#c3e6cb",
        },
    }

    # 邮件模板中的固定文本
    EMAIL_MESSAGES = {
        "backup_warning": "⚠️ 如果剩余天数小于 10 天，💾建议立即备份文件！",
        "footer_note": "本邮件由系统自动发送，用于提前 15 / 10 / 5 / 1 天提醒订阅到期，请勿回复。",
        "ignore_notice": "如非本人操作，请忽略此邮件。",
    }


# 从环境变量获取认证凭据
TENANT_ID = os.getenv("TENANT_ID")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

# 从环境变量获取请求配置
VERIFY_SSL = os.getenv("VERIFY_SSL", "True").lower() == "true"
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))


# 从环境变量获取文件路径配置
JSON_FILENAME = os.getenv("JSON_FILENAME", "e5_sub.json")
EMAIL_LOG_FILE = os.getenv("EMAIL_LOG_FILE", "email_sent_log.json")
USERS_CONFIG_FILE = os.getenv("USERS_CONFIG_FILE", "users.json")

# 获取项目根目录（脚本所在目录）
PROJECT_ROOT_DIR = os.path.dirname(os.path.abspath(__file__))


def get_json_file_path():
    """获取JSON文件的完整路径

    Returns:
        str: JSON文件的完整路径
    """
    # 如果JSON_FILENAME是绝对路径，直接使用
    if os.path.isabs(JSON_FILENAME):
        return JSON_FILENAME

    # 如果是相对路径，拼接项目根目录
    return os.path.join(PROJECT_ROOT_DIR, JSON_FILENAME)


def filter_subscription_data(data):
    """过滤订阅数据，只保留用户必要信息

    Args:
        data: 完整的订阅数据

    Returns:
        dict: 过滤后的订阅数据
    """
    # 如果是错误信息，直接返回
    if isinstance(data, dict) and "error" in data:
        return data

    # 提取基本信息
    filtered_data = {
        "sku_name": data.get("sku_name", "未知"),
        "status": data.get("status", "未知"),
        "consumed_units": data.get("consumed_units", 0),
        "total_units": data.get("total_units", 0),
        "check_time": data.get("check_time", "未知"),
    }

    # 处理到期信息
    expiry_info = data.get("expiry_info", {})
    if isinstance(expiry_info, dict) and "error" not in expiry_info:
        filtered_expiry_info = {
            "expiry_date": expiry_info.get("expiry_date", "未知"),
            "days_left": expiry_info.get("days_left", "未知"),
            "status": expiry_info.get("status", "未知"),
        }
        filtered_data["expiry_info"] = filtered_expiry_info
    else:
        # 如果到期信息有错误或不存在，设置默认值
        filtered_data["expiry_info"] = {
            "expiry_date": "未知",
            "days_left": "未知",
            "status": "未知",
        }

    return filtered_data


def save_json_data(data, file_path=None, filter_data=True):
    """保存数据到JSON文件

    Args:
        data: 要保存的数据
        file_path: 文件路径，如果为None则使用默认路径
        filter_data: 是否过滤数据，只保留用户必要信息

    Returns:
        bool: 保存是否成功
    """
    try:
        # 如果没有指定文件路径，使用默认路径
        if file_path is None:
            file_path = get_json_file_path()

        # 确保目录存在
        dir_path = os.path.dirname(file_path)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)

        # 如果文件已存在，先删除
        if os.path.exists(file_path):
            os.remove(file_path)

        # 过滤数据（如果是订阅数据）
        data_to_save = filter_subscription_data(data)

        # 保存数据
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data_to_save, f, ensure_ascii=False, indent=2)

        return True

    except Exception as e:
        print(f"保存JSON文件失败: {e}")
        return False


def load_users_config():
    """从JSON文件加载用户配置

    Returns:
        list: 用户配置列表，如果加载失败则返回空列表
    """
    try:
        # 从项目根目录加载用户配置
        config_path = os.path.join(PROJECT_ROOT_DIR, USERS_CONFIG_FILE)

        # 如果文件存在，则加载
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                users = json.load(f)
                print(f"已从 {config_path} 加载 {len(users)} 个用户")
                return users
        else:
            print(f"用户配置文件不存在: {config_path}")
            return []
    except Exception as e:
        print(f"加载用户配置文件失败: {e}")
        return []


def get_session():
    """创建一个带有重试机制的会话"""
    session = requests.Session()
    retry_strategy = Retry(
        total=MAX_RETRIES,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def get_access_token():
    """获取访问令牌"""
    token_url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
    token_data = {
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "scope": "https://graph.microsoft.com/.default",
    }

    try:
        session = get_session()
        response = session.post(
            token_url, data=token_data, verify=VERIFY_SSL, timeout=REQUEST_TIMEOUT
        )

        if response.status_code == 200:
            return response.json().get("access_token")
        else:
            print(f"获取令牌失败: {response.status_code}")
            print(response.text)
            return None
    except requests.exceptions.SSLError as ssl_err:
        print(f"SSL错误: {ssl_err}")
        return None
    except requests.exceptions.RequestException as req_err:
        print(f"请求错误: {req_err}")
        return None
    except Exception as e:
        print(f"获取访问令牌时出现未知错误: {e}")
        return None


def check_subscription_status(access_token):
    """检查订阅状态，包括到期时间"""
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    # 获取订阅信息
    subscription_url = "https://graph.microsoft.com/v1.0/subscribedSkus"
    try:
        session = get_session()
        response = session.get(
            subscription_url,
            headers=headers,
            verify=VERIFY_SSL,
            timeout=REQUEST_TIMEOUT,
        )

        if response.status_code == 200:
            subscriptions = response.json().get("value", [])

            # 查找E5订阅
            for subscription in subscriptions:
                sku_part_number = subscription.get("skuPartNumber", "")
                if "E5" in sku_part_number:
                    # 获取状态
                    status = (
                        "活跃"
                        if subscription.get("capabilityStatus") == "Enabled"
                        else "状态异常！！"
                    )
                    consumed = subscription.get("consumedUnits", 0)
                    total = subscription.get("prepaidUnits", {}).get("enabled", 0)

                    # 获取订阅ID
                    subscription_ids = subscription.get("subscriptionIds", [])

                    # 获取详细订阅信息，包括到期时间
                    # 使用正确的参数调用函数
                    if subscription_ids:
                        expiry_info = get_subscription_expiry_info(
                            access_token, subscription_ids
                        )
                        if "error" not in expiry_info:
                            # 保留完整的expiry_info，不覆盖
                            pass
                        else:
                            expiry_info = {"error": expiry_info["error"]}
                    else:
                        expiry_info = {"error": "无法获取订阅数据"}

                    # 获取上海时区的当前时间
                    shanghai_tz = pytz.timezone("Asia/Shanghai")
                    now_shanghai = datetime.now(shanghai_tz)

                    return {
                        "sku_name": sku_part_number,
                        "status": status,
                        "consumed_units": consumed,
                        "total_units": total,
                        "expiry_info": expiry_info,
                        "check_time": now_shanghai.strftime("%Y-%m-%d %H:%M:%S"),
                    }

            return {"error": "未找到E5订阅"}
        else:
            print(f"获取订阅信息失败: {response.status_code}")
            print(response.text)
            return {"error": f"API错误: {response.status_code}"}
    except requests.exceptions.RequestException as req_err:
        print(f"请求错误: {req_err}")
        return {"error": f"请求错误: {req_err}"}
    except Exception as e:
        print(f"检查订阅状态时出现未知错误: {e}")
        return {"error": f"未知错误: {e}"}


def get_subscription_expiry_info(access_token, subscription_ids):
    """获取订阅到期信息

    Args:
        access_token: 访问令牌
        subscription_ids: 订阅ID列表

    Returns:
        dict: 包含到期信息的字典
    """
    if not subscription_ids:
        return {"error": "没有可用的订阅ID"}

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    expiry_info = {}

    # 使用第一个订阅ID获取详细信息
    subscription_id = subscription_ids[0]

    # 获取上海时区
    shanghai_tz = pytz.timezone("Asia/Shanghai")

    # 尝试获取订阅的生命周期信息
    try:
        # 获取订阅详细信息
        subscriptions_url = f"https://graph.microsoft.com/v1.0/directory/subscriptions"
        session = get_session()
        response = session.get(
            subscriptions_url,
            headers=headers,
            verify=VERIFY_SSL,
            timeout=REQUEST_TIMEOUT,
        )

        if response.status_code == 200:
            subscriptions = response.json().get("value", [])
            for sub in subscriptions:
                if sub.get("id") == subscription_id:
                    # 获取下一个生命周期日期
                    next_lifecycle_date = sub.get("nextLifecycleDateTime")
                    if next_lifecycle_date:
                        try:
                            # 解析UTC时间并转换为上海时区
                            expiry_date_utc = datetime.fromisoformat(
                                next_lifecycle_date.replace("Z", "+00:00")
                            )
                            expiry_date_shanghai = expiry_date_utc.astimezone(
                                shanghai_tz
                            )
                            current_time_shanghai = datetime.now(shanghai_tz)

                            # 计算剩余天数（使用上海时区）
                            days_left = (
                                expiry_date_shanghai.date()
                                - current_time_shanghai.date()
                            ).days

                            expiry_info = {
                                "expiry_date": expiry_date_shanghai.strftime(
                                    "%Y-%m-%d %H:%M:%S"
                                ),
                                "days_left": days_left,
                                "status": "即将到期" if days_left <= 30 else "正常",
                            }
                        except Exception as e:
                            expiry_info = {"error": f"日期格式错误: {str(e)}"}
                    break

        # 如果上面的方法无法获取到期日期，使用另一种方法
        if not expiry_info:
            # 获取订阅明细
            org_info_url = "https://graph.microsoft.com/v1.0/organization"
            response = session.get(
                org_info_url,
                headers=headers,
                verify=VERIFY_SSL,
                timeout=REQUEST_TIMEOUT,
            )
            if response.status_code == 200:
                org_info = response.json().get("value", [{}])[0]

                # 检查组织信息中是否有到期日期相关字段
                if "assignedPlans" in org_info:
                    for plan in org_info.get("assignedPlans", []):
                        if (
                            "Enterprise" in plan.get("servicePlanName", "")
                            and plan.get("capabilityStatus") == "Enabled"
                        ):
                            expiry_date = plan.get("assignedDateTime")
                            if expiry_date:
                                try:
                                    # 解析UTC时间并转换为上海时区
                                    assign_date_utc = datetime.fromisoformat(
                                        expiry_date.replace("Z", "+00:00")
                                    )
                                    assign_date_shanghai = assign_date_utc.astimezone(
                                        shanghai_tz
                                    )

                                    # 估计到期时间（通常是从分配日期起一年）
                                    est_expiry_shanghai = (
                                        assign_date_shanghai + timedelta(days=365)
                                    )
                                    current_time_shanghai = datetime.now(shanghai_tz)

                                    # 计算剩余天数（使用上海时区）
                                    days_left = (
                                        est_expiry_shanghai.date()
                                        - current_time_shanghai.date()
                                    ).days

                                    expiry_info = {
                                        "expiry_date": est_expiry_shanghai.strftime(
                                            "%Y-%m-%d %H:%M:%S"
                                        ),
                                        "days_left": days_left,
                                        "status": "估计到期日期",
                                        "note": "这是一个估计值，基于订阅开始日期加一年",
                                    }
                                    break
                                except Exception as e:
                                    expiry_info = {"error": f"日期计算错误: {str(e)}"}
    except requests.exceptions.RequestException as req_err:
        expiry_info = {"error": f"请求错误: {req_err}"}
    except Exception as e:
        expiry_info = {"error": f"获取到期信息时出错: {str(e)}"}

    # 如果无法通过API获取到期信息，提供备选方法
    if not expiry_info:
        expiry_info = {
            "message": "无法通过API获取准确的到期日期",
            "suggestion": "请登录Microsoft 365管理中心查看准确的到期日期: https://admin.microsoft.com/AdminPortal/Home#/subscriptions",
        }

    return expiry_info


def load_email_log():
    """加载邮件发送记录"""
    try:
        # 获取脚本所在目录（根目录）
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # 创建date文件夹路径
        date_dir = os.path.join(script_dir, "date")
        # 确保date文件夹存在
        if not os.path.exists(date_dir):
            os.makedirs(date_dir)
        # 构建邮件日志文件完整路径
        log_file_path = os.path.join(date_dir, EMAIL_LOG_FILE)

        if os.path.exists(log_file_path):
            with open(log_file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}
    except Exception as e:
        print(f"加载邮件发送记录失败: {e}")
        return {}


def save_email_log(email_log):
    """保存邮件发送记录"""
    try:
        # 获取脚本所在目录（根目录）
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # 创建date文件夹路径
        date_dir = os.path.join(script_dir, "date")
        # 确保date文件夹存在
        if not os.path.exists(date_dir):
            os.makedirs(date_dir)
        # 构建邮件日志文件完整路径
        log_file_path = os.path.join(date_dir, EMAIL_LOG_FILE)

        with open(log_file_path, "w", encoding="utf-8") as f:
            json.dump(email_log, f, ensure_ascii=False, indent=2)
        return True, f"邮件发送记录已保存到: {log_file_path}"
    except Exception as e:
        return False, f"保存邮件发送记录失败: {e}"


def should_send_email_today(user_email, email_reason, email_log):
    """判断今天是否应该发送邮件给指定用户"""
    today = datetime.now().strftime("%Y-%m-%d")

    # 如果用户不在记录中，应该发送
    if user_email not in email_log:
        return True

    # 检查今天是否已经因为相同原因发送过邮件
    user_log = email_log[user_email]
    if today in user_log and email_reason in user_log[today]:
        return False

    return True


def determine_warning_level(days_left):
    """根据剩余天数确定警告级别和状态文本

    Args:
        days_left (int or str): 剩余天数

    Returns:
        tuple: (warning_level, status_text)
    """
    # 处理字符串类型的days_left
    if isinstance(days_left, str):
        try:
            days_left = int(days_left)
        except (ValueError, TypeError):
            return "normal", "未知"

    if not isinstance(days_left, int):
        return "normal", "未知"
    if days_left <= 0:
        return "danger", "已过期"
    elif days_left <= Constants.EXPIRY_WARNING_DAYS["URGENT"]:
        return "danger", "即将过期"
    elif days_left <= Constants.EXPIRY_WARNING_DAYS["EARLY_WARNING"]:
        return "warning", "即将到期"
    else:
        return "normal", "正常"


def build_email_subject(warning_level, status_text, email_type="NOTICE"):
    """构建邮件主题

    Args:
        warning_level (str): 警告级别
        status_text (str): 状态文本
        email_type (str): 邮件类型，可选值: "NOTICE", "RENEWAL_SUCCESS"

    Returns:
        str: 邮件主题
    """
    if email_type == "RENEWAL_SUCCESS":
        return Constants.EMAIL_SUBJECTS["RENEWAL_SUCCESS"].format(status=status_text)
    elif email_type == "NOTICE":
        if warning_level == "danger":
            return Constants.EMAIL_SUBJECTS["NOTICE"].format(status=status_text)
        elif warning_level == "warning":
            return Constants.EMAIL_SUBJECTS["WARNING"].format(status=status_text)
        else:
            return Constants.EMAIL_SUBJECTS["NORMAL"]
    else:
        return Constants.EMAIL_SUBJECTS["NOTICE"].format(status=status_text)


def get_color_config(warning_level):
    """获取颜色配置

    Args:
        warning_level (str): 警告级别

    Returns:
        dict: 颜色配置字典
    """
    return Constants.COLORS.get(warning_level, Constants.COLORS["normal"])


def load_email_template(email_type):
    """加载邮件HTML模板

    Args:
        email_type (str): 邮件类型，可选值: "NOTICE", "RENEWAL_SUCCESS"

    Returns:
        str: 模板内容
    """
    try:
        # 根据邮件类型选择模板文件
        if email_type == "RENEWAL_SUCCESS":
            template_file = "templates/renewal_success_template.html"
        else:
            template_file = "templates/notice_template.html"

        # 获取当前脚本所在目录
        current_dir = os.path.dirname(os.path.abspath(__file__))
        template_path = os.path.join(current_dir, template_file)

        # 读取模板文件
        with open(template_path, "r", encoding="utf-8") as f:
            template_content = f.read()

        return template_content
    except Exception as e:
        print(f"加载邮件模板失败: {str(e)}")
        # 如果模板加载失败，返回默认模板
        return """
        <html>
        <head><title>邮件通知</title></head>
        <body>
        <h2>邮件通知</h2>
        <p>邮件模板加载失败，使用默认模板。</p>
        </body>
        </html>
        """


def build_email_content(
    sku_name,
    status,
    expiry_date,
    days_left,
    expiry_status,
    user_url,
    user_name,
    ms_e5_email,
    warning_level,
    email_type="NOTICE",
    used_licenses=None,
    total_licenses=None,
    check_time=None,
):
    """构建邮件HTML内容

    Args:
        sku_name (str): 订阅类型
        status (str): 订阅状态
        expiry_date (str): 到期日期
        days_left (str or int): 剩余天数
        expiry_status (str): 到期状态说明
        user_url (str): 用户链接
        user_name (str): 用户名
        ms_e5_email (str): 微软E5邮箱
        warning_level (str): 警告级别
        email_type (str): 邮件类型，可选值: "NOTICE", "RENEWAL_SUCCESS"
        used_licenses (str or int): 已使用许可证数量
        total_licenses (str or int): 总许可证数量
        check_time (str): 检测时间

    Returns:
        str: HTML邮件内容
    """
    colors = get_color_config(warning_level)

    # 加载邮件模板
    template = load_email_template(email_type)

    # 替换模板中的占位符
    html_content = template.replace("{subscription_type}", sku_name)
    html_content = html_content.replace("{status}", status)
    html_content = html_content.replace("{expiry_date}", expiry_date)
    html_content = html_content.replace("{days_left}", str(days_left))
    html_content = html_content.replace("{expiry_status}", expiry_status)
    html_content = html_content.replace("{user_url}", user_url or "#")
    html_content = html_content.replace("{user_name}", user_name or "用户")
    html_content = html_content.replace("{ms_e5_email}", ms_e5_email or "未知")

    # 替换续期成功邮件特有的占位符
    if used_licenses is not None and total_licenses is not None:
        html_content = html_content.replace("{used_licenses}", str(used_licenses))
        html_content = html_content.replace("{total_licenses}", str(total_licenses))
    else:
        # 如果没有提供许可证信息，使用默认值
        html_content = html_content.replace(
            "{used_licenses}/{total_licenses}", "未知/未知"
        )

    if check_time is not None:
        html_content = html_content.replace("{check_time}", check_time)
    else:
        # 如果没有提供检测时间，使用当前时间
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        html_content = html_content.replace("{check_time}", current_time)

    # 替换颜色变量
    html_content = html_content.replace("{status_color}", colors["status_color"])
    html_content = html_content.replace("{expiry_bg}", colors["expiry_bg"])
    html_content = html_content.replace("{expiry_border}", colors["expiry_border"])

    # 替换消息常量
    html_content = html_content.replace(
        "{backup_warning}", Constants.EMAIL_MESSAGES["backup_warning"]
    )
    html_content = html_content.replace(
        "{footer_note}", Constants.EMAIL_MESSAGES["footer_note"]
    )
    html_content = html_content.replace(
        "{ignore_notice}", Constants.EMAIL_MESSAGES["ignore_notice"]
    )

    return html_content


def mark_email_sent(user_email, email_reason, email_log):
    """标记邮件已发送"""
    today = datetime.now().strftime("%Y-%m-%d")

    if user_email not in email_log:
        email_log[user_email] = {}

    if today not in email_log[user_email]:
        email_log[user_email][today] = []

    if email_reason not in email_log[user_email][today]:
        email_log[user_email][today].append(email_reason)

    return email_log


def save_to_json(results, output_dir=None):
    """将结果保存到JSON文件

    Args:
        results (list): 要保存的结果列表
        output_dir (str): 输出目录路径（可选）

    Returns:
        str: 保存的文件路径
    """
    try:
        # 如果没有指定输出目录，使用项目根目录
        if output_dir is None:
            output_dir = PROJECT_ROOT_DIR

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"e5_subscription_check_{timestamp}.json"
        file_path = os.path.join(output_dir, filename)

        data = {"timestamp": timestamp, "results": results}

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"结果已保存到: {file_path}")
        return file_path

    except Exception as e:
        print(f"保存JSON文件失败: {e}")
        return None


def sendEmail(
    to_email,
    subscription_info=None,
    userUrl=None,
    userName=None,
    msE5Email=None,
    email_type="NOTICE",
):
    """
    使用88邮箱发送微软E5订阅状态提醒邮件（重构版本）

    参数:
        to_email: 收件人邮箱地址(字符串)
        subscription_info: E5订阅信息字典(可选)，如果不提供将自动获取
        userUrl: 用户链接(可选)
        userName: 用户名(可选)
        msE5Email: 微软E5邮箱(可选)
        email_type: 邮件类型，可选值: "NOTICE", "RENEWAL_SUCCESS"

    返回:
        tuple: (是否成功, 消息)
    """
    try:
        # 验证收件人邮箱
        if not to_email or not isinstance(to_email, str):
            return False, "收件人邮箱地址格式错误"

        # 如果没有提供订阅信息，则获取
        if subscription_info is None:
            print("正在获取E5订阅信息...")
            access_token = get_access_token()
            if not access_token:
                return False, "获取访问令牌失败"
            subscription_info = check_subscription_status(access_token)

        # 检查订阅信息是否有效
        if "error" in subscription_info:
            print(f"获取订阅信息失败: {subscription_info['error']}")
            # 即使获取订阅信息失败，也发送基本通知邮件
            sku_name = "未知"
            status = "未知"
            expiry_date = "未知"
            days_left = "未知"
            expiry_status = "无法获取"
        else:
            sku_name = subscription_info.get("sku_name", "未知")
            status = subscription_info.get("status", "未知")

            # 处理到期信息
            expiry_info = subscription_info.get("expiry_info", {})
            if "error" in expiry_info or "message" in expiry_info:
                expiry_date = "未知"
                days_left = "未知"
                expiry_status = expiry_info.get("message", "无法获取")
            else:
                expiry_date = expiry_info.get("expiry_date", "未知")
                days_left = expiry_info.get("days_left", "未知")
                expiry_status = expiry_info.get("status", "未知")

        # 根据剩余天数确定警告级别
        warning_level, status_text = determine_warning_level(days_left)

        # 构建邮件主题
        subject = build_email_subject(warning_level, status_text, email_type)

        # 构建HTML内容
        html_content = build_email_content(
            sku_name,
            status,
            expiry_date,
            days_left,
            expiry_status,
            userUrl,
            userName,
            msE5Email,
            warning_level,
            email_type,
            used_licenses=(
                subscription_info.get("consumed_units")
                if "consumed_units" in subscription_info
                else None
            ),
            total_licenses=(
                subscription_info.get("total_units")
                if "total_units" in subscription_info
                else None
            ),
            check_time=(
                subscription_info.get("check_time")
                if "check_time" in subscription_info
                else None
            ),
        )

        # 从环境变量获取SMTP配置
        SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.88.com")
        SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
        SENDER_EMAIL = os.getenv("SENDER_EMAIL", "nushen@88.com")
        SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")

        # 收件人列表
        to_email_list = [to_email]

        # 创建邮件对象
        message = MIMEMultipart("alternative")
        # 确保From头符合RFC 5322规范 - 使用简单格式
        message["From"] = SENDER_EMAIL
        message["To"] = to_email
        message["Subject"] = Header(subject, "utf-8")

        # 添加邮件内容(HTML格式)
        html_part = MIMEText(html_content, "html", "utf-8")
        message.attach(html_part)

        # 连接到88邮箱SMTP服务器(使用SSL)
        print(f"正在连接到88邮箱SMTP服务器 {SMTP_SERVER}:{SMTP_PORT}...")
        server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, timeout=30)

        # 登录
        print("正在登录...")
        server.login(SENDER_EMAIL, SENDER_PASSWORD)

        # 发送邮件
        print(f"正在发送邮件到: {to_email}...")
        server.sendmail(SENDER_EMAIL, to_email_list, message.as_string())

        # 关闭连接
        server.quit()

        print("邮件发送成功！")
        return True, "邮件发送成功"

    except smtplib.SMTPAuthenticationError:
        error_msg = "SMTP认证失败，请检查88邮箱地址和密码是否正确"
        print(f"错误: {error_msg}")
        return False, error_msg
    except smtplib.SMTPException as e:
        error_msg = f"SMTP错误: {str(e)}"
        print(f"错误: {error_msg}")
        return False, error_msg
    except Exception as e:
        error_msg = f"发送邮件时出错: {str(e)}"
        print(f"错误: {error_msg}")
        return False, error_msg


def send_renewal_success_email(to_email, userUrl=None, userName=None, msE5Email=None):
    """发送续期成功邮件

    参数:
        to_email: 收件人邮箱地址(字符串)
        userUrl: 用户链接(可选)
        userName: 用户名(可选)
        msE5Email: 微软E5邮箱(可选)

    返回:
        tuple: (是否成功, 消息)
    """
    return sendEmail(
        to_email=to_email,
        userUrl=userUrl,
        userName=userName,
        msE5Email=msE5Email,
        email_type="RENEWAL_SUCCESS",
    )


def initialize_environment():
    """初始化环境，加载必要的配置和数据

    Returns:
        tuple: (email_log, users, access_token, subscription_info, error_message)
    """
    try:
        print("开始检测微软E5订阅状态...")
        start_time = time.time()

        # 加载邮件发送记录
        email_log = load_email_log()
        print(f"已加载邮件发送记录，共记录 {len(email_log)} 个用户的发送历史")

        # 加载用户配置
        users = load_users_config()
        print(f"已加载 {len(users)} 个用户配置")

        # 获取访问令牌
        access_token = get_access_token()
        if not access_token:
            return (
                None,
                None,
                None,
                None,
                "获取访问令牌失败，请检查凭据是否正确。如果是SSL错误，可能需要检查网络环境或临时禁用SSL验证。",
            )

        # 检查订阅状态
        subscription_info = check_subscription_status(access_token)

        return email_log, users, access_token, subscription_info, None

    except Exception as e:
        return None, None, None, None, f"环境初始化失败: {str(e)}"


def display_subscription_status(subscription_info, start_time):
    """显示订阅状态信息

    Args:
        subscription_info: 订阅信息字典
        start_time: 开始时间
    """
    if "error" in subscription_info:
        print(f"错误: {subscription_info['error']}")
        return

    print("\n===== 微软E5订阅状态 =====")
    print(f"订阅类型: {subscription_info['sku_name']}")
    print(f"状态: {subscription_info['status']}")
    print(
        f"已使用许可证: {subscription_info['consumed_units']}/{subscription_info['total_units']}"
    )

    # 显示到期信息
    expiry_info = subscription_info.get("expiry_info", {})
    if "error" in expiry_info:
        print(f"到期信息获取失败: {expiry_info['error']}")
    elif "message" in expiry_info:
        print(f"到期信息: {expiry_info['message']}")
        if "suggestion" in expiry_info:
            print(f"建议: {expiry_info['suggestion']}")
    else:
        print(f"到期日期: {expiry_info.get('expiry_date', '未知')}")
        print(f"剩余天数: {expiry_info.get('days_left', '未知')}")
        print(f"状态: {expiry_info.get('status', '未知')}")
        if expiry_info.get("note"):
            print(f"注意: {expiry_info['note']}")

        # 添加到期提醒
        days_left = expiry_info.get("days_left")
        if days_left is not None:
            if days_left <= 0:
                print("警告: 订阅已过期！")
            elif days_left <= 7:
                print("警告: 订阅即将在一周内过期！")
            elif days_left <= 30:
                print("提示: 订阅将在30天内过期，请考虑续订。")

    print(f"检测时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"耗时: {time.time() - start_time:.2f}秒")
    print("========================")


def check_renewal_success(current_subscription_info, json_file_path=None):
    """检查续期是否成功，通过对比当前与上次的订阅信息

    Args:
        current_subscription_info: 当前订阅信息
        json_file_path: JSON文件路径，如果为None则使用默认路径

    Returns:
        tuple: (is_renewed, previous_info, message)
    """
    try:
        # 确定JSON文件路径
        if json_file_path:
            file_path = json_file_path
        else:
            file_path = get_json_file_path()

        # 检查文件是否存在
        if not os.path.exists(file_path):
            return False, None, "未找到历史记录文件，无法判断续期状态"

        # 读取历史数据
        with open(file_path, "r", encoding="utf-8") as f:
            previous_data = json.load(f)
        # 获取当前和历史到期信息
        current_expiry = current_subscription_info.get("expiry_info", {})
        previous_expiry = previous_data.get("expiry_info", {})

        # 检查是否有有效的到期信息
        if "error" in current_expiry or "error" in previous_expiry:
            return False, previous_data, "无法获取有效的到期信息"

        # 获取剩余天数
        current_days_left = current_expiry.get("days_left")
        previous_days_left = previous_expiry.get("days_left")

        # 如果无法获取剩余天数，则无法判断
        if current_days_left is None or previous_days_left is None:
            return False, previous_data, "无法获取剩余天数信息"

        # 判断续期是否成功
        # 1. 如果之前天数小于等于0，现在大于0，说明续期成功
        # 2. 如果之前天数小于30，现在天数明显增加，说明续期成功
        is_renewed = False
        message = ""

        if previous_days_left <= 0 and current_days_left > 0:
            is_renewed = True
            message = f"续期成功！从已过期恢复为剩余{current_days_left}天"
        elif previous_days_left < 30 and current_days_left > previous_days_left + 20:
            is_renewed = True
            message = (
                f"续期成功！剩余天数从{previous_days_left}天增加到{current_days_left}天"
            )
        else:
            message = f"续期状态无变化，当前剩余{current_days_left}天"
        return is_renewed, previous_data, message

    except Exception as e:
        return False, None, f"检查续期状态时出错: {str(e)}"


def send_renewal_success_emails(users, current_subscription_info):
    """发送续期成功邮件

    Args:
        users: 用户列表
        current_subscription_info: 当前订阅信息

    Returns:
        tuple: (success_count, failure_count)
    """
    success_count = 0
    failure_count = 0

    for user in users:
        # 提取用户信息
        user_url = user["url"]
        user_name = user["username"]
        ms_e5_email = user["ms_e5_email"]
        receiver_email = user["real_email"]

        try:
            # 发送续期成功邮件
            success, message = sendEmail(
                to_email=receiver_email,
                subscription_info=current_subscription_info,
                userUrl=user_url,
                userName=user_name,
                msE5Email=ms_e5_email,
                email_type="RENEWAL_SUCCESS",
            )

            if success:
                print(f"续期成功邮件已发送到: {receiver_email}")
                success_count += 1
            else:
                print(f"发送续期成功邮件失败: {message}")
                failure_count += 1

        except Exception as e:
            print(f"处理用户 {user_name} 续期成功邮件时出错: {str(e)}")
            failure_count += 1

    return success_count, failure_count


def should_send_email_notification(subscription_info):
    """判断是否需要发送邮件通知

    Args:
        subscription_info: 订阅信息字典

    Returns:
        tuple: (should_send, reason)
    """
    # 检查订阅状态
    if subscription_info.get("status") != "活跃":
        return True, "订阅状态异常"
    # 检查剩余天数
    expiry_info = subscription_info.get("expiry_info", {})
    days_left = expiry_info.get("days_left")

    if days_left is not None:
        if days_left <= 0:
            return True, "订阅已过期"
        elif days_left in [15, 10, 5, 1]:
            return True, f"订阅剩余{days_left}天"

    return False, ""


def process_user_emails(users, email_log, subscription_info, should_send, email_reason):
    """处理用户邮件发送

    Args:
        users: 用户列表
        email_log: 邮件发送记录
        subscription_info: 订阅信息
        should_send: 是否应该发送邮件
        email_reason: 发送邮件的原因

    Returns:
        tuple: (sent_count, skipped_count, updated_email_log)
    """
    email_sent_count = 0
    email_skipped_count = 0
    updated_email_log = email_log.copy()

    for user in users:
        # 提取用户信息
        user_url = user["url"]
        user_name = user["username"]
        ms_e5_email = user["ms_e5_email"]
        receiver_email = user["real_email"]

        # 检查今天是否已经发送过邮件
        if should_send and not should_send_email_today(
            receiver_email, email_reason, email_log
        ):
            print(f"\n用户 {user_name} 今天已因'{email_reason}'发送过邮件，跳过发送")
            email_skipped_count += 1
            continue

        # 发送邮件
        if should_send:
            print(
                f"\n{email_reason}，正在发送邮件通知到: {receiver_email} ({users.index(user)+1}/{len(users)})"
            )

            try:
                # 检查是否有错误
                if "error" in subscription_info:
                    print(
                        f"订阅信息包含错误，跳过用户 {user_name}: {subscription_info['error']}"
                    )
                    email_skipped_count += 1
                    continue

                # 提取订阅信息
                sku_name = subscription_info.get("sku_name", "未知")
                status = subscription_info.get("status", "未知")

                # 获取到期信息
                expiry_info = subscription_info.get("expiry_info", {})
                expiry_date = expiry_info.get("expiry_date", "未知")
                days_left = expiry_info.get("days_left", "未知")
                expiry_status = expiry_info.get("status", "订阅正常")

                # 确定警告级别
                warning_level, _ = determine_warning_level(days_left)

                # 发送邮件
                success, message = sendEmail(
                    to_email=receiver_email,
                    subscription_info=subscription_info,
                    userUrl=user_url,
                    userName=user_name,
                    msE5Email=ms_e5_email,
                    email_type="NOTICE",
                )

                if success:
                    print(f"邮件发送成功: {message}")
                    # 标记邮件已发送
                    updated_email_log = mark_email_sent(
                        receiver_email, email_reason, updated_email_log
                    )
                    email_sent_count += 1
                else:
                    print(f"邮件发送失败: {message}")

            except Exception as e:
                print(f"处理用户 {user_name} 邮件时出错: {str(e)}")
                email_skipped_count += 1
        else:
            email_skipped_count += 1

    return email_sent_count, email_skipped_count, updated_email_log


def save_results(email_log, subscription_info, email_sent_count, json_file_path=None):
    """保存结果到文件和记录

    Args:
        email_log: 邮件发送记录
        subscription_info: 订阅信息
        email_sent_count: 发送邮件数量
        json_file_path: JSON文件完整路径，如果提供则使用此路径
    """
    try:
        # 保存邮件发送记录
        if email_sent_count > 0:
            success, message = save_email_log(email_log)
            if success:
                print(f"\n{message}")
            else:
                print(f"\n{message}")

        # 保存结果到JSON文件
        if json_file_path:
            success = save_json_data(subscription_info, json_file_path)
            if success:
                print(f"检测结果已保存到JSON文件: {json_file_path}")
            else:
                print(f"保存JSON文件失败")
        else:
            # 使用默认路径
            default_path = get_json_file_path()
            success = save_json_data(subscription_info)
            if success:
                print(f"检测结果已保存到JSON文件: {default_path}")
            else:
                print(f"保存JSON文件失败")

    except Exception as e:
        print(f"保存结果时出错: {str(e)}")


def main():
    """主函数 - 重构版本"""
    import argparse

    # 解析命令行参数
    parser = argparse.ArgumentParser(description="E5订阅监控工具")
    parser.add_argument("--json-path", type=str, help="e5_sub.json文件的完整路径")
    args = parser.parse_args()

    start_time = time.time()

    # 初始化环境
    email_log, users, access_token, subscription_info, error_msg = (
        initialize_environment()
    )

    if error_msg:
        print(f"错误: {error_msg}")
        return

    # 显示订阅状态
    display_subscription_status(subscription_info, start_time)

    # 检查续期是否成功
    is_renewed, previous_info, renewal_message = check_renewal_success(
        subscription_info, args.json_path
    )
    print(f"\n{renewal_message}")

    # 如果续期成功，发送续期成功邮件
    renewal_success_count = 0
    renewal_failure_count = 0
    if is_renewed:
        print("检测到续期成功，正在发送通知邮件...")
        renewal_success_count, renewal_failure_count = send_renewal_success_emails(
            users, subscription_info
        )

    # 判断是否需要发送常规邮件
    should_send, email_reason = should_send_email_notification(subscription_info)

    # 处理用户邮件
    email_sent_count, email_skipped_count, updated_email_log = process_user_emails(
        users, email_log, subscription_info, should_send, email_reason
    )

    # 保存结果
    save_results(updated_email_log, subscription_info, email_sent_count, args.json_path)

    # 显示统计信息
    total_sent = email_sent_count + renewal_success_count
    total_skipped = email_skipped_count + renewal_failure_count
    print(
        f"\n邮件发送统计: 成功发送 {total_sent} 封 (常规:{email_sent_count},续期:{renewal_success_count}), "
        f"跳过 {total_skipped} 封 (常规:{email_skipped_count},续期:{renewal_failure_count})"
    )


if __name__ == "__main__":
    main()
