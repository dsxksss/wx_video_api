class WxSDKError(Exception):
    """Base exception for WX Video SDK"""
    pass

class WxAuthError(WxSDKError):
    """Raised when authentication fails"""
    pass

class WxAPIError(WxSDKError):
    """Raised when an API call returns an error"""
    def __init__(self, msg, err_code=None, err_msg=None):
        super().__init__(msg)
        self.err_code = err_code
        self.err_msg = err_msg

class WxNetworkError(WxSDKError):
    """Raised when a network request fails"""
    pass
