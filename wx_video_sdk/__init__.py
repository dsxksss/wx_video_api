import base64
import json
import logging
from Crypto.Random import get_random_bytes
from requests.sessions import RequestsCookieJar
import os
import time
from typing import Any, Dict, List
import uuid
import requests
from wx_video_sdk.cache import CacheHandler
from wx_video_sdk.utils import create_msg_tip, create_qc_code, get_sha256_hash_of_file
from wx_video_sdk.api_feilds import WxVApiFields

CACHE_COOKIE_FIELD = "CACHE_COOKIES"
CACHE_AUTH_FIELD = "CACHE_AUTH"


class WXVideoSDK:
    uin = "0000000000"
    nick_name = ""
    token = ""
    cookie = None
    login_cookie = {}
    finder_username = ""
    private_already_sender = set()
    comment_already_sender = set()

    def __init__(self, cache_file_name: str) -> None:
        self.cache_name = cache_file_name.split("s/")[1].split(".")[0]
        self.is_use_cache_login = False

        if self.cache_name == "None" or self.cache_name == "扫码登录新账号":
            if self.cache_name == "None":
                logging.info("没有找到已经添加的账号缓存，请扫描登录")

            self.login()
            return

        self.is_use_cache_login = True
        self.cache_handler = CacheHandler(cache_file_name)
        self.cache_login()

    def request(
        self,
        url,
        ext_params={},
        ext_data={},
        ext_headers={},
        use_params=False,
        use_json_headers=False,
    ):
        # 为了可读性，在同url但是不同作用的情况下用来输出日志做区分
        msg_tip = create_msg_tip(url, ext_data)

        prefix_url = (
            "https://channels.weixin.qq.com/cgi-bin/mmfinderassistant-bin" + url
        )

        logging.log(15, "request url [%s]", msg_tip)
        # 获取当前时间戳
        timestamp = str(int(time.time() * 1000))
        headers = {
            "X-Wechat-Uin": self.uin,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
        }
        if use_json_headers:
            headers["Content-Type"] = "application/json"

        data = {
            "timestamp": timestamp,
            "_log_finder_uin": "",
            "_log_finder_id": self.finder_username,
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

        for key, value in ext_headers.items():
            headers[key] = value

        response: requests.Response = requests.post(
            prefix_url,
            headers=headers,
            data=json.dumps(data) if use_json_headers else data,
            params=params if use_params else None,
            cookies=self.cookie,
        )

        if response.status_code >= 400:
            msg = f"请求 [{msg_tip}] 失败!, response.status_code = [{response.status_code}], response.reason = {response.reason}"
            logging.error(msg)
            raise ValueError(msg)

        res = response.json()

        if res["errCode"] != 0:
            if url == WxVApiFields.Helper.hepler_merlin_mmdata:
                self.cache_handler.removeCache("self")
                self.cache_handler.removeCache("auth_data")
                msg = "你的身份验证失败，请关闭程序重新扫描登录"
                logging.error(msg)
                raise ValueError(msg)

            msg = f"调用 [{msg_tip}] 发生网络问题!,errCode = [{res['errCode']}], errMsg = {res['errMsg']}"
            logging.error(msg)
            raise ValueError(msg)

        return res["data"], response

    def cache_login(self):
        print("cache_login")
        self.cookie, is_can_login = self._get_cookie("self")
        if is_can_login:
            self.get_auth_data()
            return

        logging.error("不可使用缓存登录，请重新扫描登录")
        self.login()

    def login(self):
        print("login")
        is_can_login = False
        self.get_qrcode()
        while not is_can_login:
            is_can_login = self.create_session()
            time.sleep(2)

    def get_qrcode(self):
        data, _ = self.request(WxVApiFields.Auth.auth_login_code)
        self.token = data["token"]

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
        data, res = self.request(
            WxVApiFields.Auth.auth_login_status,
            ext_data={
                "token": self.token,
            },
            ext_params={
                "token": self.token,
            },
            use_params=True,
        )
        status = data["status"]
        acct_status = data["acctStatus"]

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
            self.cookie = res.cookies.get_dict()
            self.res_cookies = res.cookies

            if not self.cookie:
                logging.error("Cookie获取失败")
                raise ValueError("Cookie获取失败")

            # 获取用户信息
            self.get_auth_data()
            return True

        logging.info(msg_dict[(status, acct_status)])
        return False

    def hepler_merlin_mmdata(self):
        time10 = time.time()
        time13 = int(time.time() * 1000)
        data = {
            "id": 23865,
            "data": {
                "12": "",
                "13": "",
                "14": "",
                "15": "",
                "16": "",
                "17": time10,
                "18": time10,
                "19": 1,
                "20": "",
                "21": 2,
                "22": uuid.uuid4(),
                "23": "",
                "24": time13,
                "25": "",
                "26": 0,
                "27": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
                "28": "",
                "29": "",
                "30": "",
                "31": "LoginForIframe",
                "32": "",
                "33": uuid.uuid4(),
                "34": "",
                "35": "",
                "36": 1,
                "37": "{}",
                "38": "",
                "39": "{}",
                "40": "pageEnter",
                "41": "{}",
                "42": '{"screenHeight":1032;"screenWidth":1920;"clientHeight":0;"clientWidth":0}',
                "43": "",
            },
            "_log_finder_id": "",
        }
        self.request(WxVApiFields.Helper.hepler_merlin_mmdata, ext_data=data)

    def get_auth_data(self):

        # 保存获取的用户标识
        if not self.is_use_cache_login:
            data, _ = self.request(WxVApiFields.Auth.auth_data)
            self.finder_username = data["finderUser"]["finderUsername"]
            self.nick_name = data["finderUser"]["nickname"]
            self.uin = self.get_x_wechat_uin()
            self.login_cookie = self.get_login_cookie()
            auth_data_dict = {
                "finder_username": self.finder_username,
                "nick_name": self.nick_name,
                "uin": self.uin,
                "login_cookie": self.login_cookie,
            }
            self.cache_handler: CacheHandler = CacheHandler(
                f"./caches/{self.nick_name}.json"
            )
            self._set_cookie("self", self.res_cookies)
            self.cache_handler.saveCache("auth_data", CACHE_AUTH_FIELD, auth_data_dict)
            return

        auth_data_dict = self.cache_handler.getCache("auth_data")[CACHE_AUTH_FIELD]
        self.finder_username = auth_data_dict["finder_username"]
        self.nick_name = auth_data_dict["nick_name"]
        self.uin = auth_data_dict["uin"]
        self.login_cookie = auth_data_dict["login_cookie"]

    def get_x_wechat_uin(self) -> str:
        data, _ = self.request(WxVApiFields.Helper.helper_upload_params)
        if not data:
            raise Exception("获取wechat_uin失败")
        return str(data["uin"])

    def get_login_cookie(self) -> str:
        data, _ = self.request(WxVApiFields.PrivateMsg.get_login_cookie)
        cookie = data["cookie"]
        if not cookie:
            logging.error("登录cookie获取失败")

        return cookie

    def get_video_list(
        self, unread: bool = False, need_comment_count: bool = True
    ) -> List[Any]:
        data = {
            "pageSize": 10,
            "currentPage": 1,
            "onlyUnread": unread,
            "userpageType": 3,
            "needAllCommentCount": need_comment_count,
            "forMcn": False,
        }
        data, _ = self.request(WxVApiFields.Post.post_list, ext_data=data)

        if not data["list"]:
            logging.error("视频列表获取失败, 列表可能为空或者数据问题")
            return []

        video_list = data["list"]

        return video_list

    def get_comment_list(
        self, export_id, video, cb: Any = lambda comment: None
    ) -> List[Any]:

        data = {
            "lastBuff": "",
            "exportId": export_id,
            "commentSelection": False,
            "forMcn": False,
        }
        data, _ = self.request(WxVApiFields.Comment.comment_list, ext_data=data)

        if not data["comment"]:
            logging.log(15, "评论列表可能为空或者数据(如果觉得不重要即可忽略)")
            return []

        return data["comment"]

    def change_video_visible(self, object_id: str, visible_type: int) -> bool:
        data = {
            "objectId": object_id,
            "visibleType": visible_type,
        }
        data, _ = self.request(
            WxVApiFields.Post.post_update_visible,
            use_json_headers=True,
            ext_data=data,
        )
        if data["errorCode"] != 0:
            return False

        return True

    # 回复私信消息
    def send_private_msg(
        self, session_id, from_username: str, to_username: str, msg_content: str
    ):
        uid = str(uuid.uuid4())

        data = {
            "msgPack": {
                "sessionId": session_id,
                "fromUsername": from_username,
                "toUsername": to_username,
                "msgType": 1,
                "textMsg": {"content": msg_content},
                "cliMsgId": uid,
            },
        }

        data, _ = self.request(
            WxVApiFields.PrivateMsg.send_private_msg,
            use_json_headers=True,
            ext_data=data,
        )
        logging.log(15, data)

    def upload_media_info(self, from_username, to_username, file_path) -> Any:

        # 生成AES密钥并且转换为 base64 格式以便于存储和传输
        aes_key = base64.b64encode(get_random_bytes(32)).decode()
        with open(file_path, "rb") as file:
            file_size = os.path.getsize(file_path)
            file_md5 = get_sha256_hash_of_file(file_path)
            chunk_size = 512 * 1024
            chunks = -(-file_size // chunk_size)
            img_msg = {}

            for chunk in range(chunks):
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
                }

                data, _ = self.request(
                    WxVApiFields.PrivateMsg.upload_media_info,
                    use_json_headers=True,
                    ext_data=data,
                )
                img_msg = data["imgMsg"]

            return img_msg

    def send_private_img(
        self, session_id, from_username: str, to_username: str, img_path: str
    ):
        # 切片上传图片
        img_msg = self.upload_media_info(
            from_username=from_username, to_username=to_username, file_path=img_path
        )
        uid = str(uuid.uuid4())

        data = {
            "msgPack": {
                "sessionId": session_id,
                "fromUsername": from_username,
                "toUsername": to_username,
                "msgType": 3,
                "imgMsg": img_msg,
                "cliMsgId": uid,
            }
        }
        data, _ = self.request(
            WxVApiFields.PrivateMsg.send_private_msg,
            use_json_headers=True,
            ext_data=data,
        )
        logging.log(15, data)

    # 回复视频评论
    def send_comment(self, export_id, comment, comment_content: str):
        uid = str(uuid.uuid4())
        data = {
            "replyCommentId": comment["commentId"],
            "content": comment_content,
            "clientId": uid,
            "rootCommentId": comment["commentId"],
            "comment": comment,
            "exportId": export_id,
        }
        self.request(
            WxVApiFields.Comment.create_comment,
            use_json_headers=True,
            ext_data=data,
        )

    #  接收未读的私信消息
    def get_new_msgs(self) -> List[Any]:
        data = {
            "cookie": self.login_cookie,
        }
        data, _ = self.request(WxVApiFields.PrivateMsg.get_new_msg, ext_data=data)
        logging.log(15, data)
        msgs = data["msg"]
        return msgs

    #  接收历史私信消息
    def get_history_msgs(self) -> List[Any]:
        data, _ = self.request(
            WxVApiFields.PrivateMsg.get_history_msg,
            ext_data={
                "cookie": self.login_cookie,
            },
        )
        msgs = data["msg"]
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
                    msg["ts"],
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
