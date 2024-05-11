import base64
import logging
import sys
from Crypto.Random import get_random_bytes
from requests.sessions import RequestsCookieJar
import json
import os
import time
from typing import Any, Dict, List
import uuid
import requests
from wx_video_sdk.cache import CacheHandler
from wx_video_sdk.utils import (
    create_qc_code,
    get_sha256_hash_of_file,
    setLoggingDefaultConfig,
)
from wx_video_sdk.api_feilds import WxVApiFields

CACHE_COOKIE_FIELD = "CACHE_COOKIES"


class WXVideoSDK:
    uin = "0000000000"
    nick_name = ""
    token = ""
    cookie = None
    login_cookie = {}
    finder_username = ""
    private_already_sender = set()
    comment_already_sender = set()
    cache_handler: CacheHandler = CacheHandler("./wx_video_sdk_cache.json")

    def __init__(self) -> None:
        self.login()

    def request(self, url, ext_params={}, ext_data={}, ext_handler={}):
        logging.log(15, "request url [%s]", url)
        # 获取当前时间戳
        timestamp = str(int(time.time() * 1000))
        headers = {"X-Wechat-Uin": self.uin}
        data = {
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

        for key, value in ext_params.items():
            params[key] = value

        for key, value in ext_data.items():
            data[key] = value

        for key, value in ext_handler.items():
            headers[key] = value

        response = requests.post(url, headers=headers, data=data, params=params)

        res = response.json()

        if res["errCode"] != 0:
            input("按任意键关闭程序")
            logging.error(
                f"调用 [{url}] 失败!,errCode = [{res['errCode']}], errMsg = {res['errMsg']}"
            )
            sys.exit(1)

        return res["data"]

    def login(self):
        self.cookie, is_can_login = self._get_cookie("self")

        if self.cookie is not None and is_can_login:
            self.get_auth_data()
            self.get_x_wechat_uin()
            self.get_login_cookie()
            return

        self.get_qrcode()

        while not is_can_login:
            is_can_login = self.create_session()
            time.sleep(2)

    def get_qrcode(self):
        res = self.request(WxVApiFields.Auth.auth_login_code)
        self.token = res["token"]

        if self.token:
            create_qc_code(
                f"https://channels.weixin.qq.com/mobile/confirm_login.html?token={self.token}"
            )
        else:
            logging.error("二维码或token获取失败")

    def _set_cookie(self, name, cookie: RequestsCookieJar) -> None:
        cookies_text = "; ".join([f"{name}={value}" for name, value in cookie.items()])

        if self.cache_handler.isExists(name):
            self.cache_handler.updateCache(name, CACHE_COOKIE_FIELD, cookies_text)
        else:
            self.cache_handler.saveCache(name, CACHE_COOKIE_FIELD, cookies_text)

        self.cookies = cookie

    def _get_cookie(self, name) -> tuple[Dict | None, bool]:
        if not self.cache_handler.isExists(name):
            return (None, False)

        cookies_text = self.cache_handler.getCache(name)[CACHE_COOKIE_FIELD]
        cookies = dict(cookie.split("=") for cookie in cookies_text.split("; "))
        self.cookies = cookies
        return (cookies, True)

    def create_session(self) -> bool:
        """创建会话
        return true if the session is created successfully
        """
        timestamp = str(int(time.time() * 1000))
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
            logging.info(msg_dict[(status, acct_status)])
            self.cookie = response.cookies.get_dict()
            self._set_cookie("self", response.cookies)
            if not self.cookie:
                logging.error("Cookie获取失败")
                return False

            # 获取用户信息
            self.get_auth_data()
            return True

        logging.info(msg_dict[(status, acct_status)])
        return False

    def get_auth_data(self):
        timestamp = str(int(time.time() * 1000))
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

        if res["errCode"] != 0:
            logging.error("你的身份验证失败，请关闭程序重新扫描登录")
            self.cache_handler.removeCache("self")
            input("按任意键关闭程序")
            sys.exit(1)

        # 保存获取的用户标识
        self.finder_username = res["data"]["finderUser"]["finderUsername"]
        self.nick_name = res["data"]["finderUser"]["nickname"]

    def get_x_wechat_uin(self):
        timestamp = str(int(time.time() * 1000))
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
        timestamp = str(int(time.time() * 1000))
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
            logging.error("登录cookie获取失败")

        self.login_cookie = cookie

    def get_video_list(
        self, unread: bool = False, need_comment_count: bool = True
    ) -> List[Any]:
        timestamp = str(int(time.time() * 1000))
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
            logging.error("视频列表获取失败, 列表可能为空或者数据问题")
            return []

        video_list = res["data"]["list"]

        return video_list

    def get_comment_list(
        self, export_id, video, cb: Any = lambda comment: None
    ) -> List[Any]:
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
            logging.error("评论获取失败, 列表可能为空或者数据问题")
            return []

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
        response = requests.post(
            WxVApiFields.PrivateMsg.send_private_msg,
            headers=headers,
            data=json.dumps(data),
            cookies=self.cookie,
        )
        res = response.json()
        logging.log(15, res)

    def upload_media_info(self, from_username, to_username, file_path) -> Any:
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
        response = requests.post(
            WxVApiFields.PrivateMsg.send_private_msg,
            headers=headers,
            data=json.dumps(data),
            cookies=self.cookie,
        )
        res = response.json()
        logging.log(15, res)

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
        timestamp = str(int(time.time() * 1000))
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
        logging.log(15, res)
        msgs = res["data"]["msg"]
        return msgs

    #  接收历史私信消息
    def get_history_msgs(self) -> List[Any]:
        timestamp = str(int(time.time() * 1000))
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
        msgs = self.get_new_msgs()

        if msgs:
            for msg in msgs:
                is_sended = cb(
                    self,
                    msg["sessionId"],
                    msg["toUsername"],
                    msg["fromUsername"],
                )
                if is_sended:
                    self.private_already_sender.add(msg["sessionId"])

    def load_private_history_already_senders(self, send_text: str):
        # 确保消息已经发送过了
        history_msgs = self.get_history_msgs()
        for msg in history_msgs:
            if msg["rawContent"] == send_text:
                self.private_already_sender.add(msg["sessionId"])

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
