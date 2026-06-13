"""SQLite客户端测试"""
import pytest
from app.utils.sqlite_client import SQLiteClient


class TestSQLiteClient:
    """SQLite只读客户端测试"""

    @pytest.fixture
    def client(self):
        import os
        db_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "geomods_2.0.db")
        client = SQLiteClient(db_path)
        yield client
        client.close()

    def test_get_modules(self, client):
        """测试获取模块列表"""
        result = client.get_modules()
        assert result["total"] > 0
        assert len(result["items"]) > 0
        assert "name" in result["items"][0]

    def test_get_modules_with_keyword(self, client):
        """测试关键词搜索"""
        result = client.get_modules(keyword="absest")
        assert result["total"] >= 1
        assert result["items"][0]["name"] == "absest"

    def test_get_modules_pagination(self, client):
        """测试分页"""
        result = client.get_modules(page=1, page_size=5)
        assert len(result["items"]) <= 5

    def test_get_module_by_id(self, client):
        """测试根据ID获取模块"""
        result = client.get_module_by_id(1)
        assert result is not None
        assert result["name"] == "absest"

    def test_get_module_by_id_not_found(self, client):
        """测试获取不存在的模块"""
        result = client.get_module_by_id(99999)
        assert result is None

    def test_get_params_by_module(self, client):
        """测试获取模块参数"""
        result = client.get_params_by_module(1)
        assert len(result) > 0
        assert result[0]["module_id"] == 1

    def test_get_param_by_id(self, client):
        """测试根据ID获取参数"""
        result = client.get_param_by_id(1)
        assert result is not None
        assert result["name"] == "compid"

    def test_get_params_by_ids(self, client):
        """测试批量获取参数"""
        result = client.get_params_by_ids([1, 2, 3])
        assert len(result) == 3

    def test_get_dependencies_by_module(self, client):
        """测试获取模块依赖"""
        result = client.get_dependencies_by_module(1)
        assert isinstance(result, list)

    def test_get_param_with_module(self, client):
        """测试获取参数及模块信息"""
        result = client.get_param_with_module(1)
        assert result is not None
        assert "module_name" in result

    def test_module_param_count(self, client):
        """测试模块参数数量"""
        result = client.get_modules(page=1, page_size=5)
        for item in result["items"]:
            assert "param_count" in item
            assert item["param_count"] >= 0

    def test_get_dependencies_by_param_ids(self, client):
        """测试批量获取参数依赖"""
        result = client.get_dependencies_by_param_ids([47, 53])
        assert isinstance(result, list)
