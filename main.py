import logging
import os
import signal
import sys
import traceback
import urllib3
import questionary

from wx_video_sdk import WXVideoClient, WXVideoAssistant, AppConfig
from wx_video_sdk.utils import (
    is_dev,
    mkdir_if_not_exist,
    setLoggingDefaultConfig,
    install_ssl_cert,
)

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class App:
    def __init__(self):
        self.config_path = "./config_test.toml" if is_dev() else "./config.toml"
        self.config = AppConfig.load_from_toml(self.config_path)
        self.assistant = None
        
        # Setup logging
        setLoggingDefaultConfig()
        level = 15 if self.config.run_config.verbose_logging == 1 else logging.INFO
        logging.getLogger().setLevel(level)
        
        # Signal handling
        signal.signal(signal.SIGINT, self.handle_exit)
        signal.signal(signal.SIGTERM, self.handle_exit)

    def handle_exit(self, sig, frame):
        logging.info("Terminating gracefully...")
        if self.assistant:
            self.assistant.stop()
        sys.exit(0)

    def select_account(self) -> str:
        caches_dir = "./caches/"
        mkdir_if_not_exist(caches_dir)
        options = [f for f in os.listdir(caches_dir) if f.endswith(".json")]
        
        if not options:
            return "Scan QR Code"
            
        options.append("Scan QR Code for new account")
        selected = questionary.select(
            "Select an account to login:",
            choices=options
        ).ask()
        
        if selected is None:
            return None
        if "Scan QR Code" in selected:
            return "Scan QR Code"
        return os.path.join(caches_dir, selected)

    def run(self):
        install_ssl_cert()
        
        account_path = self.select_account()
        if account_path is None:
            logging.info("Login cancelled.")
            return

        # Initialize Client
        # If it's a new account, we'll initialize without path first or with a default path
        # Actually the Client saves to cache if cache_handler is present.
        
        if account_path == "Scan QR Code":
            client = WXVideoClient(cache_file_path=None)
            client.login_with_qrcode()
        else:
            client = WXVideoClient(cache_file_path=account_path)
            client.login()

        self.assistant = WXVideoAssistant(client, self.config)
        self.assistant.start_loop()

def main():
    # Handle dev mode flag without global argparse side effects
    if "-d" in sys.argv:
        os.environ["WX_SDK_DEV"] = "1"
        
    try:
        app = App()
        app.run()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logging.error(f"Application crashed: {e}")
        logging.error(traceback.format_exc())
        input("Press any key to exit...")
        sys.exit(1)

if __name__ == "__main__":
    main()
