# 微信视频号助手 (wx_video_sdk) v1.2.0

## 功能介绍

微信视频号助手是一个自动化工具，可以帮助视频号运营者自动执行以下任务：

1. **数据统计与导出**：自动收集视频播放、点赞、评论等数据，并支持CSV格式导出
2. **视频可见性管理**：根据设定的条件（如播放量）自动调整视频可见性
3. **自动回复评论**：自动回复视频下的评论，支持随机回复内容
4. **自动回复私信**：自动回复用户私信，支持文字和图片，支持随机回复内容，且支持**关键字过滤触发**
5. **数据报告生成**：自动生成视频数据报告

## 安装与运行

本工程已升级至使用现代 Python 依赖管理工具 [uv](https://github.com/astral-sh/uv)。

### 运行环境要求

- Python 3.12+ (推荐)

### 开发与本地运行

1. 安装 `uv` 工具（若尚未安装）：
   ```bash
   pip install uv
   ```
2. 使用 `uv` 运行主程序（`uv` 会自动下载并配置 `.venv` 环境）：
   ```bash
   uv run main.py
   ```
   或者使用 `uv` 同步项目依赖环境：
   ```bash
   uv sync
   ```

### 打包为可执行文件 (PyInstaller)

本工程包含 `main.spec` 配置文件，可通过以下命令直接打包成单文件二进制可执行程序：

```bash
uv run pyinstaller --clean main.spec
```
或者使用原生 PyInstaller 命令：
```bash
pyinstaller -F -i icon.png main.py
```

## 使用说明

1. 修改`config.toml`配置文件，根据需要调整各项参数（例如配置自动回复文本、私信关键字等）
2. 运行程序：
   - 直接运行：`uv run main.py`
   - 或者运行打包后的可执行文件

## 开发者指南 (SDK使用)

该项目已经过重构，开发人员可以非常方便地将其作为 SDK 引入自己的项目：

```python
from wx_video_sdk import WXVideoClient, AppConfig, __version__

print(f"SDK Version: {__version__}")

# 加载配置
config = AppConfig.load_from_toml("config.toml")

# 初始化客户端并登录（先尝试缓存，失败自动扫码）
client = WXVideoClient(cache_file_path="./caches/account.json")
client.login()

# 调用 API (例如获取视频列表)
videos = client.get_video_list(page_size=10)
```

> 如需精细控制，仍可分别调用 `client.login_with_cache()` 和 `client.login_with_qrcode()`。

### 核心类说明
- `WXVideoClient`: 封装了底层的微信视频号助手 API
- `WXVideoAssistant`: 封装了高层自动化逻辑（自动回复、定时任务等）
- `AppConfig`: 结构化的配置管理类

## 配置文件说明

`config.toml` 配置文件详细说明：

```toml
# 脚本配置
[run_config]
# 运行延迟间隔，值越小脚本处理速度越快，不建议小于1，默认4
run_delay = 4
# 设置最近输出几天之内要查看的视频数据(按该视频创建的时间)，默认2，设置成0则不会处理
create_video_report_days = 2
# 心跳检查间隔（秒），默认60秒检查一次会话状态
heartbeat_interval = 60
# 是否开启日志详细模式(0:关闭, 1:开启)，默认0
verbose_logging = 0

# 视频可见性管理配置
[auto_video_visible]
# 是否开启自动修改视频可见功能(0:关闭, 1:开启)，默认1
visible_target = 1
# 设置最近几天之内要处理的视频(按该视频创建的时间)，默认2，设置成0则不会处理
auto_video_visible_days = 2
# 设置当浏览量大于多少要处理的视频(和days配置配合使用)，默认5500
max_video_count = 5500
# 设置当以上两个配置都触发后的视频是否公开或隐藏(1:所有人可见,3:仅自己可见)，默认值3
video_visible_type = 3
# 任务执行间隔（秒），默认300秒执行一次
task_interval = 300

# 评论自动回复配置
[auto_send_comment]
# 是否开启评论自动回复(0:关闭, 1:开启)，默认1
comment_target = 1
# 回复自己的评论(0:关闭, 1:开启)，默认0
self_comment_target = 0
# 设置最近几天之内要处理的评论(按该评论创建的时间)，默认2，设置成0则不会处理
auto_send_comment_days = 2
# 自动回复评论内容
auto_send_comment_text = "感谢您的评论"
# 任务执行间隔（秒），默认120秒执行一次
task_interval = 120
# 多条随机回复文本，用英文分号;分隔，如果不设置则使用auto_send_comment_text
random_replies = "感谢您的评论;谢谢支持;已收到您的评论，感谢反馈"

# 私信自动回复配置
[auto_send_private_msg]
# 是否开启消息发送(0:关闭, 1:开启)，默认1
private_msg_target = 1
# 是否开启图片发送(0:关闭, 1:开启)，默认0（关掉以免重复打扰，需要再开）
private_img_target = 0
# 设置最近几天之内要处理的私信(按该私信创建的时间)，默认1，设置成0则不会处理
auto_send_msg_days = 1
# 自动回复私信文字内容（random_replies 留空时用这条作为默认兜底）
auto_send_private_msg = "感谢私信！商品详情请点击：https://example.com/product"
# 自动回复私信图片文件路径
auto_send_img_path = "./icon.png"
# 任务执行间隔（秒），默认60秒执行一次
task_interval = 60
# 多条随机回复文本，用英文分号;分隔，如果不设置则使用auto_send_private_msg
random_replies = "感谢私信～商品在这里：https://example.com/product-a;您好，商品链接奉上：https://example.com/product-b"
# 关键字触发：留空数组 [] 表示所有新私信都回；填了关键字则只回包含其中任一关键字的私信（不区分大小写，子串匹配）
trigger_keywords = ["666"]

# 数据导出配置
[data_export]
# 是否开启数据导出(0:关闭, 1:开启)，默认1
export_target = 1
# 数据导出间隔（秒），默认3600秒(1小时)执行一次
export_interval = 3600
# 数据导出路径，默认./视频数据
export_path = "./视频数据"
# 是否导出CSV格式(0:关闭, 1:开启)，默认1
export_csv = 1
```

## 新功能说明

### v1.2.0 更新内容

1. **私信关键字匹配回复**：引入 `trigger_keywords` 配置过滤，现在支持仅针对包含指定关键字（例如 `"666"`）的私信进行自动回复。
2. **规范命名重构**：底层 SDK 代码接口方法全面重构为 Python 官方推荐的 `snake_case`（蛇形命名法），清理并淘汰了全部旧版驼峰命名兼容方法。
3. **移除多余生成器**：删除了 SDK Client 中多余的 Generator 迭代设计（如 `iter_videos`），直接采用直观的列表遍历及 API 交互。
4. **包与依赖工具链现代化**：正式弃用 `requirements.txt`，采用 `uv` + `pyproject.toml` 的项目管理体系。

### v1.1.0 更新内容

1. **随机回复功能**：评论和私信支持设置多条回复内容，随机选择一条回复
2. **数据导出功能**：定期自动导出视频数据为CSV格式，方便后续分析
3. **任务间隔设置**：每种任务可单独设置执行间隔，避免频繁操作
4. **优化错误处理**：更完善的错误处理和日志记录
5. **优雅退出机制**：捕获退出信号，确保程序能够安全退出并保存数据

## 常见问题

1. **登录失败**：
   - 检查网络连接
   - 清空caches目录后重新登录

2. **API调用失败**：
   - 检查日志文件了解详细错误
   - 可能是接口变更，请等待更新

3. **频繁操作导致账号风险**：
   - 适当调大各任务的执行间隔

## 注意事项

- 本工具仅用于辅助运营，请勿用于违规内容
- 避免过于频繁的操作，以免触发微信风控
- 定期备份导出的数据
