from wx_video_sdk.client import WXVideoClient
from wx_video_sdk.assistant import WXVideoAssistant
from wx_video_sdk.models import AppConfig

__version__ = "1.2.0"

# Generic name for easier identification in main.py if needed, 
# although using specific classes is better for developers.
WXVideoSDK = WXVideoClient

__all__ = ["WXVideoClient", "WXVideoAssistant", "AppConfig", "WXVideoSDK", "__version__"]
