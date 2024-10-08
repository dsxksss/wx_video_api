import logging
import os
import sys
import time
import traceback
import toml
import questionary
from wx_video_sdk import WXVideoSDK
from wx_video_sdk.utils import (
    create_video_report,
    is_dev,
    is_within_days,
    mkdir_if_not_exist,
    setLoggingDefaultConfig,
)


def read_config(file_path):
    config = toml.load(file_path)

    # 获取run_config部分的值
    run_delay = config["run_config"]["run_delay"]
    create_video_report_days = config["run_config"]["create_video_report_days"]

    # 获取auto_video_visible部分的值
    visible_target = config["auto_video_visible"]["visible_target"]
    auto_video_visible_days = config["auto_video_visible"]["auto_video_visible_days"]
    max_video_count = config["auto_video_visible"]["max_video_count"]
    video_visible_type = config["auto_video_visible"]["video_visible_type"]

    # 获取auto_send_comment部分的值
    comment_target = config["auto_send_comment"]["comment_target"]
    self_comment_target = config["auto_send_comment"]["self_comment_target"]
    auto_send_comment_days = config["auto_send_comment"]["auto_send_comment_days"]
    auto_send_comment_text = config["auto_send_comment"]["auto_send_comment_text"]

    # 获取auto_send_private_msg部分的值
    private_msg_target = config["auto_send_private_msg"]["private_msg_target"]
    private_img_target = config["auto_send_private_msg"]["private_img_target"]
    auto_send_msg_days = config["auto_send_private_msg"]["auto_send_msg_days"]
    auto_send_private_msg = config["auto_send_private_msg"]["auto_send_private_msg"]
    auto_send_img_path = config["auto_send_private_msg"]["auto_send_img_path"]

    return (
        run_delay,
        create_video_report_days,
        visible_target,
        auto_video_visible_days,
        max_video_count,
        video_visible_type,
        comment_target,
        self_comment_target,
        auto_send_comment_days,
        auto_send_comment_text,
        private_msg_target,
        private_img_target,
        auto_send_msg_days,
        auto_send_private_msg,
        auto_send_img_path,
    )


def main():
    config_path = "./config_test.toml" if is_dev() else "./config.toml"

    setLoggingDefaultConfig()
    (
        run_delay,
        create_video_report_days,
        visible_target,
        auto_video_visible_days,
        max_video_count,
        video_visible_type,
        comment_target,
        self_comment_target,
        auto_send_comment_days,
        auto_send_comment_text,
        private_msg_target,
        private_img_target,
        auto_send_msg_days,
        auto_send_private_msg,
        auto_send_img_path,
    ) = read_config(config_path)

    logging.info(f"配置文件 [ {config_path} ] 已载入.")
    logging.info("视频号助手脚本运行中...(ctrl+c或关闭窗口结束脚本)")

    caches_dir = "./caches/"

    mkdir_if_not_exist(caches_dir)
    options = os.listdir(caches_dir)
    selected = "None"

    if len(options) > 0:
        options.append("扫码登录新账号")
        selected = questionary.select(
            "检测到存在账号缓存，请使用上下方向键选择你要登录的账号:", options
        ).ask()
        
    if not selected.endswith(".json"):
        selected = f"{selected}.json"
    sdk = WXVideoSDK(os.path.join(caches_dir, selected))

    # 载入历史聊天中已经发送过的用户
    sdk.load_private_history_already_senders(auto_send_private_msg)
    sdk.load_comment_already_senders(auto_send_comment_text)

    def update_video_list_visible(sdk: WXVideoSDK, object_id, read_count, create_time):
        current_timestamp = round(float(time.time()))
        video_create_timestamp = create_time

        if is_within_days(
            days=auto_video_visible_days,
            new_timestamp=current_timestamp,
            old_timestamp=video_create_timestamp,
        ):
            sdk.change_video_visible(object_id, video_visible_type)

    def send_ones_custom_video_comment(sdk: WXVideoSDK, export_id, comment):
        if not comment["commentId"] in sdk.comment_already_sender and is_within_days(
            days=auto_send_comment_days,
            new_timestamp=round(float(time.time())),
            old_timestamp=float(comment["commentCreatetime"]),
        ):
            if self_comment_target == 0:
                if comment["commentNickname"] != sdk.nick_name:
                    sdk.send_comment(
                        export_id=export_id,
                        comment=comment,
                        comment_content=auto_send_comment_text,
                    )
                    sdk.comment_already_sender.add(comment["commentId"])
            elif self_comment_target == 1:
                if comment["commentNickname"] == sdk.nick_name:
                    sdk.send_comment(
                        export_id=export_id,
                        comment=comment,
                        comment_content=auto_send_comment_text,
                    )
                    sdk.comment_already_sender.add(comment["commentId"])

    def send_ones_custom_private_msg(
        sdk: WXVideoSDK,
        session_id: str,
        from_username: str,
        to_username: str,
        msg_ts: int,
    ) -> bool:

        if session_id not in sdk.private_already_sender and is_within_days(
            days=auto_send_msg_days,
            new_timestamp=round(float(time.time())),
            old_timestamp=float(msg_ts),
        ):
            if private_msg_target == 1:
                sdk.send_private_msg(
                    session_id=session_id,
                    from_username=from_username,
                    to_username=to_username,
                    msg_content=auto_send_private_msg,
                )

            if private_img_target == 1:
                sdk.send_private_img(
                    session_id=session_id,
                    from_username=from_username,
                    to_username=to_username,
                    img_path=auto_send_img_path,
                )
            return True

        return False

    while True:
        # 检查是否session是否断开
        sdk.hepler_merlin_mmdata()

        # 全局运行间隔
        video_list = sdk.get_video_list()
        for video in video_list:
            logging.log(15, "create_video_report_days")
            create_video_report(video, video_day=create_video_report_days)

        if visible_target == 1:
            time.sleep(max(1, run_delay // 3))
            logging.log(15, "update_video_list_visible")
            sdk.on_video_readcount_upper_do(max_video_count, update_video_list_visible)

        if comment_target == 1:
            time.sleep(max(1, run_delay // 3))
            logging.log(15, "send_ones_custom_video_comment")
            sdk.on_video_comment_do(send_ones_custom_video_comment)

        time.sleep(max(1, run_delay // 3))
        logging.log(15, "send_ones_custom_private_msg")
        sdk.on_get_new_msg_do(send_ones_custom_private_msg)


if __name__ == "__main__":
    try:
        main()
    except:
        logging.log(15, "脚本崩溃: %s", traceback.format_exc())
        input("按任意键结束")
        sys.exit(1)
