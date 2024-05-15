class WxVApiFields:
    class Auth:
        prefix = "/auth"
        auth_login_code = prefix + "/auth_login_code"
        auth_data = prefix + "/auth_data"
        auth_login_status = prefix + "/auth_login_status"

    class Helper:
        prefix = "/helper"
        helper_upload_params = prefix + "/helper_upload_params"
        hepler_merlin_mmdata = prefix + "/hepler_merlin_mmdata"

    class Comment:
        prefix = "/comment"
        comment_list = prefix + "/comment_list"
        create_comment = prefix + "/create_comment"

    class Post:
        prefix = "/post"
        post_list = prefix + "/post_list"
        post_update_visible = prefix + "/post_update_visible"
        new_post_total_data = "/statistic/new_post_total_data"

    class PrivateMsg:
        prefix = "/private-msg"
        get_login_cookie = prefix + "/get-login-cookie"
        get_new_msg = prefix + "/get-new-msg"
        get_history_msg = prefix + "/get-history-msg"
        send_private_msg = prefix + "/send-private-msg"
        upload_media_info = prefix + "/upload-media-info"


class VideoVisibleTypes:
    # 视频可见类型
    # Public: 所有人可见
    # Private: 仅自己可见
    Public = 1
    Private = 3
