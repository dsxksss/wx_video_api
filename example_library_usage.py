import logging
from wx_video_sdk import WXVideoClient

# This script demonstrates how to use the SDK as a library 
# to perform specific tasks programmatically.

def main():
    # Setup basic logging
    logging.basicConfig(level=logging.INFO)
    
    # Initialize the client with a specific cache file, then login.
    # client.login() tries the cache first and falls back to QR scan automatically.
    client = WXVideoClient(cache_file_path="./caches/your_nickname.json")
    client.login()

    print(f"Logged in as: {client.nick_name}")

    # Example 1: Get the last 5 videos
    videos = client.get_video_list(page_size=5)
    print(f"\nRecent Videos ({len(videos)}):")
    for v in videos:
        title = v.get("desc", {}).get("description", "No Title")
        reads = v.get("readCount", 0)
        print(f"- {title} | Reads: {reads}")
    
    # Example 2: Check for new private messages
    msgs = client.get_new_private_msgs()
    if msgs:
        print(f"\nFound {len(msgs)} new private messages.")
        for m in msgs:
            print(f"From: {m['fromUsername']} | Time: {m['ts']}")
    else:
        print("\nNo new private messages.")

if __name__ == "__main__":
    main()
