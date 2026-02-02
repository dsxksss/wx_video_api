import base64
import json
import logging
import os
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple, Set, Generator

import requests
from Crypto.Random import get_random_bytes
from requests.sessions import RequestsCookieJar

from wx_video_sdk.api_fields import WxVApiFields
from wx_video_sdk.cache import CacheHandler
from wx_video_sdk.utils import create_msg_tip, create_qc_code, get_sha256_hash_of_file, mkdir_if_not_exist
from wx_video_sdk.exceptions import WxSDKError, WxAuthError, WxAPIError, WxNetworkError

CACHE_COOKIE_FIELD = "CACHE_COOKIES"
CACHE_AUTH_FIELD = "CACHE_AUTH"

class WXVideoClient:
    def __init__(self, cache_file_path: Optional[str] = None, cache_dir: str = "./caches") -> None:
        self.uin = "0000000000"
        self.nick_name = ""
        self.token = ""
        self.cookie: Optional[Dict[str, str]] = None
        self.login_cookie: Dict[str, Any] = {}
        self.finder_username = ""
        self.res_cookies: Optional[RequestsCookieJar] = None
        self.cache_dir = cache_dir
        
        self.cache_handler = None
        if cache_file_path:
            self.cache_handler = CacheHandler(cache_file_path)

    def request(
        self,
        url: str,
        ext_params: Dict = {},
        ext_data: Dict = {},
        ext_headers: Dict = {},
        use_params: bool = False,
        use_json_headers: bool = False,
    ) -> Tuple[Any, requests.Response]:
        msg_tip = create_msg_tip(url, ext_data)
        prefix_url = "https://channels.weixin.qq.com/cgi-bin/mmfinderassistant-bin" + url

        logging.log(15, "Requesting: %s", msg_tip)
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

        params.update(ext_params)
        data.update(ext_data)
        headers.update(ext_headers)

        try:
            response = requests.post(
                prefix_url,
                headers=headers,
                data=json.dumps(data) if use_json_headers else data,
                params=params if use_params else None,
                cookies=self.cookie,
                verify=False,
                timeout=30
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            msg = f"Network error during [{msg_tip}]: {e}"
            logging.error(msg)
            raise WxNetworkError(msg)

        try:
            res = response.json()
        except ValueError:
            raise WxAPIError(f"Invalid JSON response from [{msg_tip}]")

        if res.get("errCode") != 0:
            err_msg = res.get("errMsg", "Unknown error")
            err_code = res.get("errCode")
            
            if url == WxVApiFields.Helper.helper_merlin_mmdata:
                if self.cache_handler:
                    self.cache_handler.removeCache("self")
                    self.cache_handler.removeCache("auth_data")
                raise WxAuthError("Authentication expired. Please re-login.")

            msg = f"API [{msg_tip}] Error {err_code}: {err_msg}"
            logging.error(msg)
            raise WxAPIError(msg, err_code=err_code, err_msg=err_msg)

        return res.get("data"), response

    def login_with_cache(self) -> bool:
        if not self.cache_handler:
            return False
        
        self.cookie, ok = self._get_cookie_from_cache("self")
        if ok:
            try:
                self._load_auth_data_from_cache()
                return True
            except Exception as e:
                logging.warning(f"Failed to load auth data from cache: {e}")
        return False

    def _get_qrcode(self):
        data, _ = self.request(WxVApiFields.Auth.auth_login_code)
        self.token = data.get("token")
        if self.token:
            create_qc_code(f"https://channels.weixin.qq.com/mobile/confirm_login.html?token={self.token}")
        else:
            raise WxAuthError("Failed to get login token from server")

    def login_steps(self) -> Generator[Tuple[str, str], None, None]:
        """
        Login process as a generator to avoid blocking the main thread.
        Yields (status_code, message).
        """
        self._get_qrcode()
        yield "QR_CODE_READY", f"https://channels.weixin.qq.com/mobile/confirm_login.html?token={self.token}"
        
        while True:
            data, res = self.request(
                WxVApiFields.Auth.auth_login_status,
                ext_data={"token": self.token},
                ext_params={"token": self.token},
                use_params=True,
            )
            status = data.get("status")
            acct_status = data.get("acctStatus")
            
            state = (status, acct_status)
            msg_dict = {
                (0, 0): "WAITING_SCAN",
                (5, 1): "SCANNED_WAITING_CONFIRM",
                (1, 1): "SUCCESS",
                (5, 2): "NO_ACCOUNT",
                (4, 0): "EXPIRED",
                (3, 0): "CANCELLED",
            }
            current_status = msg_dict.get(state, f"UNKNOWN_{status}_{acct_status}")
            
            if current_status == "SUCCESS":
                self.cookie = res.cookies.get_dict()
                self.res_cookies = res.cookies
                self._fetch_and_save_auth_data()
                yield "SUCCESS", "Login successful"
                return
            
            yield current_status, f"Login status: {current_status}"
            if current_status in ["EXPIRED", "CANCELLED", "NO_ACCOUNT"]:
                return
                
            time.sleep(2)

    def login_with_qrcode(self) -> bool:
        """Blocking method for simple usage."""
        for status, msg in self.login_steps():
            logging.info(f"Login Step: {status} - {msg}")
            if status == "SUCCESS":
                return True
            if status in ["EXPIRED", "CANCELLED", "NO_ACCOUNT"]:
                return False
        return False

    # --- Generators ---

    def iter_videos(self, pageSize: int = 10) -> Generator[Dict[str, Any], None, None]:
        videos = self.get_video_list(pageSize=pageSize)
        for video in videos:
            yield video

    def iter_comments(self, video_list: Optional[List[Any]] = None) -> Generator[Tuple[Dict[str, Any], Dict[str, Any]], None, None]:
        target_list = video_list if video_list is not None else self.get_video_list()
        for video in target_list:
            export_id = video.get("exportId")
            if not export_id: continue
            comments = self.get_comment_list(export_id)
            for comment in comments:
                yield video, comment

    def iter_new_messages(self) -> Generator[Dict[str, Any], None, None]:
        msgs = self.get_new_private_msgs()
        for msg in msgs:
            yield msg

    # --- Internal Helpers ---

    def _fetch_and_save_auth_data(self):
        data, _ = self.request(WxVApiFields.Auth.auth_data)
        self.finder_username = data["finderUser"]["finderUsername"]
        self.nick_name = data["finderUser"]["nickname"]
        self.uin = self._get_x_wechat_uin()
        self.login_cookie = self._get_login_cookie()
        
        if not self.cache_handler and self.nick_name:
            mkdir_if_not_exist(self.cache_dir)
            cache_path = os.path.join(self.cache_dir, f"{self.nick_name}.json")
            self.cache_handler = CacheHandler(cache_path)

        if self.cache_handler:
            auth_data_dict = {
                "finder_username": self.finder_username,
                "nick_name": self.nick_name,
                "uin": self.uin,
                "login_cookie": self.login_cookie,
            }
            if self.res_cookies:
                self._save_cookie_to_cache("self", self.res_cookies)
            self.cache_handler.saveCache("auth_data", CACHE_AUTH_FIELD, auth_data_dict)

    def _load_auth_data_from_cache(self):
        if not self.cache_handler:
            raise WxSDKError("No cache handler configured")
        cache = self.cache_handler.getCache("auth_data")
        if not cache or CACHE_AUTH_FIELD not in cache:
            raise WxAuthError("Auth data missing in cache")
        
        auth_data = cache[CACHE_AUTH_FIELD]
        self.finder_username = auth_data["finder_username"]
        self.nick_name = auth_data["nick_name"]
        self.uin = auth_data["uin"]
        self.login_cookie = auth_data["login_cookie"]

    def _get_x_wechat_uin(self) -> str:
        data, _ = self.request(WxVApiFields.Helper.helper_upload_params)
        return str(data.get("uin", ""))

    def _get_login_cookie(self) -> str:
        data, _ = self.request(WxVApiFields.PrivateMsg.get_login_cookie)
        return data.get("cookie", "")

    def _save_cookie_to_cache(self, name: str, cookie: RequestsCookieJar):
        cookies_text = "; ".join([f"{n}={v}" for n, v in cookie.items()])
        if self.cache_handler.isExists(name):
            self.cache_handler.updateCache(name, CACHE_COOKIE_FIELD, cookies_text)
        else:
            self.cache_handler.saveCache(name, CACHE_COOKIE_FIELD, cookies_text)

    def _get_cookie_from_cache(self, name: str) -> Tuple[Optional[Dict[str, str]], bool]:
        if not self.cache_handler or not self.cache_handler.isExists(name):
            return None, False
        cache = self.cache_handler.getCache(name)
        cookies_text = cache.get(CACHE_COOKIE_FIELD)
        if not cookies_text: return None, False
        cookies = dict(item.split("=") for item in cookies_text.split("; ") if "=" in item)
        return cookies, True

    # --- API Methods ---

    def heartbeat(self):
        data = {
            "id": 23865,
            "data": {
                "17": time.time(), "18": time.time(), "19": 1, "21": 2, "22": str(uuid.uuid4()),
                "24": int(time.time() * 1000), "27": "Mozilla/5.0 ... SDK", "31": "LoginForIframe",
                "33": str(uuid.uuid4()), "36": 1, "37": "{}", "39": "{}", "40": "pageEnter",
                "41": "{}", "42": '{"screenHeight":1080;"screenWidth":1920;"clientHeight":0;"clientWidth":0}',
            },
            "_log_finder_id": "",
        }
        self.request(WxVApiFields.Helper.helper_merlin_mmdata, ext_data=data)

    def get_video_list(self, unread: bool = False, pageSize: int = 10) -> List[Dict[str, Any]]:
        data = {
            "pageSize": pageSize, "currentPage": 1, "onlyUnread": unread,
            "userpageType": 3, "needAllCommentCount": True, "forMcn": False,
        }
        res, _ = self.request(WxVApiFields.Post.post_list, ext_data=data)
        return res.get("list", [])

    def get_comment_list(self, export_id: str) -> List[Dict[str, Any]]:
        data = {"lastBuff": "", "exportId": export_id, "commentSelection": False, "forMcn": False}
        res, _ = self.request(WxVApiFields.Comment.comment_list, ext_data=data)
        return res.get("comment", [])

    def update_video_visible(self, object_id: str, visible_type: int) -> bool:
        data = {"objectId": object_id, "visibleType": visible_type}
        res, _ = self.request(WxVApiFields.Post.post_update_visible, use_json_headers=True, ext_data=data)
        return res.get("errorCode") == 0

    def send_private_msg(self, session_id: str, from_username: str, to_username: str, content: str):
        data = {
            "msgPack": {
                "sessionId": session_id, "fromUsername": from_username, "toUsername": to_username,
                "msgType": 1, "textMsg": {"content": content}, "cliMsgId": str(uuid.uuid4()),
            },
        }
        self.request(WxVApiFields.PrivateMsg.send_private_msg, use_json_headers=True, ext_data=data)

    def send_private_img(self, session_id: str, from_username: str, to_username: str, img_path: str):
        img_msg = self._upload_media(from_username, to_username, img_path)
        data = {
            "msgPack": {
                "sessionId": session_id, "fromUsername": from_username, "toUsername": to_username,
                "msgType": 3, "imgMsg": img_msg, "cliMsgId": str(uuid.uuid4()),
            }
        }
        self.request(WxVApiFields.PrivateMsg.send_private_msg, use_json_headers=True, ext_data=data)

    def _upload_media(self, from_username: str, to_username: str, file_path: str) -> Any:
        aes_key = base64.b64encode(get_random_bytes(32)).decode()
        file_size = os.path.getsize(file_path)
        file_md5 = get_sha256_hash_of_file(file_path)
        chunk_size = 512 * 1024
        chunks = -(-file_size // chunk_size)
        img_msg = {}

        with open(file_path, "rb") as file:
            for chunk in range(chunks):
                file.seek(chunk * chunk_size)
                data = file.read(chunk_size)
                base64_data = base64.b64encode(data).decode()
                payload = {
                    "aesKey": aes_key, "chunk": chunk, "chunks": chunks,
                    "content": f"data:application/octet-stream;base64,{base64_data}",
                    "fromUsername": from_username, "toUsername": to_username,
                    "md5": file_md5, "mediaSize": file_size, "mediaType": 3,
                }
                res, _ = self.request(WxVApiFields.PrivateMsg.upload_media_info, use_json_headers=True, ext_data=payload)
                img_msg = res.get("imgMsg")
        return img_msg

    def send_comment_reply(self, export_id: str, comment: Dict[str, Any], content: str):
        data = {
            "replyCommentId": comment["commentId"], "content": content, "clientId": str(uuid.uuid4()),
            "rootCommentId": comment["commentId"], "comment": comment, "exportId": export_id,
        }
        self.request(WxVApiFields.Comment.create_comment, use_json_headers=True, ext_data=data)

    def get_new_private_msgs(self) -> List[Dict[str, Any]]:
        data = {"cookie": self.login_cookie}
        res, _ = self.request(WxVApiFields.PrivateMsg.get_new_msg, ext_data=data)
        return res.get("msg", [])

    def get_history_private_msgs(self) -> List[Dict[str, Any]]:
        data = {"cookie": self.login_cookie}
        res, _ = self.request(WxVApiFields.PrivateMsg.get_history_msg, ext_data=data)
        return res.get("msg", [])
