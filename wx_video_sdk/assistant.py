import csv
import logging
import os
import random
import time
import traceback
from typing import Dict, List, Optional, Set

from wx_video_sdk.client import WXVideoClient
from wx_video_sdk.models import AppConfig
from wx_video_sdk.utils import (
    save_video_report,
    is_within_days,
    mkdir_if_not_exist,
    parse_timestamp,
)

class WXVideoAssistant:
    def __init__(self, client: WXVideoClient, config: AppConfig):
        self.client = client
        self.config = config
        self.running = True
        self.last_task_time = {}
        self.video_data_cache = {}
        self.private_already_sender: Set[str] = set()
        self.comment_already_sender: Set[str] = set()

    def load_already_senders(self):
        """Pre-load historical data to avoid duplicate replies."""
        logging.info("Loading historical interactions to prevent duplicate replies...")
        try:
            # Private messages
            history_msgs = self.client.get_history_private_msgs()
            reply_text = self.config.auto_send_private_msg.auto_send_private_msg
            for msg in history_msgs:
                if msg.get("rawContent") == reply_text:
                    self.private_already_sender.add(msg.get("sessionId"))

            # Comments
            video_list = self.client.get_video_list()
            comment_text = self.config.auto_send_comment.auto_send_comment_text
            for video in video_list:
                export_id = video["exportId"]
                comments = self.client.get_comment_list(export_id)
                for comment in comments:
                    for level2 in comment.get("levelTwoComment", []):
                        if level2.get("commentContent") == comment_text:
                            self.comment_already_sender.add(comment["commentId"])
                            break
            logging.info(f"Loaded {len(self.private_already_sender)} private and {len(self.comment_already_sender)} comment historical records.")
        except Exception as e:
            logging.error(f"Failed to load historical senders: {e}")

    def should_run_task(self, task_name: str, interval: int) -> bool:
        now = time.time()
        if task_name not in self.last_task_time or now - self.last_task_time[task_name] >= interval:
            self.last_task_time[task_name] = now
            return True
        return False

    def run_once(self):
        """Execute all enabled tasks once."""
        now = time.time()

        # Heartbeat
        if self.should_run_task("heartbeat", self.config.run_config.heartbeat_interval):
            self.client.heartbeat()
            logging.log(15, f"Heartbeat check - {parse_timestamp(now)}")

        # Video Data Export & Report
        if self.should_run_task("video_report", 300):
            self._handle_video_reports()

        # Data Export to CSV
        if self.config.data_export.export_target == 1:
            if self.should_run_task("data_export", self.config.data_export.export_interval):
                self.export_video_data()

        # Video Visibility
        if self.config.auto_video_visible.visible_target == 1:
            if self.should_run_task("video_visible", self.config.auto_video_visible.task_interval):
                self._handle_video_visibility()

        # Comment Auto-Reply
        if self.config.auto_send_comment.comment_target == 1:
            if self.should_run_task("comment", self.config.auto_send_comment.task_interval):
                self._handle_comment_replies()

        # Private Message Auto-Reply
        if self.config.auto_send_private_msg.private_msg_target == 1:
            if self.should_run_task("private_msg", self.config.auto_send_private_msg.task_interval):
                self._handle_private_messages()

    def _handle_video_reports(self):
        video_list = self.client.get_video_list()
        self._update_video_data_cache(video_list)
        report_days = self.config.run_config.create_video_report_days
        
        for video in video_list:
            if is_within_days(report_days, time.time(), video["createTime"]):
                save_video_report(video, export_path=self.config.data_export.export_path)
        logging.info(f"Updated video reports for {len(video_list)} videos.")

    def _handle_video_visibility(self):
        days = self.config.auto_video_visible.auto_video_visible_days
        max_count = self.config.auto_video_visible.max_video_count
        target_type = self.config.auto_video_visible.video_visible_type
        
        for video in self.client.iter_videos():
            if video["readCount"] > max_count and is_within_days(days, time.time(), video["createTime"]):
                self.client.update_video_visible(video["objectId"], target_type)
                logging.info(f"Updated video {video['objectId']} visibility to {target_type}")

    def _handle_comment_replies(self):
        conf = self.config.auto_send_comment
        # Using the new generator-based approach
        for video, comment in self.client.iter_comments():
            if comment["commentId"] in self.comment_already_sender:
                continue
            
            if not is_within_days(conf.auto_send_comment_days, time.time(), comment["commentCreatetime"]):
                continue

            is_self = comment["commentNickname"] == self.client.nick_name
            if (conf.self_comment_target == 0 and not is_self) or (conf.self_comment_target == 1 and is_self):
                reply = random.choice(conf.random_replies_list) if conf.random_replies_list else conf.auto_send_comment_text
                try:
                    self.client.send_comment_reply(video["exportId"], comment, reply)
                    self.comment_already_sender.add(comment["commentId"])
                    logging.info(f"Replied to comment by {comment['commentNickname']}: {reply}")
                except Exception as e:
                    logging.error(f"Failed to reply to comment: {e}")

    def _handle_private_messages(self):
        conf = self.config.auto_send_private_msg
        for msg in self.client.iter_new_messages():
            session_id = msg["sessionId"]
            if session_id in self.private_already_sender:
                continue
            
            if not is_within_days(conf.auto_send_msg_days, time.time(), msg["ts"]):
                continue

            try:
                sent = False
                if conf.private_msg_target == 1:
                    reply = random.choice(conf.random_replies_list) if conf.random_replies_list else conf.auto_send_private_msg
                    self.client.send_private_msg(session_id, msg["toUsername"], msg["fromUsername"], reply)
                    sent = True
                    logging.info(f"Sent private message to {msg['fromUsername']}: {reply}")

                if conf.private_img_target == 1 and os.path.exists(conf.auto_send_img_path):
                    self.client.send_private_img(session_id, msg["toUsername"], msg["fromUsername"], conf.auto_send_img_path)
                    sent = True
                    logging.info(f"Sent private image to {msg['fromUsername']}")

                if sent:
                    self.private_already_sender.add(session_id)
            except Exception as e:
                logging.error(f"Failed to send private message: {e}")

    def _update_video_data_cache(self, video_list):
        for video in video_list:
            vid = video.get("objectId", "unknown")
            if vid not in self.video_data_cache:
                self.video_data_cache[vid] = []
            
            self.video_data_cache[vid].append({
                "timestamp": time.time(),
                "time": parse_timestamp(time.time()),
                "title": video.get("desc", {}).get("description", ""),
                "create_time": parse_timestamp(video.get("createTime", 0)),
                "read_count": video.get("readCount", 0),
                "like_count": video.get("likeCount", 0),
                "fav_count": video.get("favCount", 0),
                "forward_count": video.get("forwardCount", 0),
                "comment_count": video.get("commentCount", 0),
            })

    def export_video_data(self):
        if not self.video_data_cache:
            return
        
        try:
            mkdir_if_not_exist(self.config.data_export.export_path)
            timestamp = parse_timestamp(time.time(), "%Y%m%d_%H%M%S")
            export_file = os.path.join(self.config.data_export.export_path, f"video_stats_{timestamp}.csv")

            with open(export_file, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(["Video ID", "Title", "Created At", "Data Time", "Reads", "Likes", "Favs", "Forwards", "Comments"])
                for vid, points in self.video_data_cache.items():
                    if points:
                        latest = points[-1]
                        writer.writerow([vid, latest["title"], latest["create_time"], latest["time"], latest["read_count"],
                                       latest["like_count"], latest["fav_count"], latest["forward_count"], latest["comment_count"]])
            logging.info(f"Data exported to {export_file}")
        except Exception as e:
            logging.error(f"Failed to export data: {e}")

    def stop(self):
        self.running = False
        if self.config.data_export.export_target == 1:
            self.export_video_data()

    def start_loop(self):
        logging.info("Starting Video Assistant loop... (Press Ctrl+C to stop)")
        while self.running:
            try:
                self.run_once()
                time.sleep(1)
            except KeyboardInterrupt:
                break
            except Exception as e:
                logging.error(f"Error in loop: {e}")
                logging.error(traceback.format_exc())
                time.sleep(5)
        self.stop()
