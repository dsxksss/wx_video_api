base_url = "https://channels.weixin.qq.com/cgi-bin/mmfinderassistant-bin"


class WxVApiFields:
    class Auth:
        prefix = "/auth"
        auth_login_code = base_url + prefix + "/auth_login_code"
        auth_data = base_url + prefix + "/auth_data"
        auth_login_status = base_url + prefix + "/auth_login_status"

    class Helper:
        prefix = "/helper"
        helper_upload_params = base_url + prefix + "/helper_upload_params"

    class Comment:
        prefix = "/comment"
        comment_list = base_url + prefix + "/comment_list"
        create_comment = base_url + prefix + "/create_comment"

    class Post:
        prefix = "/post"
        post_list = base_url + prefix + "/post_list"
        post_update_visible = base_url + prefix + "/post_update_visible"
        new_post_total_data = base_url + "/statistic/new_post_total_data"

    class PrivateMsg:
        prefix = "/private-msg"
        get_login_cookie = base_url + prefix + "/get-login-cookie"
        get_new_msg = base_url + prefix + "/get-new-msg"
        get_history_msg = base_url + prefix + "/get-history-msg"
        send_private_msg = base_url + prefix + "/send-private-msg"
        upload_media_info = base_url + prefix + "/upload-media-info"


class VideoVisibleTypes:
    # 视频可见类型
    # Public: 所有人可见
    # Private: 仅自己可见
    Public = 1
    Private = 3
