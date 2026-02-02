from typing import Any, Dict, List, Optional
from tinydb import TinyDB, Query


class CacheHandler:
    def __init__(self, save_path: str):
        self.db = TinyDB(save_path)
        self.query = Query()

    def is_exists(self, name: str) -> bool:
        """Check if a record with the given name exists."""
        return self.db.contains(self.query.name == name)

    def save_cache(self, name: str, key: str, value: Any) -> None:
        """Insert a new cache record if it doesn't exist."""
        if not self.is_exists(name):
            self.db.insert({"name": name, key: value})

    def update_cache(self, name: str, key: str, value: Any) -> None:
        """Update an existing cache record."""
        self.db.update({key: value}, self.query.name == name)

    def get_cache(self, name: str) -> Dict[str, Any]:
        """Retrieve a cache record by name. Returns empty dict if not found."""
        result = self.db.get(self.query.name == name)
        return dict(result) if result else {}

    def get_all_caches(self) -> List[Dict[str, Any]]:
        """Return all cache records."""
        return self.db.all()

    def remove_cache(self, name: str) -> None:
        """Delete a cache record by name."""
        self.db.remove(self.query.name == name)

    def clear(self) -> None:
        """Truncate the entire database."""
        self.db.truncate()

    # Alias for backward compatibility if needed, but better to use snake_case
    isExists = is_exists
    saveCache = save_cache
    updateCache = update_cache
    getCache = get_cache
    removeCache = remove_cache
