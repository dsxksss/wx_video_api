import logging
import os
import sys
import time
import traceback
import toml
import questionary
import signal
import datetime
import random
import csv
import urllib3
from wx_video_sdk import WXVideoSDK
from wx_video_sdk.utils import (
    create_video_report,
    is_dev,
    is_within_days,
    mkdir_if_not_exist,
    setLoggingDefaultConfig,
    parse_timestamp,
    install_ssl_cert,
)

# 禁用SSL证书验证警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def read_config(file_path):
    try:
        config = toml.load(file_path)
        logging.info(f"配置文件 [ {file_path} ] 已载入.")

        # 获取run_config部分的值
        run_delay = config["run_config"]["run_delay"]
        create_video_report_days = config["run_config"]["create_video_report_days"]
        heartbeat_interval = config["run_config"].get("heartbeat_interval", 60)
        verbose_logging = config["run_config"].get("verbose_logging", 0)

        # 获取auto_video_visible部分的值
        visible_target = config["auto_video_visible"]["visible_target"]
        auto_video_visible_days = config["auto_video_visible"][
            "auto_video_visible_days"
        ]
        max_video_count = config["auto_video_visible"]["max_video_count"]
        video_visible_type = config["auto_video_visible"]["video_visible_type"]
        video_task_interval = config["auto_video_visible"].get("task_interval", 300)

        # 获取auto_send_comment部分的值
        comment_target = config["auto_send_comment"]["comment_target"]
        self_comment_target = config["auto_send_comment"]["self_comment_target"]
        auto_send_comment_days = config["auto_send_comment"]["auto_send_comment_days"]
        auto_send_comment_text = config["auto_send_comment"]["auto_send_comment_text"]
        comment_task_interval = config["auto_send_comment"].get("task_interval", 120)
        comment_random_replies = config["auto_send_comment"].get("random_replies", "")

        # 获取auto_send_private_msg部分的值
        private_msg_target = config["auto_send_private_msg"]["private_msg_target"]
        private_img_target = config["auto_send_private_msg"]["private_img_target"]
        auto_send_msg_days = config["auto_send_private_msg"]["auto_send_msg_days"]
        auto_send_private_msg = config["auto_send_private_msg"]["auto_send_private_msg"]
        auto_send_img_path = config["auto_send_private_msg"]["auto_send_img_path"]
        private_msg_task_interval = config["auto_send_private_msg"].get(
            "task_interval", 60
        )
        private_msg_random_replies = config["auto_send_private_msg"].get(
            "random_replies", ""
        )

        # 获取data_export部分的值
        export_target = config.get("data_export", {}).get("export_target", 1)
        export_interval = config.get("data_export", {}).get("export_interval", 3600)
        export_path = config.get("data_export", {}).get("export_path", "./视频数据")
        export_csv = config.get("data_export", {}).get("export_csv", 1)

        return (
            run_delay,
            create_video_report_days,
            heartbeat_interval,
            verbose_logging,
            visible_target,
            auto_video_visible_days,
            max_video_count,
            video_visible_type,
            video_task_interval,
            comment_target,
            self_comment_target,
            auto_send_comment_days,
            auto_send_comment_text,
            comment_task_interval,
            comment_random_replies,
            private_msg_target,
            private_img_target,
            auto_send_msg_days,
            auto_send_private_msg,
            private_msg_task_interval,
            private_msg_random_replies,
            auto_send_img_path,
            export_target,
            export_interval,
            export_path,
            export_csv,
        )
    except Exception as e:
        logging.error(f"读取配置文件失败: {str(e)}")
        raise


class VideoAssistant:
    def __init__(self, config_path):
        self.config_path = config_path
        self.sdk = None
        self.running = True
        self.last_task_time = {}  # 记录各任务上次执行时间
        self.video_data_cache = {}  # 缓存视频数据用于导出

        # 读取配置
        self.load_config()

        # 初始化日志
        self.setup_logging()

        # 设置信号处理
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

    def signal_handler(self, sig, frame):
        logging.info("接收到终止信号，程序正在优雅退出...")
        # 导出最终数据
        if self.export_target == 1 and hasattr(self, "sdk") and self.sdk:
            self.export_video_data()
        self.running = False

    def setup_logging(self):
        setLoggingDefaultConfig()
        if self.verbose_logging == 1:
            logging.getLogger().setLevel(15)  # 设置为详细日志级别
        else:
            logging.getLogger().setLevel(logging.INFO)

    def load_config(self):
        (
            self.run_delay,
            self.create_video_report_days,
            self.heartbeat_interval,
            self.verbose_logging,
            self.visible_target,
            self.auto_video_visible_days,
            self.max_video_count,
            self.video_visible_type,
            self.video_task_interval,
            self.comment_target,
            self.self_comment_target,
            self.auto_send_comment_days,
            self.auto_send_comment_text,
            self.comment_task_interval,
            self.comment_random_replies,
            self.private_msg_target,
            self.private_img_target,
            self.auto_send_msg_days,
            self.auto_send_private_msg,
            self.private_msg_task_interval,
            self.private_msg_random_replies,
            self.auto_send_img_path,
            self.export_target,
            self.export_interval,
            self.export_path,
            self.export_csv,
        ) = read_config(self.config_path)

        # 处理随机回复列表
        self.comment_random_replies_list = (
            self.comment_random_replies.split(";")
            if self.comment_random_replies
            else []
        )
        self.private_msg_random_replies_list = (
            self.private_msg_random_replies.split(";")
            if self.private_msg_random_replies
            else []
        )

        # 确保导出目录存在
        if self.export_target == 1:
            mkdir_if_not_exist(self.export_path)

    def login(self):
        caches_dir = "./caches/"
        mkdir_if_not_exist(caches_dir)
        options = os.listdir(caches_dir)
        selected = "None"

        if len(options) > 0:
            options.append("扫码登录新账号")
            selected = questionary.select(
                "检测到存在账号缓存，请使用上下方向键选择你要登录的账号:", options
            ).ask()

        if selected is None:
            logging.info("用户取消登录")
            return False

        if not selected.endswith(".json"):
            selected = f"{selected}.json"

        try:
            self.sdk = WXVideoSDK(os.path.join(caches_dir, selected))

            # 载入历史聊天中已经发送过的用户
            self.sdk.load_private_history_already_senders(self.auto_send_private_msg)
            self.sdk.load_comment_already_senders(self.auto_send_comment_text)

            return True
        except Exception as e:
            logging.error(f"登录失败: {str(e)}")
            return False

    def update_video_list_visible(self, object_id, read_count, create_time):
        current_timestamp = round(float(time.time()))
        video_create_timestamp = create_time

        if is_within_days(
            days=self.auto_video_visible_days,
            new_timestamp=current_timestamp,
            old_timestamp=video_create_timestamp,
        ):
            try:
                if self.sdk:
                    self.sdk.change_video_visible(object_id, self.video_visible_type)
                    logging.info(
                        f"已将视频 {object_id} 的可见性设置为 {self.video_visible_type}"
                    )
            except Exception as e:
                logging.error(f"修改视频可见性失败: {str(e)}")

    def get_random_comment_reply(self):
        """获取随机评论回复内容"""
        if self.comment_random_replies_list:
            return random.choice(self.comment_random_replies_list)
        return self.auto_send_comment_text

    def get_random_private_msg(self):
        """获取随机私信回复内容"""
        if self.private_msg_random_replies_list:
            return random.choice(self.private_msg_random_replies_list)
        return self.auto_send_private_msg

    def send_ones_custom_video_comment(self, export_id, comment):
        if (
            self.sdk
            and not comment["commentId"] in self.sdk.comment_already_sender
            and is_within_days(
                days=self.auto_send_comment_days,
                new_timestamp=round(float(time.time())),
                old_timestamp=float(comment["commentCreatetime"]),
            )
        ):
            try:
                # 获取随机回复内容
                reply_content = self.get_random_comment_reply()

                if self.self_comment_target == 0:
                    if comment["commentNickname"] != self.sdk.nick_name:
                        self.sdk.send_comment(
                            export_id=export_id,
                            comment=comment,
                            comment_content=reply_content,
                        )
                        self.sdk.comment_already_sender.add(comment["commentId"])
                        logging.info(
                            f"已回复评论: {comment['commentNickname']} -> {reply_content}"
                        )
                elif self.self_comment_target == 1:
                    if comment["commentNickname"] == self.sdk.nick_name:
                        self.sdk.send_comment(
                            export_id=export_id,
                            comment=comment,
                            comment_content=reply_content,
                        )
                        self.sdk.comment_already_sender.add(comment["commentId"])
                        logging.info(f"已回复自己的评论 -> {reply_content}")
            except Exception as e:
                logging.error(f"回复评论失败: {str(e)}")

    def send_ones_custom_private_msg(
        self, session_id, from_username, to_username, msg_ts
    ):
        if (
            self.sdk
            and session_id not in self.sdk.private_already_sender
            and is_within_days(
                days=self.auto_send_msg_days,
                new_timestamp=round(float(time.time())),
                old_timestamp=float(msg_ts),
            )
        ):
            try:
                sent = False
                if self.private_msg_target == 1:
                    # 获取随机回复内容
                    reply_content = self.get_random_private_msg()

                    self.sdk.send_private_msg(
                        session_id=session_id,
                        from_username=from_username,
                        to_username=to_username,
                        msg_content=reply_content,
                    )
                    sent = True
                    logging.info(
                        f"已发送私信文本给: {from_username} -> {reply_content}"
                    )

                if self.private_img_target == 1:
                    if os.path.exists(self.auto_send_img_path):
                        self.sdk.send_private_img(
                            session_id=session_id,
                            from_username=from_username,
                            to_username=to_username,
                            img_path=self.auto_send_img_path,
                        )
                        sent = True
                        logging.info(f"已发送私信图片给: {from_username}")
                    else:
                        logging.error(f"图片路径不存在: {self.auto_send_img_path}")

                if sent:
                    self.sdk.private_already_sender.add(session_id)
                return sent
            except Exception as e:
                logging.error(f"发送私信失败: {str(e)}")

        return False

    def should_run_task(self, task_name, interval_seconds=None):
        """判断是否应该执行特定任务"""
        now = time.time()
        if interval_seconds is None:
            interval_seconds = max(1, self.run_delay)

        if (
            task_name not in self.last_task_time
            or now - self.last_task_time[task_name] >= interval_seconds
        ):
            self.last_task_time[task_name] = now
            return True
        return False

    def update_video_data_cache(self, video_list):
        """更新视频数据缓存，用于后续的数据导出"""
        for video in video_list:
            video_id = video.get("objectId", "unknown")
            if video_id not in self.video_data_cache:
                self.video_data_cache[video_id] = []

            # 添加带时间戳的数据点
            self.video_data_cache[video_id].append(
                {
                    "timestamp": time.time(),
                    "time": parse_timestamp(time.time()),
                    "title": video.get("desc", {}).get("description", ""),
                    "create_time": parse_timestamp(video.get("createTime", 0)),
                    "read_count": video.get("readCount", 0),
                    "like_count": video.get("likeCount", 0),
                    "fav_count": video.get("favCount", 0),
                    "forward_count": video.get("forwardCount", 0),
                    "comment_count": video.get("commentCount", 0),
                }
            )

    def export_video_data(self):
        """导出视频数据到CSV文件"""
        if not self.video_data_cache:
            logging.info("没有可导出的视频数据")
            return

        try:
            timestamp = parse_timestamp(time.time(), "%Y%m%d_%H%M%S")
            export_file = f"{self.export_path}/视频数据统计_{timestamp}.csv"

            with open(export_file, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                # 写入表头
                writer.writerow(
                    [
                        "视频ID",
                        "视频标题",
                        "创建时间",
                        "数据时间",
                        "播放量",
                        "点赞数",
                        "收藏数",
                        "转发数",
                        "评论数",
                    ]
                )

                # 写入每个视频的数据
                for video_id, data_points in self.video_data_cache.items():
                    # 取最新的一条数据
                    if data_points:
                        latest = data_points[-1]
                        writer.writerow(
                            [
                                video_id,
                                latest["title"],
                                latest["create_time"],
                                latest["time"],
                                latest["read_count"],
                                latest["like_count"],
                                latest["fav_count"],
                                latest["forward_count"],
                                latest["comment_count"],
                            ]
                        )

            logging.info(f"视频数据已导出到: {export_file}")
        except Exception as e:
            logging.error(f"导出视频数据失败: {str(e)}")

    def run(self):
        if not self.login():
            logging.error("登录失败，程序退出")
            return

        logging.info("视频号助手脚本运行中...(ctrl+c或关闭窗口结束脚本)")

        last_heartbeat_time = time.time()
        last_export_time = time.time()

        while self.running:
            try:
                # 定期检查会话状态
                now = time.time()
                if now - last_heartbeat_time >= self.heartbeat_interval:
                    if self.sdk:
                        self.sdk.hepler_merlin_mmdata()
                    last_heartbeat_time = now
                    logging.log(15, f"会话心跳检查 - {parse_timestamp(now)}")

                # 检查数据导出
                if (
                    self.export_target == 1
                    and now - last_export_time >= self.export_interval
                ):
                    self.export_video_data()
                    last_export_time = now

                # 处理视频报告
                if self.should_run_task("video_report", 300):  # 5分钟更新一次视频报告
                    if self.sdk:
                        video_list = self.sdk.get_video_list()
                        # 更新数据缓存
                        self.update_video_data_cache(video_list)
                        for video in video_list:
                            create_video_report(
                                video, video_day=self.create_video_report_days
                            )
                        logging.info(f"已更新视频报告 - {len(video_list)}个视频")

                # 处理视频可见性
                if self.visible_target == 1 and self.should_run_task(
                    "video_visible", self.video_task_interval
                ):
                    logging.log(15, "执行视频可见性任务")
                    if self.sdk:
                        self.sdk.on_video_readcount_upper_do(
                            self.max_video_count, self.update_video_list_visible
                        )

                # 处理评论回复
                if self.comment_target == 1 and self.should_run_task(
                    "comment", self.comment_task_interval
                ):
                    logging.log(15, "执行评论回复任务")
                    if self.sdk:
                        self.sdk.on_video_comment_do(
                            self.send_ones_custom_video_comment
                        )

                # 处理私信回复
                if self.should_run_task("private_msg", self.private_msg_task_interval):
                    logging.log(15, "执行私信回复任务")
                    if self.sdk:
                        self.sdk.on_get_new_msg_do(self.send_ones_custom_private_msg)

                # 休眠一小段时间，避免CPU占用过高
                time.sleep(1)

            except Exception as e:
                logging.error(f"运行过程中发生错误: {str(e)}")
                logging.error(traceback.format_exc())
                # 出错后稍微等待一下再继续
                time.sleep(5)


def main():
    config_path = "./config_test.toml" if is_dev() else "./config.toml"

    try:
        # 尝试安装SSL证书
        install_ssl_cert()
        
        assistant = VideoAssistant(config_path)
        assistant.run()
    except KeyboardInterrupt:
        logging.info("用户手动中断程序")
    except Exception as e:
        logging.error(f"程序崩溃: {str(e)}")
        logging.error(traceback.format_exc())
        input("按任意键结束")
        sys.exit(1)


if __name__ == "__main__":
    main()
