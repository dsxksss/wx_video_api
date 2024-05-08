from typing import Any, Dict, List
from tinydb import TinyDB, Query


class CacheHandler:
    def __init__(self, save_path: str):
        self.db = TinyDB(save_path)

    # 检查数据是否已存在
    def isExists(self, name: str) -> bool:
        result = self.db.search(Query().name == name)
        return len(result) > 0

    # 存储缓存
    def saveCache(self, name: str, key: str, value: Any) -> None:
        if not self.isExists(name):
            self.db.insert({"name": name, key: value})

    # 更新缓存
    def updateCache(self, name: str, key: str, value: Any) -> None:
        self.db.update({key: value}, Query().name == name)

    # 获取缓存
    def getCache(self, name: str) -> Dict[str, Any]:
        data = self.db.search(Query().name == name)
        result = data[0]
        return result if result else dict()

    # 获取全部缓存
    def getCacheList(self) -> List[Any]:
        return self.db.all()

    # 根据缓存名删除某个缓存
    def removeCache(self, name: str) -> None:
        self.db.remove(Query().name == name)

    # 清空缓存
    def clearCache(self) -> None:
        self.db.clear_cache()
