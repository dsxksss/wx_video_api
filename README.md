# 脚本打包

```bash
pyinstaller -F -i icon.png main.py
```
data, _= self.request(WxVApiFields.Auth.auth_data)

        if data["errCode"] != 0:
            logging.error("你的身份验证失败，请关闭程序重新扫描登录")
            self.cache_handler.removeCache("self")
            input("按任意键关闭程序")
            sys.exit(1)

        # 保存获取的用户标识
        self.finder_username = data["finderUser"]["finderUsername"]
        self.nick_name = data["finderUser"]["nickname"]
