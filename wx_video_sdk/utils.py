import hashlib
import logging
import os
import time
from typing import Any, Dict, Optional
from qrcode.main import QRCode
from datetime import datetime, timedelta

from wx_video_sdk.api_fields import WxVApiFields

def create_qc_code(url: str, save_img: bool = False, save_img_filename: str = "qrcode.png"):
    """Generate and display QR code."""
    qr = QRCode(box_size=10, border=2)
    qr.add_data(url)

    if save_img:
        img = qr.make_image(fill_color="black", back_color="white")
        img.save(save_img_filename)
    
    # Print to console
    qr.print_ascii()


def is_within_days(days: int, new_timestamp: float, old_timestamp: float) -> bool:
    """Check if old_timestamp is within 'days' of new_timestamp."""
    new_date = datetime.fromtimestamp(new_timestamp)
    old_date = datetime.fromtimestamp(old_timestamp)
    delta = new_date - old_date
    return delta <= timedelta(days=days)


def get_sha256_hash_of_file(file_path: str) -> str:
    """Calculate SHA256 of a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def parse_timestamp(timestamp: float, custom_strfmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Format timestamp to string."""
    dt = datetime.fromtimestamp(timestamp)
    return dt.strftime(custom_strfmt)


def mkdir_if_not_exist(path: str) -> None:
    """Create directory if it doesn't exist."""
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)


def is_dev() -> bool:
    """Check if in development mode via environment variable."""
    return os.environ.get("WX_SDK_DEV", "0") == "1"


def setLoggingDefaultConfig(log_level: Optional[int] = None, log_dir: str = "./logs") -> None:
    """Set default logging configuration."""
    level = log_level or (15 if is_dev() else logging.INFO)
    logging.addLevelName(15, "WX_DEBUG")

    handlers = [logging.StreamHandler()]
    
    try:
        mkdir_if_not_exist(log_dir)
        log_file = os.path.join(log_dir, f"sdk-{parse_timestamp(time.time(), '%Y%m%d-%H%M%S')}.log")
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))
    except Exception as e:
        print(f"Warning: Failed to setup file logging: {e}")

    logging.basicConfig(
        level=level,
        format="[%(asctime)s] %(name)s [%(levelname)s] %(message)s",
        handlers=handlers
    )


def generate_video_report_data(video: Dict[str, Any]) -> Dict[str, Any]:
    """Extract video data without side effects."""
    desc = video.get("desc", {})
    return {
        "title": desc.get("description", "Untitled"),
        "like_count": video.get("likeCount", 0),
        "favorite_count": video.get("favCount", 0),
        "comment_count": video.get("commentCount", 0),
        "read_count": video.get("readCount", 0),
        "forward_count": video.get("forwardCount", 0),
        "create_time": parse_timestamp(video.get("createTime", 0)),
        "update_time": parse_timestamp(time.time()),
        "raw_create_time": video.get("createTime", 0)
    }

def format_video_report_text(data: Dict[str, Any]) -> str:
    """Format report to string."""
    return (
        f"Data Report - {data['update_time']}\n"
        f"-----------------------------------\n"
        f"Title: {data['title']}\n"
        f"Created: {data['create_time']}\n"
        f"Reads:   {data['read_count']}\n"
        f"Likes:   {data['like_count']}\n"
        f"Favs:    {data['favorite_count']}\n"
        f"Forwards: {data['forward_count']}\n"
        f"Comments: {data['comment_count']}\n"
    )

def save_video_report(video: Dict[str, Any], export_path: str = "./视频数据") -> str:
    """Save report to file."""
    data = generate_video_report_data(video)
    content = format_video_report_text(data)
    mkdir_if_not_exist(export_path)
    
    timestamp_str = parse_timestamp(data['raw_create_time'], '%Y%m%d_%H%M%S')
    safe_title = "".join([c for c in data['title'] if c.isalnum() or c in (' ', '-', '_')]).strip()[:50]
    file_path = os.path.join(export_path, f"report_{safe_title}_{timestamp_str}.txt")
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    return file_path


def create_msg_tip(url: str, data: Dict[str, Any]) -> str:
    """Helper for logging URL simplified names."""
    if url == WxVApiFields.PrivateMsg.send_private_msg:
        msg_pack = data.get("msgPack", {})
        if msg_pack.get("msgType") == 3:
            return "/private-msg/send-private-img"
        return "/private-msg/send-private-msg"
    return url


def install_ssl_cert() -> bool:
    """Attempt to setup SSL environment for requests."""
    import ssl
    import certifi
    try:
        os.environ['SSL_CERT_FILE'] = certifi.where()
        os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()
        ssl._create_default_https_context = ssl._create_unverified_context
        logging.info("SSL environment configured.")
        return True
    except Exception as e:
        logging.error(f"Failed to configure SSL: {e}")
        return False
