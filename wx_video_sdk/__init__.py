import json
import time
from typing import Any, List
import requests
from utils import create_qc_code
from api_feilds import VideoVisibleTypes, WxVApiFields


class WXVideoSDK:
    uin = "0000000000"
    token = ""
    cookie = {}
    finder_username = ""
    latitude = 0
    longitude = 0
    city = ""
    trace_key = ""

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
        }

        if status == 1 and acct_status == 1:
            print(msg_dict[(status, acct_status)])
            self.cookie = response.cookies.get_dict()
            if not self.cookie:
                msg = "Cookie获取失败"
                print(msg)
                return False
            self.get_x_wechat_uin()
            return True

        print(msg_dict[(status, acct_status)])
        return False

    def get_auth_data(self):
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

    def get_video_list(self) -> List[Any]:
        print("get_video_list")
        timestamp = int(time.time() * 1000)
        headers = {
            "X-Wechat-Uin": self.uin,
        }
        data = {
            "pageSize": 10,
            "currentPage": 1,
            "onlyUnread": False,
            "userpageType": 3,
            "needAllCommentCount": True,
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
        if res["data"]["list"]:
            for row in res["data"]["list"]:
                exportId = row["exportId"]
                # 获取评论列表
                self.get_comment_list(exportId, row)
        else:
            print("视频列表获取失败")

        return res["data"]["list"]

    def get_comment_list(self, export_id, row) -> List[Any]:
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
        if res["data"]["comment"]:
            for row in res["data"]["comment"]:
                print(row["commentContent"])

                # 监听评论内容
                # if row["commentContent"] == "太美了":
                #     print("回复评论")
                #     send_comment(finderUsername, exportId, row)
                # else:
                #     print("其他评论")
        else:
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
        print(res)
        if res["data"]["errorCode"] != 0:
            return False

        return True

    def on_video_readcount_upper_do(
        self,
        read_count: int,
        cb: Any,
        is_all_video: bool = True,
        object_id: str | None = None,
    ):
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


def update_video_list_visible_to_public(
    sdk: WXVideoSDK, object_id, read_count, create_time
):
    sdk.change_video_visible(object_id, VideoVisibleTypes.Private)


if __name__ == "__main__":
    sdk = WXVideoSDK()
    video_list = sdk.get_video_list()
    print(video_list)

    sdk.on_video_readcount_upper_do(100, update_video_list_visible_to_public)
