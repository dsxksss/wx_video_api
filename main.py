# type: ignore
import requests
import time
import json
from qrcode import QRCode
import uuid
import qrcode

# import websocket

uin = "0000000000"
Cookie = ""
finderUsername = ""
latitude = 0
longitude = 0       
city = ""
traceKey = ""


# 1.获取二维码
def get_qrcode():
    # 获取当前时间戳
    timestamp = int(time.time() * 1000)
    url = "https://channels.weixin.qq.com/cgi-bin/mmfinderassistant-bin/auth/auth_login_code"
    headers = {
        "X-Wechat-Uin": uin,
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
        url,
        headers=headers,
        data=data,
    )
    response_json = json.loads(response.text)
    token = response_json.get("data").get("token")
    img = f"https://channels.weixin.qq.com/mobile/confirm_login.html?token={token}"

    if img:
        create_qc_code(img)
    else:
        print("二维码获取失败")

    if token:
        create_session(token)
    else:
        print("token获取失败")


# 2.获取token
def create_session(token):
    timestamp = int(time.time() * 1000)
    url = "https://channels.weixin.qq.com/cgi-bin/mmfinderassistant-bin/auth/auth_login_status"
    headers = {
        "X-Wechat-Uin": uin,
    }
    data = {
        "token": token,
        "timestamp": timestamp,
        "_log_finder_uin": "",
        "_log_finder_id": "",
        "rawKeyBuff": None,
        "pluginSessionId": None,
        "scene": 7,
        "reqScene": 7,
    }
    params = {
        "token": token,
        "timestamp": timestamp,
        "_log_finder_uin": "",
        "_log_finder_id": "",
        "scene": 7,
        "reqScene": 7,
    }
    response = requests.post(
        url,
        headers=headers,
        data=data,
        params=params,
    )
    res = response.json()
    if res["data"]["status"] == 0 and res["data"]["acctStatus"] == 0:
        time.sleep(2)
        print("未登录")
        create_session(token)
    elif res["data"]["status"] == 5 and res["data"]["acctStatus"] == 1:
        print("已经扫码未确认")
        time.sleep(2)
        create_session(token)
    elif res["data"]["status"] == 1 and res["data"]["acctStatus"] == 1:
        print("登录成功")
        # 从响应头中获取请求头cookie
        global Cookie
        # Cookie = response.headers["Set-Cookie"]
        Cookie = response.cookies.get_dict()  # map object
        # print(Cookie)
        if Cookie:
            get_auth_data()
        else:
            print("Cookie获取失败")
    elif res["data"]["status"] == 5 and res["data"]["acctStatus"] == 2:
        print("没有可登录的视频号")
    elif res["data"]["status"] == 4:
        print("二维码已经过期")
    else:
        print("网络错误")


# 3.获取authData
def get_auth_data():
    timestamp = int(time.time() * 1000)
    url = "https://channels.weixin.qq.com/cgi-bin/mmfinderassistant-bin/auth/auth_data"
    headers = {
        "X-Wechat-Uin": uin,
        # "Cookie": Cookie,
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
        url,
        headers=headers,
        data=data,
        cookies=Cookie,
    )
    res = response.json()
    finderUsername = res["data"]["finderUser"]["finderUsername"]
    if finderUsername:
        print("Foundfinder")
        # 获取uin
        get_x_wechat_uin(finderUsername)
        # 获取cookie
        get_login_cookie(finderUsername)
        # 获取视频列表 暂时注释
        get_video_list(finderUsername)
        # 上传视频
        # upload_video()
        # 获取当前位置
        locaction = get_location()
        print(locaction)
        # 获取traceKey
        traceKey = get_trace_key()
        print(traceKey)
        time.sleep(2)
        # 发布视频
        publish_video()
    else:
        print("authData获取失败")


# 4.获取登录cookie  https://channels.weixin.qq.com/cgi-bin/mmfinderassistant-bin/private-msg/get-login-cookie
def get_login_cookie(finderUsername):
    timestamp = int(time.time() * 1000)
    print("get_login_cookie")
    url = "https://channels.weixin.qq.com/cgi-bin/mmfinderassistant-bin/private-msg/get-login-cookie"
    headers = {
        "X-Wechat-Uin": uin,
        # "Cookie": Cookie,
    }
    data = {
        "timestamp": timestamp,
        "_log_finder_uin": "",
        "_log_finder_id": finderUsername,
        "rawKeyBuff": None,
        "pluginSessionId": None,
        "scene": 7,
        "reqScene": 7,
    }
    print("--------------data------------------")
    print(data)
    print("--------------data-----------------")
    response = requests.post(
        url,
        headers=headers,
        data=data,
        cookies=Cookie,
    )
    res = response.json()
    cookie = res["data"]["cookie"]
    if cookie:
        print("--------------cookie------------------")
        print(cookie)
        print("---------------cookie-----------------")
        get_new_msg(finderUsername, cookie)  # 接收私信消息 暂时注释
    else:
        print("登录cookie获取失败")

# 5.接收私信消息 https://channels.weixin.qq.com/cgi-bin/mmfinderassistant-bin/private-msg/get-new-msg
def get_new_msg(finderUsername, cookie):
    timestamp = int(time.time() * 1000)
    print("get_new_msg")
    url = "https://channels.weixin.qq.com/cgi-bin/mmfinderassistant-bin/private-msg/get-new-msg"
    headers = {
        "X-Wechat-Uin": uin,
        # "Cookie": Cookie,
    }
    data = {
        "cookie": cookie,
        "timestamp": timestamp,
        "_log_finder_uin": "",
        "_log_finder_id": finderUsername,
        "rawKeyBuff": None,
        "pluginSessionId": None,
        "scene": 7,
        "reqScene": 7,
    }
    response = requests.post(
        url,
        headers=headers,
        data=data,
        cookies=Cookie,
    )
    res = response.json()
    print(res)
    msg = res["data"]["msg"]
    # 循环遍历消息 如果是文本消息就回复 如果是其他消息就不回复
    for i in msg:
        if i["rawContent"] == "你好":
            time.sleep(2)
            # 回复消息
            send_private_msg(
                finderUsername,
                i["sessionId"],
                i["toUsername"],
                i["fromUsername"],
            )
        else:
            print("其他消息")
    # 每隔5秒请求一次
    time.sleep(5)
    print("---------------555-----------------")
    get_new_msg(finderUsername, res["data"]["cookie"])


# 6.回复私信消息 https://channels.weixin.qq.com/cgi-bin/mmfinderassistant-bin/private-msg/send-private-msg
def send_private_msg(finderUsername, sessionId, toUsername, fromUsername):
    myUUID = str(uuid.uuid4())
    timestamp = str(int(time.time() * 1000))
    url = "https://channels.weixin.qq.com/cgi-bin/mmfinderassistant-bin/private-msg/send-private-msg"
    headers = {
        "X-Wechat-Uin": uin,
        "Content-Type": "application/json",
    }
    data = {
        "msgPack": {
            "sessionId": sessionId,
            "fromUsername": toUsername,
            "toUsername": fromUsername,
            "msgType": 1,
            "textMsg": {"content": "你好呀！"},
            "cliMsgId": myUUID,
        },
        "timestamp": timestamp,
        "_log_finder_uin": "",
        "_log_finder_id": finderUsername,
        "rawKeyBuff": None,
        "pluginSessionId": None,
        "scene": 7,
        "reqScene": 7,
    }
    response = requests.post(
        url,
        headers=headers,
        data=json.dumps(data),
        cookies=Cookie,
    )
    print(response)
    res = response.json()
    print("回复消息", res)


# 7.生成二维码
def create_qc_code(url):
    qr = QRCode(box_size=10, border=2)
    # 添加链接
    qr.add_data(url)
    
    # # 生成二维码，默认是常规白底黑色填充的
    # img = qr.make_image(fill_color="black", back_color="white")
    # # 保存二维码为png格式
    # img.save("qrcode.png")
    
    # 显示二维码至终端
    qr.print_ascii()


# 8.获取X-Wechat-Uin
def get_x_wechat_uin(finderUsername):
    print("get_x_wechat_uin")
    timestamp = int(time.time() * 1000)
    url = "https://channels.weixin.qq.com/cgi-bin/mmfinderassistant-bin/helper/helper_upload_params"
    headers = {
        "X-Wechat-Uin": "0000000000",
        # "Cookie": Cookie,
    }
    data = {
        "timestamp": timestamp,
        "_log_finder_uin": "",
        "_log_finder_id": finderUsername,
        "rawKeyBuff": None,
        "pluginSessionId": None,
        "scene": 7,
        "reqScene": 7,
    }
    response = requests.post(
        url,
        headers=headers,
        data=data,
        cookies=Cookie,
    )
    res = response.json()
    global uin
    uin = str(res["data"]["uin"])
    print("--------------------------------")
    print(uin)
    print("--------------------------------")


# 9.获取视频列表
def get_video_list(finderUsername):
    print("get_video_list")
    timestamp = int(time.time() * 1000)
    url = "https://channels.weixin.qq.com/cgi-bin/mmfinderassistant-bin/post/post_list"
    headers = {
        "X-Wechat-Uin": uin,
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
        "_log_finder_id": finderUsername,
        "rawKeyBuff": None,
        "pluginSessionId": None,
        "scene": 7,
        "reqScene": 7,
    }
    response = requests.post(
        url,
        headers=headers,
        data=data,
        cookies=Cookie,
    )
    res = response.json()
    print(res)
    if res.get("data").get("list"):
        for i in res["data"]["list"]:
            exportId = i["exportId"]
            # 获取评论列表
            get_comment_list(finderUsername, exportId, i)
    else:
        print("视频列表获取失败")


# 获取评论内容 https://channels.weixin.qq.com/cgi-bin/mmfinderassistant-bin/comment/comment_list
def get_comment_list(finderUsername, exportId, i):
    timestamp = str(int(time.time() * 1000))
    print(uin)
    url = "https://channels.weixin.qq.com/cgi-bin/mmfinderassistant-bin/comment/comment_list"
    headers = {
        "X-Wechat-Uin": uin,
        "Content-Type": "application/json",
    }
    data = {
        "lastBuff": "",
        "exportId": exportId,
        "commentSelection": False,
        "forMcn": False,
        "timestamp": timestamp,
        "_log_finder_uin": "",
        "_log_finder_id": finderUsername,
        "rawKeyBuff": None,
        "pluginSessionId": None,
        "scene": 7,
        "reqScene": 7,
    }
    response = requests.post(
        url,
        headers=headers,
        cookies=Cookie,
        data=json.dumps(data),
    )
    res = response.json()
    print(res["data"])
    if res["data"]["comment"]:
        for i in res["data"]["comment"]:
            print(i["commentContent"])
            if i["commentContent"] == "太美了":
                print("回复评论")
                send_comment(finderUsername, exportId, i)
            else:
                print("其他评论")
    else:
        print("评论获取失败")


# 回复视频评论
def send_comment(finderUsername, exportId, i):
    myUUID = str(uuid.uuid4())
    timestamp = str(int(time.time() * 1000))
    url = "https://channels.weixin.qq.com/cgi-bin/mmfinderassistant-bin/comment/create_comment"
    headers = {
        "X-Wechat-Uin": uin,
        "Content-Type": "application/json",
    }
    data = {
        "replyCommentId": i["commentId"],
        "content": "哈哈",
        "clientId": myUUID,
        "rootCommentId": i["commentId"],
        "comment": i,
        "exportId": exportId,
        "timestamp": timestamp,
        "_log_finder_uin": "",
        "_log_finder_id": finderUsername,
        "rawKeyBuff": None,
        "pluginSessionId": None,
        "scene": 7,
        "reqScene": 7,
    }
    response = requests.post(
        url,
        headers=headers,
        cookies=Cookie,
        data=json.dumps(data),
    )
    res = response.json()
    print(res)


# 上传视频
def upload_video():
    url = "https://finderassistancea.video.qq.com/applyuploaddfs"
    headers = {
        "X-Arguments": "apptype=251&filetype=20304&weixinnum=981816192&filekey=finder_video_img.jpeg&filesize=369410&taskid=0153ddfd-305f-4dca-aea6-748af8bafa47&scene=0",
        "Content-Type": "application/json",
        "Authorization": "303e0201010437303502010102010102043a855380020101020102020404030201020320141d020412124475020414efe97902046622167602045e79fee50400",
    }                     
    data = {"BlockSum": 1, "BlockPartLength": [369410]}

    response = requests.put(
        url,
        headers=headers,
        cookies=Cookie,
        data=json.dumps(data),
    )
    res = response.json()
    # print(res["DownloadURL"])


# 获取当前位置
def get_location():
    timestamp = str(int(time.time() * 1000))
    url = "https://channels.weixin.qq.com/cgi-bin/mmfinderassistant-bin/helper/helper_search_location"
    headers = {
        "X-Wechat-Uin": uin,
    }
    data = {
        "query": "",
        "cookies": "",
        "longitude": 0,
        "latitude": 0,
        "timestamp": timestamp,
        "_log_finder_uin": "",
        "_log_finder_id": finderUsername,
        "rawKeyBuff": None,
        "pluginSessionId": None,
        "scene": 7,
        "reqScene": 7,
    }
    response = requests.post(
        url,
        headers=headers,
        data=data,
        cookies=Cookie,
    )
    res = response.json()
    latitude = res["data"]["address"]["latitude"]
    longitude = res["data"]["address"]["longitude"]
    city = res["data"]["address"]["city"]
    return {
        "latitude": latitude,
        "longitude": longitude,
        "city": city,
    }


# 获取traceKey
def get_trace_key():
    timestamp = str(int(time.time() * 1000))
    url = "https://channels.weixin.qq.com/cgi-bin/mmfinderassistant-bin/post/get-finder-post-trace-key"
    headers = {
        "X-Wechat-Uin": uin,
    }
    data = {
        "objectId": None,
        "timestamp": timestamp,
        "_log_finder_uin": "",
        "_log_finder_id": finderUsername,
        "rawKeyBuff": None,
        "pluginSessionId": None,
        "scene": 7,
        "reqScene": 7,
    }
    response = requests.post(
        url,
        headers=headers,
        data=data,
        cookies=Cookie,
    )
    res = response.json()
    traceKey = res["data"]["traceKey"]
    return traceKey


# 发布视频
def publish_video():
    myUUID = str(uuid.uuid4())
    timestamp = str(int(time.time() * 1000))
    m_timestamp = str(int(time.time()))
    url = (
        "https://channels.weixin.qq.com/cgi-bin/mmfinderassistant-bin/post/post_create"
    )
    headers = {
        "X-Wechat-Uin": uin,
        "Content-Type": "application/json",
    }
    data = {
        "objectType": 0,
        "longitude": 0,
        "latitude": 0,
        "feedLongitude": 0,
        "feedLatitude": 0,
        "originalFlag": 0,
        "topics": [],
        "isFullPost": 1,
        "handleFlag": 2,
        "videoClipTaskId": "",
        "traceInfo": {
            "traceKey": traceKey,
            "uploadCdnStart": m_timestamp,
            "uploadCdnEnd": m_timestamp,
        },
        "objectDesc": {
            "mpTitle": "",
            "description": "#",
            "extReading": {},
            "mediaType": 2,
            "location": {
                "latitude": latitude,
                "longitude": longitude,
                "city": city,
                "poiClassifyId": "",
            },
            "topic": {
                "finderTopicInfo": "<finder><version>1</version><valuecount>1</valuecount><style><at></at></style><value0><![CDATA[#]]></value0></finder>"
            },
            "event": {},
            "mentionedUser": [],
            "media": [
                {
                    "url": "https://finder.video.qq.com/251/20304/stodownload?bizid=1023&dotrans=0&encfilekey=rjD5jyTuFrIpZ2ibE8T7YmwgiahniaXswqzlcPHbg3keBzW4VS8lwPicXwrhNTBNPANzbmJy5eCYtU9wW84HkFg0SodsuItTiaJCntECoD6KjS40Xic9YW9F23pQ&hy=SH&idx=1&m=&scene=0&token=6xykWLEnztLZ2p2FvRHDeQllaUUlhtY4uib9kA3OuU1hn8128ltYoZ03MExib0nWAsib78xicM1SWibEdGia1hactfMw",
                    "fileSize": 3654801,
                    "thumbUrl": "https://finder.video.qq.com/251/20350/stodownload?bizid=1023&dotrans=0&encfilekey=rjD5jyTuFrIpZ2ibE8T7YmwgiahniaXswqzP07ibSibiciaOBic48bnlJPOzGP19NJZPg9xqnVu1cFkQmQGibHTOSta4RjeAORYGoJWPW5mp97cFRmrlGGiasWIibhiaww&hy=SH&idx=1&m=&scene=0&token=cztXnd9GyrF2IupOnSmYjcggicYCNZSU0HfvmaQHkqcjCAapPClozqrSbaYIXazT1UXprqOqYMJYqMqsviamW5yg",
                    "fullThumbUrl": "https://finder.video.qq.com/251/20350/stodownload?bizid=1023&dotrans=0&encfilekey=rjD5jyTuFrIpZ2ibE8T7YmwgiahniaXswqzP07ibSibiciaOBic48bnlJPOzGP19NJZPg9xqnVu1cFkQmQGibHTOSta4RjeAORYGoJWPW5mp97cFRmrlGGiasWIibhiaww&hy=SH&idx=1&m=&scene=0&token=cztXnd9GyrF2IupOnSmYjcggicYCNZSU0HfvmaQHkqcjCAapPClozqrSbaYIXazT1UXprqOqYMJYqMqsviamW5yg",
                    "mediaType": 2,
                    "videoPlayLen": 0,
                    "width": 2600,
                    "height": 3900,
                    "md5sum": "f025b779-4814-448c-840f-afb0bb51175e",
                    "urlCdnTaskId": "",
                }
            ],
            "member": {},
        },
        "postFlag": 0,
        "mode": 1,
        "clientid": myUUID,
        "timestamp": timestamp,
        "_log_finder_uin": "",
        "_log_finder_id": finderUsername,
        "rawKeyBuff": None,
        "pluginSessionId": None,
        "scene": 7,
        "reqScene": 7,
    }
    response = requests.post(
        url,
        headers=headers,
        cookies=Cookie,
        data=json.dumps(data),
    )
    res = response.json()
    print(res)


if __name__ == "__main__":
    get_qrcode()
