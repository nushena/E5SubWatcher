import requests
import json
import time
import os
from datetime import datetime, timedelta
import urllib3
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import argparse

# 禁用不安全连接警告（仅在verify=False时需要）
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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
DEFAULT_OUTPUT_DIR = "./Output"  # 默认输出目录

def get_session():
    """创建一个带有重试机制的会话"""
    session = requests.Session()
    retry_strategy = Retry(
        total=MAX_RETRIES,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session

def get_access_token():
    """获取访问令牌"""
    token_url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
    token_data = {
        'grant_type': 'client_credentials',
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'scope': 'https://graph.microsoft.com/.default'
    }
    
    try:
        session = get_session()
        response = session.post(
            token_url, 
            data=token_data, 
            verify=VERIFY_SSL,
            timeout=REQUEST_TIMEOUT
        )
        
        if response.status_code == 200:
            return response.json().get('access_token')
        else:
            print(f"获取令牌失败: {response.status_code}")
            print(response.text)
            return None
    except requests.exceptions.SSLError as ssl_err:
        print(f"SSL错误: {ssl_err}")
        print("提示: 如果这是测试环境，可以尝试将VERIFY_SSL设置为False（不建议在生产环境中使用）")
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
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    # 获取订阅信息
    subscription_url = "https://graph.microsoft.com/v1.0/subscribedSkus"
    try:
        session = get_session()
        response = session.get(
            subscription_url, 
            headers=headers, 
            verify=VERIFY_SSL,
            timeout=REQUEST_TIMEOUT
        )
        
        if response.status_code == 200:
            subscriptions = response.json().get('value', [])
            
            # 查找E5订阅
            for subscription in subscriptions:
                sku_part_number = subscription.get('skuPartNumber', '')
                if 'E5' in sku_part_number:
                    # 获取状态
                    status = "活跃" if subscription.get('capabilityStatus') == "Enabled" else "状态异常！！"
                    consumed = subscription.get('consumedUnits', 0)
                    total = subscription.get('prepaidUnits', {}).get('enabled', 0)
                    
                    # 获取订阅ID
                    subscription_ids = subscription.get('subscriptionIds', [])
                    
                    # 获取详细订阅信息，包括到期时间
                    expiry_info = get_subscription_expiry_info(access_token, subscription_ids)
                    
                    return {
                        "sku_name": sku_part_number,
                        "status": status,
                        "consumed_units": consumed,
                        "total_units": total,
                        "expiry_info": expiry_info,
                        "check_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        "raw_data": subscription
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
    """获取订阅到期信息"""
    if not subscription_ids:
        return {"error": "没有可用的订阅ID"}
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    expiry_info = {}
    
    # 使用第一个订阅ID获取详细信息
    subscription_id = subscription_ids[0]
    
    # 尝试获取订阅的生命周期信息
    try:
        # 获取订阅详细信息
        subscriptions_url = f"https://graph.microsoft.com/v1.0/directory/subscriptions"
        session = get_session()
        response = session.get(
            subscriptions_url, 
            headers=headers, 
            verify=VERIFY_SSL,
            timeout=REQUEST_TIMEOUT
        )
        
        if response.status_code == 200:
            subscriptions = response.json().get('value', [])
            for sub in subscriptions:
                if sub.get('id') == subscription_id:
                    # 获取下一个生命周期日期
                    next_lifecycle_date = sub.get('nextLifecycleDateTime')
                    if next_lifecycle_date:
                        try:
                            expiry_date = datetime.fromisoformat(next_lifecycle_date.replace('Z', '+00:00'))
                            days_left = (expiry_date - datetime.now(expiry_date.tzinfo)).days
                            
                            expiry_info = {
                                "expiry_date": expiry_date.strftime('%Y-%m-%d'),
                                "days_left": days_left,
                                "status": "即将到期" if days_left <= 30 else "正常"
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
                timeout=REQUEST_TIMEOUT
            )
            if response.status_code == 200:
                org_info = response.json().get('value', [{}])[0]
                
                # 检查组织信息中是否有到期日期相关字段
                if 'assignedPlans' in org_info:
                    for plan in org_info.get('assignedPlans', []):
                        if 'Enterprise' in plan.get('servicePlanName', '') and plan.get('capabilityStatus') == 'Enabled':
                            expiry_date = plan.get('assignedDateTime')
                            if expiry_date:
                                try:
                                    # 估计到期时间（通常是从分配日期起一年）
                                    assign_date = datetime.fromisoformat(expiry_date.replace('Z', '+00:00'))
                                    est_expiry = assign_date + timedelta(days=365)
                                    days_left = (est_expiry - datetime.now(assign_date.tzinfo)).days
                                    
                                    expiry_info = {
                                        "expiry_date": est_expiry.strftime('%Y-%m-%d'),
                                        "days_left": days_left,
                                        "status": "估计到期日期",
                                        "note": "这是一个估计值，基于订阅开始日期加一年"
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
            "suggestion": "请登录Microsoft 365管理中心查看准确的到期日期: https://admin.microsoft.com/AdminPortal/Home#/subscriptions"
        }
    
    return expiry_info

def save_to_json(data, filename=None, output_dir=None):
    """将数据保存到JSON文件
    
    Args:
        data: 要保存的数据
        filename: 文件名，如果为None则使用默认值
        output_dir: 输出目录，如果为None则使用默认值
    
    Returns:
        (bool, str): 成功状态和结果信息
    """
    try:
        # 如果没有指定文件名，使用默认配置
        if filename is None:
            filename = JSON_FILENAME
        
        # 如果没有指定输出目录，使用默认配置
        if output_dir is None:
            output_dir = DEFAULT_OUTPUT_DIR
        
        # 确保输出目录存在
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            print(f"已创建目录: {output_dir}")
        
        # 构建完整的文件路径
        file_path = os.path.join(output_dir, filename)
        
        # 创建一个包含时间戳的数据副本
        json_data = data.copy()
        
        # 移除raw_data以减小文件体积，除非你特别需要它
        if "raw_data" in json_data:
            del json_data["raw_data"]
        
        # 检查文件是否存在，如果存在则删除
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"已删除旧文件: {file_path}")
        
        # 写入JSON文件
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=4)
        
        return True, file_path
    except Exception as e:
        return False, str(e)

def main():
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='微软E5订阅状态检测工具')
    parser.add_argument('-o', '--output-dir', dest='output_dir', default=DEFAULT_OUTPUT_DIR,
                        help=f'指定输出目录 (默认: {DEFAULT_OUTPUT_DIR})')
    parser.add_argument('-f', '--filename', dest='filename', default=JSON_FILENAME,
                        help=f'指定输出文件名 (默认: {JSON_FILENAME})')
    args = parser.parse_args()
    
    print("开始检测微软E5订阅状态...")
    start_time = time.time()
    
    # 获取访问令牌
    access_token = get_access_token()
    if not access_token:
        print("获取访问令牌失败，请检查凭据是否正确。")
        print("如果是SSL错误，可能需要检查网络环境或临时禁用SSL验证（修改VERIFY_SSL = False）。")
        return
    
    # 检查订阅状态
    subscription_info = check_subscription_status(access_token)
    
    # 保存结果到JSON文件
    success, result = save_to_json(subscription_info, filename=args.filename, output_dir=args.output_dir)
    if success:
        print(f"检测结果已保存到JSON文件: {result}")
    else:
        print(f"保存JSON文件失败: {result}")
    
    # 显示结果
    if "error" in subscription_info:
        print(f"错误: {subscription_info['error']}")
    else:
        print("\n===== 微软E5订阅状态 =====")
        print(f"订阅类型: {subscription_info['sku_name']}")
        print(f"状态: {subscription_info['status']}")
        print(f"已使用许可证: {subscription_info['consumed_units']}/{subscription_info['total_units']}")
        
        # 显示到期信息
        expiry_info = subscription_info.get('expiry_info', {})
        if "error" in expiry_info:
            print(f"到期信息获取失败: {expiry_info['error']}")
        elif "message" in expiry_info:
            print(f"到期信息: {expiry_info['message']}")
            print(f"建议: {expiry_info['suggestion']}")
        else:
            print(f"到期日期: {expiry_info.get('expiry_date', '未知')}")
            print(f"剩余天数: {expiry_info.get('days_left', '未知')}")
            if expiry_info.get('note'):
                print(f"注意: {expiry_info['note']}")
            
            # 添加到期提醒
            days_left = expiry_info.get('days_left')
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
    
if __name__ == "__main__":
    main()
