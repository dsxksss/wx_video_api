from dataclasses import dataclass, field
from typing import List, Optional
import toml
import os

@dataclass
class RunConfig:
    run_delay: int = 4
    create_video_report_days: int = 2
    heartbeat_interval: int = 60
    verbose_logging: int = 0

@dataclass
class AutoVideoVisibleConfig:
    visible_target: int = 1
    auto_video_visible_days: int = 2
    max_video_count: int = 5500
    video_visible_type: int = 3
    task_interval: int = 300

@dataclass
class AutoSendCommentConfig:
    comment_target: int = 1
    self_comment_target: int = 0
    auto_send_comment_days: int = 2
    auto_send_comment_text: str = "感谢您的评论"
    task_interval: int = 120
    random_replies: str = ""
    
    @property
    def random_replies_list(self) -> List[str]:
        return self.random_replies.split(";") if self.random_replies else []

@dataclass
class AutoSendPrivateMsgConfig:
    private_msg_target: int = 1
    private_img_target: int = 1
    auto_send_msg_days: int = 1
    auto_send_private_msg: str = "你好，感谢私信"
    auto_send_img_path: str = "./icon.png"
    task_interval: int = 60
    random_replies: str = ""
    
    @property
    def random_replies_list(self) -> List[str]:
        return self.random_replies.split(";") if self.random_replies else []

@dataclass
class DataExportConfig:
    export_target: int = 1
    export_interval: int = 3600
    export_path: str = "./视频数据"
    export_csv: int = 1

@dataclass
class AppConfig:
    run_config: RunConfig = field(default_factory=RunConfig)
    auto_video_visible: AutoVideoVisibleConfig = field(default_factory=AutoVideoVisibleConfig)
    auto_send_comment: AutoSendCommentConfig = field(default_factory=AutoSendCommentConfig)
    auto_send_private_msg: AutoSendPrivateMsgConfig = field(default_factory=AutoSendPrivateMsgConfig)
    data_export: DataExportConfig = field(default_factory=DataExportConfig)

    @classmethod
    def load_from_toml(cls, file_path: str) -> 'AppConfig':
        if not os.path.exists(file_path):
            return cls()
        
        try:
            data = toml.load(file_path)
            
            def filter_keys(cls_type, d):
                valid_keys = cls_type.__dataclass_fields__.keys()
                return {k: v for k, v in d.items() if k in valid_keys}

            return cls(
                run_config=RunConfig(**filter_keys(RunConfig, data.get("run_config", {}))),
                auto_video_visible=AutoVideoVisibleConfig(**filter_keys(AutoVideoVisibleConfig, data.get("auto_video_visible", {}))),
                auto_send_comment=AutoSendCommentConfig(**filter_keys(AutoSendCommentConfig, data.get("auto_send_comment", {}))),
                auto_send_private_msg=AutoSendPrivateMsgConfig(**filter_keys(AutoSendPrivateMsgConfig, data.get("auto_send_private_msg", {}))),
                data_export=DataExportConfig(**filter_keys(DataExportConfig, data.get("data_export", {})))
            )
        except Exception as e:
            print(f"Warning: Failed to load config from {file_path} ({e}), using defaults.")
            return cls()
