import sqlite3
from pathlib import Path
from typing import Optional

from app.config import settings


class SQLiteClient:
    """SQLite只读客户端，用于读取geomods_2.0.db"""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or settings.SQLITE_DB_PATH
        self._conn: Optional[sqlite3.Connection] = None

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            path = Path(self.db_path)
            if not path.exists():
                raise FileNotFoundError(f"SQLite数据库文件不存在: {self.db_path}")
            self._conn = sqlite3.connect(str(path))
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def get_modules(self, keyword: Optional[str] = None, page: int = 1, page_size: int = 20) -> dict:
        """获取模块列表"""
        query = "SELECT * FROM modules"
        count_query = "SELECT COUNT(*) as total FROM modules"
        params = []

        if keyword:
            query += " WHERE name LIKE ?"
            count_query += " WHERE name LIKE ?"
            params.append(f"%{keyword}%")

        # 获取总数
        total = self.conn.execute(count_query, params).fetchone()["total"]

        # 分页
        query += " ORDER BY name LIMIT ? OFFSET ?"
        params.extend([page_size, (page - 1) * page_size])

        rows = self.conn.execute(query, params).fetchall()
        items = [dict(row) for row in rows]

        # 为每个模块添加参数数量
        for item in items:
            count_row = self.conn.execute(
                "SELECT COUNT(*) as cnt FROM parameters WHERE module_id = ?",
                (item["id"],)
            ).fetchone()
            item["param_count"] = count_row["cnt"]

        return {"total": total, "items": items}

    def get_module_by_id(self, module_id: int) -> Optional[dict]:
        """根据ID获取模块"""
        row = self.conn.execute("SELECT * FROM modules WHERE id = ?", (module_id,)).fetchone()
        return dict(row) if row else None

    def get_params_by_module(self, module_id: int) -> list[dict]:
        """获取模块的参数列表"""
        rows = self.conn.execute(
            "SELECT * FROM parameters WHERE module_id = ? ORDER BY class_val, col",
            (module_id,)
        ).fetchall()
        return [dict(row) for row in rows]

    def get_param_by_id(self, param_id: int) -> Optional[dict]:
        """根据ID获取参数"""
        row = self.conn.execute("SELECT * FROM parameters WHERE id = ?", (param_id,)).fetchone()
        return dict(row) if row else None

    def get_params_by_ids(self, param_ids: list[int]) -> list[dict]:
        """根据ID列表获取参数"""
        if not param_ids:
            return []
        placeholders = ",".join("?" * len(param_ids))
        rows = self.conn.execute(
            f"SELECT * FROM parameters WHERE id IN ({placeholders})",
            param_ids
        ).fetchall()
        return [dict(row) for row in rows]

    def get_dependencies_by_module(self, module_id: int) -> list[dict]:
        """获取模块参数的依赖关系"""
        rows = self.conn.execute(
            """SELECT d.*, p.name as param_name, p.module_id
               FROM dependencies d
               JOIN parameters p ON d.parameter_id = p.id
               WHERE p.module_id = ?""",
            (module_id,)
        ).fetchall()
        return [dict(row) for row in rows]

    def get_dependencies_by_param_ids(self, param_ids: list[int]) -> list[dict]:
        """根据参数ID列表获取依赖关系"""
        if not param_ids:
            return []
        placeholders = ",".join("?" * len(param_ids))
        rows = self.conn.execute(
            f"""SELECT d.*, p.name as param_name, p.module_id, m.name as module_name
                FROM dependencies d
                JOIN parameters p ON d.parameter_id = p.id
                JOIN modules m ON p.module_id = m.id
                WHERE d.parameter_id IN ({placeholders})""",
            param_ids
        ).fetchall()
        return [dict(row) for row in rows]

    def get_param_with_module(self, param_id: int) -> Optional[dict]:
        """获取参数及其所属模块信息"""
        row = self.conn.execute(
            """SELECT p.*, m.name as module_name
               FROM parameters p
               JOIN modules m ON p.module_id = m.id
               WHERE p.id = ?""",
            (param_id,)
        ).fetchone()
        return dict(row) if row else None

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None


# 全局单例
sqlite_client = SQLiteClient()
