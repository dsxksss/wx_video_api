import hashlib
import logging
import os
import time
from typing import Any
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


def get_sha256_hash_of_file(file_path):
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        # 读取文件直到结束
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()


def parse_timestamp(timestamp, custom_strfmt="%Y-%m-%d %H:%M:%S"):
    # 将时间戳转换为datetime对象
    dt = datetime.fromtimestamp(timestamp)

    # 格式化日期和时间
    formatted = dt.strftime(custom_strfmt)

    return formatted


def mkdir_if_not_exist(path: str) -> None:
    if not os.path.exists(path):
        os.makedirs(path)


def setLoggingDefaultConfig() -> None:
    Log_level = 15

    console_handler = logging.StreamHandler()
    file_handler = logging.FileHandler("./wx_video_sdk.log", encoding="utf-8")

    console_handler.setLevel(Log_level)
    file_handler.setLevel(Log_level)

    console_format = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_format = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    console_handler.setFormatter(console_format)
    file_handler.setFormatter(file_format)

    logging.basicConfig(level=Log_level, handlers=[console_handler, file_handler])


def create_video_report(video: Any, video_day: int):
    video_title = video["desc"]["description"]
    video_like_count = video["likeCount"]
    video_favorite_count = video["favCount"]
    video_comment_count = video["commentCount"]
    video_read_count = video["readCount"]
    video_forward_count = video["forwardCount"]
    video_create_date = parse_timestamp(video["createTime"])
    current_date = parse_timestamp(float(time.time()))

    if is_within_days(
        days=video_day,
        new_timestamp=float(time.time()),
        old_timestamp=video["createTime"],
    ):

        file_path = f"./视频数据"
        mkdir_if_not_exist(file_path)

        with open(
            f"{file_path}/[{video_title}]-[{parse_timestamp(video['createTime'],'%Y_%m_%d_%H_%M_%S')}].txt",
            "w",
            encoding="utf-8",
        ) as w:
            w.write(f"数据更新于: {current_date}\n\n")
            w.write(f"视频标题: {video_title}\n")
            w.write(f"视频创建时间: {video_create_date}\n")
            w.write(f"浏览数: {video_read_count}\n")
            w.write(f"点赞数: {video_like_count}\n")
            w.write(f"推荐数: {video_favorite_count}\n")
            w.write(f"转发数: {video_forward_count}\n")
            w.write(f"评论数: {video_comment_count}\n")


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
