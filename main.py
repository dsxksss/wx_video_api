import os
import time
import toml
from wx_video_sdk import WXVideoSDK
from wx_video_sdk.utils import is_within_days


def read_config(file_path):
    if not os.path.exists(file_path):
        print("配置文件读取失败, 请创建config.tmol配置文件")
        input("按任意键结束")

    config = toml.load(file_path)

    # 获取run_config部分的值
    run_delay = config["run_config"]["run_delay"]

    # 获取custom_config部分的值
    days = config["custom_config"]["days"]
    max_video_count = config["custom_config"]["max_video_count"]
    video_visible_type = config["custom_config"]["video_visible_type"]
    auto_send_comment_text = config["custom_config"]["auto_send_comment_text"]
    auto_send_private_msg = config["custom_config"]["auto_send_private_msg"]
    auto_send_img_path = config["custom_config"]["auto_send_img_path"]

    return (
        run_delay,
        days,
        max_video_count,
        video_visible_type,
        auto_send_comment_text,
        auto_send_private_msg,
        auto_send_img_path,
    )


if __name__ == "__main__":
    try:
        print("视频号助手脚本运行中...(ctrl+c或关闭窗口结束脚本)")
        (
            run_delay,
            days,
            max_video_count,
            video_visible_type,
            auto_send_comment_text,
            auto_send_private_msg,
            auto_send_img_path,
        ) = read_config("./config.toml")

        sdk = WXVideoSDK()

        # 载入历史聊天中已经发送过的用户
        sdk.load_private_history_already_senders(auto_send_private_msg)
        sdk.load_comment_already_senders(auto_send_comment_text)

        def update_video_list_visible_to_public(
            sdk: WXVideoSDK, object_id, read_count, create_time
        ):
            current_timestamp = round(float(time.time()))
            video_create_timestamp = create_time

            if is_within_days(
                days=days,
                new_timestamp=current_timestamp,
                old_timestamp=video_create_timestamp,
            ):
                sdk.change_video_visible(object_id, video_visible_type)

        def send_ones_custom_video_comment(sdk: WXVideoSDK, export_id, comment):
            if not comment["commentId"] in sdk.comment_already_sender:
                sdk.send_comment(
                    export_id=export_id,
                    comment=comment,
                    comment_content=auto_send_comment_text,
                )
                sdk.comment_already_sender.add(comment["commentId"])

        def send_ones_custom_private_msg(
            sdk: WXVideoSDK, session_id: str, from_username: str, to_username: str
        ) -> bool:
            if session_id not in sdk.private_already_sender:
                sdk.send_private_msg(
                    session_id=session_id,
                    from_username=from_username,
                    to_username=to_username,
                    msg_content=auto_send_private_msg,
                )
                sdk.send_private_img(
                    session_id=session_id,
                    from_username=from_username,
                    to_username=to_username,
                    img_path=auto_send_img_path,
                )
                return True
            else:
                return False

        while True:
            # 全局运行间隔

            time.sleep(max(1, run_delay // 3))
            sdk.on_video_readcount_upper_do(
                max_video_count, update_video_list_visible_to_public
            )
            time.sleep(max(1, run_delay // 3))
            sdk.on_video_comment_do(send_ones_custom_video_comment)
            time.sleep(max(1, run_delay // 3))
            sdk.on_get_new_msg_do(send_ones_custom_private_msg)
    except Exception as e:
        print(f"脚本崩溃: {e}")
        input("按任意键结束")
