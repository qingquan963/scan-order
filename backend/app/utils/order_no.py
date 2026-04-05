import random
import datetime


def generate_order_number() -> str:
    """生成订单号：年月日时分秒 + 4位随机数"""
    now = datetime.datetime.now()
    timestamp = now.strftime("%Y%m%d%H%M%S")
    rand = random.randint(1000, 9999)  # 4位随机数
    return f"{timestamp}{rand}"
