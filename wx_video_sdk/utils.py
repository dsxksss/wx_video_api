from qrcode.main import QRCode
from datetime import datetime, timedelta


# 生成二维码
def create_qc_code(
    url: str, save_img: bool = False, save_img_filename: str = "qrcode.png"
):
    qr = QRCode(box_size=10, border=2)

    # 添加链接
    qr.add_data(url)

    if save_img:
        # 生成二维码，默认是常规白底黑色填充的
        img = qr.make_image(fill_color="black", back_color="white")
        # 保存二维码为png格式
        img.save(save_img_filename)

    # 显示二维码至终端
    qr.print_ascii()


def is_within_days(days: int, new_timestamp: float, old_timestamp: float):
    """
    new_timestamp = 1714722954  # 新时间戳
    old_timestamp = 1714636554  # 旧时间戳

    if is_within_days(2, new_timestamp, old_timestamp):
        print("旧时间戳处于新时间戳的前两天之内")
    else:
        print("旧时间戳不在新时间戳的前两天之内")
    """
    # 将时间戳转换为 datetime 对象
    new_date = datetime.fromtimestamp(new_timestamp)
    old_date = datetime.fromtimestamp(old_timestamp)

    # 计算两个日期之间的差值
    delta = new_date - old_date

    # 判断差值是否在两天之内
    return delta <= timedelta(days=days)


if __name__ == "__main__":
    # 旧时间戳
    old_timestamp = 1714636554
    # 新时间戳
    new_timestamp = 1714722954
    assert is_within_days(
        2, new_timestamp, old_timestamp
    ), "旧时间戳应处于新时间戳的前两天之内，可是不符合设定"

    # 旧时间戳
    old_timestamp = 1614636554
    # 新时间戳
    new_timestamp = 1714722954
    assert not is_within_days(
        2, new_timestamp, old_timestamp
    ), "旧时间戳应不处于新时间戳的前两天之内，可是不符合设定"
