"""试验管理API测试"""
import pytest


class TestExperimentsAPI:
    """试验管理API测试"""

    @pytest.mark.asyncio
    async def test_create_experiment(self, client):
        """测试创建试验"""
        response = await client.post("/api/experiments", json={
            "name": "测试试验1",
            "description": "这是一个测试试验"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "测试试验1"
        assert data["description"] == "这是一个测试试验"
        assert data["status"] == "draft"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_create_experiment_without_description(self, client):
        """测试创建试验（无描述）"""
        response = await client.post("/api/experiments", json={
            "name": "测试试验2"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "测试试验2"

    @pytest.mark.asyncio
    async def test_list_experiments(self, client):
        """测试获取试验列表"""
        # 先创建一个
        await client.post("/api/experiments", json={"name": "列表测试试验"})
        response = await client.get("/api/experiments")
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "items" in data
        assert data["total"] >= 1

    @pytest.mark.asyncio
    async def test_get_experiment_detail(self, client):
        """测试获取试验详情"""
        create_resp = await client.post("/api/experiments", json={"name": "详情测试试验"})
        exp_id = create_resp.json()["id"]
        response = await client.get(f"/api/experiments/{exp_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "详情测试试验"
        assert "modules" in data
        assert "params" in data
        assert "constraints" in data

    @pytest.mark.asyncio
    async def test_update_experiment(self, client):
        """测试更新试验"""
        create_resp = await client.post("/api/experiments", json={"name": "更新前"})
        exp_id = create_resp.json()["id"]
        response = await client.put(f"/api/experiments/{exp_id}", json={
            "name": "更新后",
            "description": "已更新"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "更新后"

    @pytest.mark.asyncio
    async def test_delete_experiment(self, client):
        """测试删除试验"""
        create_resp = await client.post("/api/experiments", json={"name": "待删除试验"})
        exp_id = create_resp.json()["id"]
        response = await client.delete(f"/api/experiments/{exp_id}")
        assert response.status_code == 200
        # 验证已删除
        get_resp = await client.get(f"/api/experiments/{exp_id}")
        assert get_resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_nonexistent_experiment(self, client):
        """测试获取不存在的试验"""
        response = await client.get("/api/experiments/99999")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_save_experiment_config(self, client):
        """测试保存试验配置"""
        create_resp = await client.post("/api/experiments", json={"name": "配置测试试验"})
        exp_id = create_resp.json()["id"]
        response = await client.post(f"/api/experiments/{exp_id}/save-config", json={
            "modules": [{"module_name": "absest", "module_id": 1}],
            "params": [{
                "module_name": "absest",
                "param_name": "leftshift",
                "param_id": 2,
                "type_val": "SINGLE",
                "vtype": "Float",
                "raw_description": "取1到10间隔2",
                "parsed_values": [1, 3, 5, 7, 9],
                "is_confirmed": True
            }],
            "constraints": []
        })
        assert response.status_code == 200
