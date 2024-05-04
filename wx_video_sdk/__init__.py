import base64
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
import json
import os
import time
from typing import Any, List
import uuid
import requests
from utils import create_qc_code, get_sha256_hash_of_file, is_within_days
from api_feilds import VideoVisibleTypes, WxVApiFields


class WXVideoSDK:
    uin = "0000000000"
    token = ""
    cookie = {}
    login_cookie = {}
    finder_username = ""
    latitude = 0
    longitude = 0
    city = ""
    trace_key = ""
    private_already_sender = set()
    comment_already_sender = set()

    def __init__(self) -> None:
        self.login()

    def login(self):
        is_can_login = False
        self.get_qrcode()

        while not is_can_login:
            is_can_login = self.create_session()
            time.sleep(2)

    def get_qrcode(self):
        # 获取当前时间戳
        timestamp = int(time.time() * 1000)
        headers = {
            "X-Wechat-Uin": self.uin,
        }
        data = {
            "timestamp": timestamp,
            "_log_finder_uin": "",
            "_log_finder_id": "",
            "rawKeyBuff": None,
            "pluginSessionId": None,
            "scene": 7,
            "reqScene": 7,
        }
        response = requests.post(
            WxVApiFields.Auth.auth_login_code,
            headers=headers,
            data=data,
        )
        response_json = json.loads(response.text)
        self.token = response_json.get("data").get("token")

        if self.token:
            create_qc_code(
                f"https://channels.weixin.qq.com/mobile/confirm_login.html?token={self.token}"
            )
        else:
            print("二维码或token获取失败")

    def create_session(self) -> bool:
        """创建会话
        return true if the session is created successfully
        """
        timestamp = int(time.time() * 1000)
        headers = {
            "X-Wechat-Uin": self.uin,
        }
        data = {
            "token": self.token,
            "timestamp": timestamp,
            "_log_finder_uin": "",
            "_log_finder_id": "",
            "rawKeyBuff": None,
            "pluginSessionId": None,
            "scene": 7,
            "reqScene": 7,
        }
        params = {
            "token": self.token,
            "timestamp": timestamp,
            "_log_finder_uin": "",
            "_log_finder_id": "",
            "scene": 7,
            "reqScene": 7,
        }
        response = requests.post(
            WxVApiFields.Auth.auth_login_status,
            headers=headers,
            data=data,
            params=params,
        )
        res = response.json()
        status = res["data"]["status"]
        acct_status = res["data"]["acctStatus"]

        msg_dict = {
            (0, 0): "未登录",
            (5, 1): "已扫码, 等待确认",
            (1, 1): "登录成功",
            (5, 2): "没有可登录的视频号",
            (4, 0): "二维码已经过期",
            (3, 0): "已取消登录.",
        }

        if status == 1 and acct_status == 1:
            print(msg_dict[(status, acct_status)])
            self.cookie = response.cookies.get_dict()
            if not self.cookie:
                msg = "Cookie获取失败"
                print(msg)
                return False
            self.get_auth_data()
            self.get_x_wechat_uin()
            self.get_login_cookie()
            return True

        print(msg_dict[(status, acct_status)])
        return False

    def get_auth_data(self):
        print("get_auth_data")
        timestamp = int(time.time() * 1000)
        headers = {
            "X-Wechat-Uin": self.uin,
        }
        data = {
            "timestamp": timestamp,
            "_log_finder_uin": "",
            "_log_finder_id": "",
            "rawKeyBuff": None,
            "pluginSessionId": None,
            "scene": 7,
            "reqScene": 7,
        }

        response = requests.post(
            WxVApiFields.Auth.auth_data,
            headers=headers,
            data=data,
            cookies=self.cookie,
        )
        res = response.json()

        # 保存获取的用户标识
        self.finder_username = res["data"]["finderUser"]["finderUsername"]

    def get_x_wechat_uin(self):
        print("get_x_wechat_uin")
        timestamp = int(time.time() * 1000)
        headers = {
            "X-Wechat-Uin": self.uin,
        }
        data = {
            "timestamp": timestamp,
            "_log_finder_uin": "",
            "_log_finder_id": self.finder_username,
            "rawKeyBuff": None,
            "pluginSessionId": None,
            "scene": 7,
            "reqScene": 7,
        }
        response = requests.post(
            WxVApiFields.Helper.helper_upload_params,
            headers=headers,
            data=data,
            cookies=self.cookie,
        )
        res = response.json()
        if not res:
            raise Exception("获取wechat_uin失败")
        self.uin = str(res["data"]["uin"])

    def get_login_cookie(self):
        timestamp = int(time.time() * 1000)
        print("get_login_cookie")
        headers = {"X-Wechat-Uin": self.uin}
        data = {
            "timestamp": timestamp,
            "_log_finder_uin": "",
            "_log_finder_id": self.finder_username,
            "rawKeyBuff": None,
            "pluginSessionId": None,
            "scene": 7,
            "reqScene": 7,
        }

        response = requests.post(
            WxVApiFields.PrivateMsg.get_login_cookie,
            headers=headers,
            data=data,
            cookies=self.cookie,
        )
        res = response.json()
        cookie = res["data"]["cookie"]
        if not cookie:
            print("登录cookie获取失败")

        self.login_cookie = cookie

    def get_video_list(
        self, unread: bool = False, need_comment_count: bool = True
    ) -> List[Any]:
        print("get_video_list")
        timestamp = int(time.time() * 1000)
        headers = {
            "X-Wechat-Uin": self.uin,
        }
        data = {
            "pageSize": 10,
            "currentPage": 1,
            "onlyUnread": unread,
            "userpageType": 3,
            "needAllCommentCount": need_comment_count,
            "forMcn": False,
            "timestamp": timestamp,
            "_log_finder_uin": "",
            "_log_finder_id": self.finder_username,
            "rawKeyBuff": None,
            "pluginSessionId": None,
            "scene": 7,
            "reqScene": 7,
        }
        response = requests.post(
            WxVApiFields.Post.post_list,
            headers=headers,
            data=data,
            cookies=self.cookie,
        )
        res = response.json()
        if not res["data"]["list"]:
            print("视频列表获取失败")

        return res["data"]["list"]

    def get_comment_list(
        self, export_id, row, cb: Any = lambda comment: None
    ) -> List[Any]:
        print("get_comment_list")
        timestamp = str(int(time.time() * 1000))
        headers = {
            "X-Wechat-Uin": self.uin,
            "Content-Type": "application/json",
        }
        data = {
            "lastBuff": "",
            "exportId": export_id,
            "commentSelection": False,
            "forMcn": False,
            "timestamp": timestamp,
            "_log_finder_uin": "",
            "_log_finder_id": self.finder_username,
            "rawKeyBuff": None,
            "pluginSessionId": None,
            "scene": 7,
            "reqScene": 7,
        }
        response = requests.post(
            WxVApiFields.Comment.comment_list,
            headers=headers,
            cookies=self.cookie,
            data=json.dumps(data),
        )
        res = response.json()
        if not res["data"]["comment"]:
            print("评论获取失败")
        return res["data"]["comment"]

    def change_video_visible(self, object_id: str, visible_type: int) -> bool:
        timestamp = str(int(time.time() * 1000))
        headers = {
            "X-Wechat-Uin": self.uin,
            "Content-Type": "application/json",
        }
        data = {
            "objectId": object_id,
            "timestamp": timestamp,
            "visibleType": visible_type,
            "_log_finder_uin": "",
            "_log_finder_id": self.finder_username,
            "rawKeyBuff": None,
            "pluginSessionId": None,
            "scene": 7,
            "reqScene": 7,
        }
        response = requests.post(
            WxVApiFields.Post.post_update_visible,
            headers=headers,
            cookies=self.cookie,
            data=json.dumps(data),
        )
        res = response.json()
        if res["data"]["errorCode"] != 0:
            return False

        return True

    # 回复私信消息
    def send_private_msg(
        self, session_id, from_username, to_username, msg_content: str
    ):
        print("send_private_msg")
        myUUID = str(uuid.uuid4())
        timestamp = str(int(time.time() * 1000))
        headers = {
            "X-Wechat-Uin": self.uin,
            "Content-Type": "application/json",
        }
        data = {
            "msgPack": {
                "sessionId": session_id,
                "fromUsername": from_username,
                "toUsername": to_username,
                "msgType": 1,
                "textMsg": {"content": msg_content},
                "cliMsgId": myUUID,
            },
            "timestamp": timestamp,
            "_log_finder_uin": "",
            "_log_finder_id": self.finder_username,
            "rawKeyBuff": None,
            "pluginSessionId": None,
            "scene": 7,
            "reqScene": 7,
        }
        requests.post(
            WxVApiFields.PrivateMsg.send_private_msg,
            headers=headers,
            data=json.dumps(data),
            cookies=self.cookie,
        )

    def upload_media_info(self, from_username, to_username, file_path) -> Any:
        print("upload_media_info")
        headers = {
            "X-Wechat-Uin": self.uin,
            "Content-Type": "application/json",
        }
        # 生成AES密钥并且转换为 base64 格式以便于存储和传输
        aes_key = base64.b64encode(get_random_bytes(32)).decode()
        with open(file_path, "rb") as file:
            file_size = os.path.getsize(file_path)
            file_md5 = get_sha256_hash_of_file(file_path)
            chunk_size = 512 * 1024
            chunks = -(-file_size // chunk_size)
            img_msg = {}

            for chunk in range(chunks):
                timestamp = str(int(time.time() * 1000))
                file.seek(chunk * chunk_size)
                data = file.read(chunk_size)

                # 将数据编码为 base64
                base64_data = base64.b64encode(data).decode()

                data = {
                    "aesKey": aes_key,
                    "chunk": chunk,
                    "chunks": chunks,
                    "content": f"data:application/octet-stream;base64,{base64_data}",
                    "fromUsername": from_username,
                    "toUsername": to_username,
                    "md5": file_md5,
                    "mediaSize": file_size,
                    "mediaType": 3,
                    "pluginSessionId": None,
                    "rawKeyBuff": None,
                    "reqScene": 7,
                    "scene": 7,
                    "timestamp": timestamp,
                    "_log_finder_id": self.finder_username,
                    "_log_finder_uin": "",
                }

                response = requests.post(
                    WxVApiFields.PrivateMsg.upload_media_info,
                    headers=headers,
                    data=json.dumps(data),
                    cookies=self.cookie,
                )
                res = response.json()
                img_msg = res["data"]["imgMsg"]

            return img_msg

    def send_private_img(
        self, session_id, from_username: str, to_username: str, img_path: str
    ):
        print("send_private_img")

        # 切片上传图片
        img_msg = self.upload_media_info(
            from_username=from_username, to_username=to_username, file_path=img_path
        )
        myUUID = str(uuid.uuid4())
        timestamp = str(int(time.time() * 1000))
        headers = {
            "X-Wechat-Uin": self.uin,
            "Content-Type": "application/json",
        }
        data = {
            "msgPack": {
                "sessionId": session_id,
                "fromUsername": from_username,
                "toUsername": to_username,
                "msgType": 3,
                "imgMsg": img_msg,
                "cliMsgId": myUUID,
            },
            "timestamp": timestamp,
            "_log_finder_uin": "",
            "_log_finder_id": self.finder_username,
            "rawKeyBuff": None,
            "pluginSessionId": None,
            "scene": 7,
            "reqScene": 7,
        }
        requests.post(
            WxVApiFields.PrivateMsg.send_private_msg,
            headers=headers,
            data=json.dumps(data),
            cookies=self.cookie,
        )

    # 回复视频评论
    def send_comment(self, export_id, comment, comment_content: str):
        myUUID = str(uuid.uuid4())
        timestamp = str(int(time.time() * 1000))
        headers = {
            "X-Wechat-Uin": self.uin,
            "Content-Type": "application/json",
        }
        data = {
            "replyCommentId": comment["commentId"],
            "content": comment_content,
            "clientId": myUUID,
            "rootCommentId": comment["commentId"],
            "comment": comment,
            "exportId": export_id,
            "timestamp": timestamp,
            "_log_finder_uin": "",
            "_log_finder_id": self.finder_username,
            "rawKeyBuff": None,
            "pluginSessionId": None,
            "scene": 7,
            "reqScene": 7,
        }
        requests.post(
            WxVApiFields.Comment.create_comment,
            headers=headers,
            cookies=self.cookie,
            data=json.dumps(data),
        )

    #  接收未读的私信消息
    def get_new_msgs(self) -> List[Any]:
        timestamp = int(time.time() * 1000)
        print("get_new_msg")
        headers = {"X-Wechat-Uin": self.uin}
        data = {
            "cookie": self.login_cookie,
            "timestamp": timestamp,
            "_log_finder_uin": "",
            "_log_finder_id": self.finder_username,
            "rawKeyBuff": None,
            "pluginSessionId": None,
            "scene": 7,
            "reqScene": 7,
        }
        response = requests.post(
            WxVApiFields.PrivateMsg.get_new_msg,
            headers=headers,
            data=data,
            cookies=self.cookie,
        )
        res = response.json()
        msgs = res["data"]["msg"]
        return msgs

    #  接收历史私信消息
    def get_history_msgs(self) -> List[Any]:
        timestamp = int(time.time() * 1000)
        print("get_history_msg")
        headers = {"X-Wechat-Uin": self.uin}
        data = {
            "cookie": self.login_cookie,
            "timestamp": timestamp,
            "_log_finder_uin": "",
            "_log_finder_id": self.finder_username,
            "rawKeyBuff": None,
            "pluginSessionId": None,
            "scene": 7,
            "reqScene": 7,
        }
        response = requests.post(
            WxVApiFields.PrivateMsg.get_history_msg,
            headers=headers,
            data=data,
            cookies=self.cookie,
        )
        res = response.json()
        msgs = res["data"]["msg"]
        return msgs

    def on_video_readcount_upper_do(
        self,
        read_count: int,
        cb: Any,
        is_all_video: bool = True,
        object_id: str | None = None,
    ) -> None:
        """_summary_

        Args:
            readcount (int): _description_
            cb (function(sdk: WXVideoSDK,object_id:str,read_count:int,create_time:float)): _description_
            is_all_video (bool, optional): _description_. Defaults to True.
        """
        video_list = self.get_video_list()
        if is_all_video:
            for video in video_list:
                if video["readCount"] > read_count:
                    cb(self, video["objectId"], video["readCount"], video["createTime"])
        elif object_id is not None:
            exist = False
            video_readcount: int = 0
            video_create_time: float = 0
            for video in video_list:
                if object_id == video["objectId"]:
                    exist = True
                    video_readcount = video["readCount"]
                    video_create_time = video["createTime"]
                    break
            if exist:
                if video_readcount > read_count:
                    cb(self, object_id, video_readcount, video_create_time)

    def on_video_comment_do(self, cb: Any):
        video_list = self.get_video_list()
        for video in video_list:
            export_id = video["exportId"]
            # 获取评论列表
            comment_list = self.get_comment_list(export_id, video)
            for comment in comment_list:
                cb(self, export_id, comment)

    def on_get_new_msg_do(self, cb: Any) -> None:
        msgs = sdk.get_new_msgs()

        if msgs:
            for msg in msgs:
                is_sended = cb(
                    self,
                    msg["sessionId"],
                    msg["toUsername"],
                    msg["fromUsername"],
                )
                if is_sended:
                    self.private_already_sender.add(msg["fromUsername"])

    def load_private_history_already_senders(self, send_text: str):
        # 确保消息已经发送过了
        history_msgs = sdk.get_history_msgs()
        for msg in history_msgs:
            if msg["rawContent"] == send_text:
                self.private_already_sender.add(msg["fromUsername"])

    def load_comment_already_senders(self, send_comment: str):
        # 确保消息已经发送过了
        video_list = self.get_video_list()
        for video in video_list:
            exportId = video["exportId"]
            # 获取评论列表
            comment_list = self.get_comment_list(exportId, video)
            for comment in comment_list:
                level_two_comments = comment["levelTwoComment"]
                for level_comment in level_two_comments:
                    if level_comment["commentContent"] == send_comment:
                        self.comment_already_sender.add(comment["commentId"])
                        break


if __name__ == "__main__":
    print("视频号助手脚本运行中...(ctrl+c或关闭窗口结束脚本)")
    sdk = WXVideoSDK()

    run_delay = 4
    days = 2
    max_video_count = 100
    video_visible_type = VideoVisibleTypes.Private

    auto_send_comment_text = "你好我是test 评论回复"
    auto_send_private_msg = "你好我是私信的test IMG"
    auto_send_img_path = r"D:\wx_video_api\QR.png"

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
        print(sdk.private_already_sender)
        print(
            f"对比结果是：{ to_username not in sdk.private_already_sender}"
        )
        if to_username not in sdk.private_already_sender:
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
        time.sleep(run_delay)

        # sdk.on_video_readcount_upper_do(
        #     max_video_count, update_video_list_visible_to_public
        # )

        sdk.on_get_new_msg_do(send_ones_custom_private_msg)

        # sdk.on_video_comment_do(send_ones_custom_video_comment)
