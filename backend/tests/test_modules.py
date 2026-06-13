"""模块与参数API测试"""
import pytest


class TestModulesAPI:
    """模块API测试"""

    @pytest.mark.asyncio
    async def test_list_modules_default(self, client):
        """测试默认获取模块列表"""
        response = await client.get("/api/modules")
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "items" in data
        assert data["total"] > 0
        assert len(data["items"]) > 0

    @pytest.mark.asyncio
    async def test_list_modules_with_keyword(self, client):
        """测试关键词搜索模块"""
        response = await client.get("/api/modules", params={"keyword": "absest"})
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert any(m["name"] == "absest" for m in data["items"])

    @pytest.mark.asyncio
    async def test_list_modules_pagination(self, client):
        """测试模块列表分页"""
        response = await client.get("/api/modules", params={"page": 1, "page_size": 5})
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) <= 5

    @pytest.mark.asyncio
    async def test_list_modules_empty_keyword(self, client):
        """测试空关键词搜索"""
        response = await client.get("/api/modules", params={"keyword": ""})
        assert response.status_code == 200
        data = response.json()
        assert data["total"] > 0

    @pytest.mark.asyncio
    async def test_list_modules_not_found_keyword(self, client):
        """测试搜索不存在的模块"""
        response = await client.get("/api/modules", params={"keyword": "zzz_nonexistent_module"})
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert len(data["items"]) == 0


class TestModuleParamsAPI:
    """模块参数API测试"""

    @pytest.mark.asyncio
    async def test_get_module_params(self, client):
        """测试获取模块参数列表"""
        response = await client.get("/api/modules/1/params")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        # 验证参数字段
        param = data[0]
        assert "id" in param
        assert "name" in param
        assert "type_val" in param
        assert "vtype" in param
        assert "module_name" in param

    @pytest.mark.asyncio
    async def test_get_module_params_has_module_name(self, client):
        """测试参数列表包含module_name"""
        response = await client.get("/api/modules/1/params")
        assert response.status_code == 200
        data = response.json()
        for param in data:
            assert param["module_name"] is not None

    @pytest.mark.asyncio
    async def test_get_module_params_types(self, client):
        """测试参数包含各种类型"""
        response = await client.get("/api/modules/1/params")
        assert response.status_code == 200
        data = response.json()
        type_vals = {p["type_val"] for p in data}
        # absest模块应该有SINGLE和SELECT类型
        assert "SINGLE" in type_vals or "SELECT" in type_vals

    @pytest.mark.asyncio
    async def test_get_module_params_select_items(self, client):
        """测试SELECT类型参数有select_items"""
        # absest模块的hodsrc参数是SELECT类型
        response = await client.get("/api/modules/1/params")
        assert response.status_code == 200
        data = response.json()
        select_params = [p for p in data if p["type_val"] == "SELECT"]
        if select_params:
            for sp in select_params:
                assert sp["select_items"] is not None

    @pytest.mark.asyncio
    async def test_get_module_dependencies(self, client):
        """测试获取模块依赖关系"""
        response = await client.get("/api/modules/1/dependencies")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestHealthAPI:
    """健康检查API测试"""

    @pytest.mark.asyncio
    async def test_health_check(self, client):
        """测试健康检查"""
        response = await client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
