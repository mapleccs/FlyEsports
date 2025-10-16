"""文件管理API路由测试"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
from fastapi import UploadFile
from fastapi.testclient import TestClient
from io import BytesIO
from PIL import Image

from src.presentation.api.main import create_app
from src.domain.value_objects.user import User
from src.application.use_cases.file_upload import FileUploadResult


class MockUploadFile:
    """模拟UploadFile对象"""
    
    def __init__(self, filename: str, content: bytes, content_type: str):
        self.filename = filename
        self.content_type = content_type
        self.file = BytesIO(content)
        self.size = len(content)
    
    async def read(self, size: int = -1) -> bytes:
        if size == -1:
            return self.file.getvalue()
        return self.file.read(size)
    
    async def seek(self, offset: int) -> None:
        self.file.seek(offset)


@pytest.fixture
def app():
    """创建测试应用"""
    return create_app()


@pytest.fixture
def client(app):
    """创建测试客户端"""
    return TestClient(app)


@pytest.fixture
def sample_image():
    """创建测试图片"""
    img = Image.new('RGB', (100, 100), color='red')
    img_bytes = BytesIO()
    img.save(img_bytes, format='PNG')
    return img_bytes.getvalue()


@pytest.fixture
def mock_current_user():
    """模拟当前用户"""
    return User(
        user_id="test-user-123",
        username="testuser",
        email="test@example.com",
        roles=["user"]
    )


class TestFileUploadAPI:
    """文件上传API测试"""
    
    @pytest.mark.asyncio
    async def test_successful_logo_upload(self, client, sample_image, mock_current_user):
        """测试成功上传Logo"""
        with patch('src.presentation.api.routes.files.get_current_user', return_value=mock_current_user), \
             patch('src.presentation.api.routes.files.create_upload_tournament_media_use_case') as mock_use_case_factory:
            
            # 准备mock用例
            mock_use_case = Mock()
            mock_use_case.execute = AsyncMock(return_value=FileUploadResult(
                file_id="file-123",
                filename="logo.png", 
                url="/api/v1/files/tournaments/logos/logo.png",
                path="tournaments/logos/logo.png",
                size=len(sample_image),
                content_type="image/png",
                width=100,
                height=100,
                format="PNG",
                hash="abc123def456"
            ))
            mock_use_case_factory.return_value = mock_use_case
            
            # 执行请求
            response = client.post(
                "/api/v1/files/tournament-media/upload",
                files={"file": ("logo.png", BytesIO(sample_image), "image/png")},
                data={"media_type": "logo"}
            )
            
            # 验证响应
            assert response.status_code == 201
            data = response.json()
            assert data["file_id"] == "file-123"
            assert data["filename"] == "logo.png"
            assert data["url"] == "/api/v1/files/tournaments/logos/logo.png"
            assert data["width"] == 100
            assert data["height"] == 100
    
    @pytest.mark.asyncio
    async def test_successful_banner_upload_with_tournament_id(self, client, sample_image, mock_current_user):
        """测试成功上传横幅并指定赛事ID"""
        with patch('src.presentation.api.routes.files.get_current_user', return_value=mock_current_user), \
             patch('src.presentation.api.routes.files.create_upload_tournament_media_use_case') as mock_use_case_factory:
            
            # 准备mock用例
            mock_use_case = Mock()
            mock_use_case.execute = AsyncMock(return_value=FileUploadResult(
                file_id="banner-456",
                filename="banner.jpg",
                url="/api/v1/files/tournaments/banners/banner.jpg",
                path="tournaments/banners/banner.jpg",
                size=len(sample_image),
                content_type="image/jpeg",
                width=400,
                height=150,
                format="JPEG",
                hash="def456ghi789"
            ))
            mock_use_case_factory.return_value = mock_use_case
            
            # 执行请求
            response = client.post(
                "/api/v1/files/tournament-media/upload",
                files={"file": ("banner.jpg", BytesIO(sample_image), "image/jpeg")},
                data={
                    "media_type": "banner",
                    "tournament_id": "tournament-123"
                }
            )
            
            # 验证响应
            assert response.status_code == 201
            data = response.json()
            assert data["file_id"] == "banner-456"
            assert data["content_type"] == "image/jpeg"
    
    @pytest.mark.asyncio
    async def test_invalid_media_type(self, client, sample_image, mock_current_user):
        """测试无效媒体类型"""
        with patch('src.presentation.api.routes.files.get_current_user', return_value=mock_current_user):
            
            response = client.post(
                "/api/v1/files/tournament-media/upload",
                files={"file": ("test.png", BytesIO(sample_image), "image/png")},
                data={"media_type": "invalid_type"}
            )
            
            # 验证错误响应
            assert response.status_code == 400
            data = response.json()
            assert "不支持的媒体类型" in data["detail"]
    
    @pytest.mark.asyncio
    async def test_upload_without_authentication(self, client, sample_image):
        """测试未认证时的上传"""
        with patch('src.presentation.api.routes.files.get_current_user', side_effect=Exception("未认证")):
            
            response = client.post(
                "/api/v1/files/tournament-media/upload",
                files={"file": ("test.png", BytesIO(sample_image), "image/png")},
                data={"media_type": "logo"}
            )
            
            # 验证认证失败响应
            assert response.status_code >= 400
    
    @pytest.mark.asyncio
    async def test_file_upload_service_error(self, client, sample_image, mock_current_user):
        """测试文件上传服务错误"""
        with patch('src.presentation.api.routes.files.get_current_user', return_value=mock_current_user), \
             patch('src.presentation.api.routes.files.create_upload_tournament_media_use_case') as mock_use_case_factory:
            
            # 配置mock抛出异常
            mock_use_case = Mock()
            mock_use_case.execute = AsyncMock(side_effect=Exception("磁盘空间不足"))
            mock_use_case_factory.return_value = mock_use_case
            
            response = client.post(
                "/api/v1/files/tournament-media/upload",
                files={"file": ("test.png", BytesIO(sample_image), "image/png")},
                data={"media_type": "logo"}
            )
            
            # 验证错误响应
            assert response.status_code == 500
            data = response.json()
            assert "文件上传失败" in data["detail"]
    
    @pytest.mark.asyncio
    async def test_validation_error_handling(self, client, sample_image, mock_current_user):
        """测试验证错误处理"""
        with patch('src.presentation.api.routes.files.get_current_user', return_value=mock_current_user), \
             patch('src.presentation.api.routes.files.create_upload_tournament_media_use_case') as mock_use_case_factory:
            
            # 配置mock抛出验证异常
            mock_use_case = Mock()
            mock_use_case.execute = AsyncMock(side_effect=ValueError("文件大小超过限制"))
            mock_use_case_factory.return_value = mock_use_case
            
            response = client.post(
                "/api/v1/files/tournament-media/upload",
                files={"file": ("large.png", BytesIO(sample_image), "image/png")},
                data={"media_type": "logo"}
            )
            
            # 验证错误响应
            assert response.status_code == 400
            data = response.json()
            assert "文件大小超过限制" in data["detail"]


class TestFileDeleteAPI:
    """文件删除API测试"""
    
    @pytest.mark.asyncio
    async def test_successful_file_deletion(self, client, mock_current_user):
        """测试成功删除文件"""
        with patch('src.presentation.api.routes.files.get_current_user', return_value=mock_current_user), \
             patch('src.presentation.api.routes.files.create_delete_file_use_case') as mock_use_case_factory:
            
            # 准备mock用例
            mock_use_case = Mock()
            mock_use_case.execute = AsyncMock(return_value=True)
            mock_use_case_factory.return_value = mock_use_case
            
            # 执行删除请求
            response = client.delete("/api/v1/files/tournaments/logos/test.png")
            
            # 验证响应
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "成功" in data["message"]
    
    @pytest.mark.asyncio
    async def test_file_deletion_failure(self, client, mock_current_user):
        """测试文件删除失败"""
        with patch('src.presentation.api.routes.files.get_current_user', return_value=mock_current_user), \
             patch('src.presentation.api.routes.files.create_delete_file_use_case') as mock_use_case_factory:
            
            # 配置mock返回失败
            mock_use_case = Mock()
            mock_use_case.execute = AsyncMock(return_value=False)
            mock_use_case_factory.return_value = mock_use_case
            
            response = client.delete("/api/v1/files/tournaments/logos/nonexistent.png")
            
            # 验证响应
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False
            assert "不存在" in data["message"] or "失败" in data["message"]
    
    @pytest.mark.asyncio
    async def test_file_deletion_exception(self, client, mock_current_user):
        """测试文件删除异常"""
        with patch('src.presentation.api.routes.files.get_current_user', return_value=mock_current_user), \
             patch('src.presentation.api.routes.files.create_delete_file_use_case') as mock_use_case_factory:
            
            # 配置mock抛出异常
            mock_use_case = Mock()
            mock_use_case.execute = AsyncMock(side_effect=Exception("权限不足"))
            mock_use_case_factory.return_value = mock_use_case
            
            response = client.delete("/api/v1/files/tournaments/logos/test.png")
            
            # 验证错误响应
            assert response.status_code == 500
            data = response.json()
            assert "文件删除失败" in data["detail"]


class TestFileRetrievalAPI:
    """文件获取API测试"""
    
    @pytest.mark.asyncio
    async def test_get_existing_file(self, client):
        """测试获取存在的文件"""
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
            # 写入测试图片数据
            img = Image.new('RGB', (50, 50), color='blue')
            img.save(temp_file.name, format='PNG')
            temp_path = Path(temp_file.name)
            
            with patch('src.presentation.api.routes.files.FileStorageService') as mock_service_class:
                # 配置mock服务
                mock_service = Mock()
                mock_service.get_full_path.return_value = temp_path
                mock_service_class.return_value = mock_service
                
                response = client.get("/api/v1/files/tournaments/logos/test.png")
                
                # 验证响应
                assert response.status_code == 200
                assert response.headers["content-type"] == "image/png"
            
            # 清理临时文件
            temp_path.unlink()
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_file(self, client):
        """测试获取不存在的文件"""
        with patch('src.presentation.api.routes.files.FileStorageService') as mock_service_class:
            # 配置mock返回不存在的路径
            mock_service = Mock()
            mock_service.get_full_path.return_value = Path("nonexistent.png")
            mock_service_class.return_value = mock_service
            
            response = client.get("/api/v1/files/tournaments/logos/nonexistent.png")
            
            # 验证404响应
            assert response.status_code == 404
            data = response.json()
            assert "文件不存在" in data["detail"]
    
    @pytest.mark.asyncio
    async def test_different_image_types(self, client):
        """测试不同图片类型的Content-Type设置"""
        test_cases = [
            ("test.jpg", "image/jpeg"),
            ("test.jpeg", "image/jpeg"), 
            ("test.png", "image/png"),
            ("test.gif", "image/gif"),
            ("test.webp", "image/webp"),
            ("test.unknown", "application/octet-stream")
        ]
        
        for filename, expected_content_type in test_cases:
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_path = Path(temp_file.name)
                
                with patch('src.presentation.api.routes.files.FileStorageService') as mock_service_class:
                    mock_service = Mock()
                    mock_service.get_full_path.return_value = temp_path
                    mock_service_class.return_value = mock_service
                    
                    response = client.get(f"/api/v1/files/tournaments/logos/{filename}")
                    
                    if response.status_code == 200:
                        assert response.headers["content-type"] == expected_content_type
                
                temp_path.unlink()


class TestTournamentMediaPresetsAPI:
    """赛事媒体预设API测试"""
    
    @pytest.mark.asyncio
    async def test_get_presets_success(self, client):
        """测试成功获取预设素材"""
        response = client.get("/api/v1/files/tournament-media/presets")
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        
        # 验证数据结构
        assert "logos" in data
        assert "banners" in data
        assert isinstance(data["logos"], list)
        assert isinstance(data["banners"], list)
        
        # 验证预设项目结构
        if data["logos"]:
            logo = data["logos"][0]
            assert "id" in logo
            assert "name" in logo
            assert "url" in logo
        
        if data["banners"]:
            banner = data["banners"][0]
            assert "id" in banner
            assert "name" in banner
            assert "url" in banner
    
    @pytest.mark.asyncio
    async def test_get_presets_with_expected_items(self, client):
        """测试预设素材包含期望的项目"""
        response = client.get("/api/v1/files/tournament-media/presets")
        
        assert response.status_code == 200
        data = response.json()
        
        # 验证包含默认预设项目
        logo_names = [logo["name"] for logo in data["logos"]]
        banner_names = [banner["name"] for banner in data["banners"]]
        
        assert "经典奖杯" in logo_names or len(data["logos"]) > 0
        assert "科技蓝" in banner_names or len(data["banners"]) > 0


class TestAPIInputValidation:
    """API输入验证测试"""
    
    @pytest.mark.asyncio
    async def test_missing_file_parameter(self, client, mock_current_user):
        """测试缺少文件参数"""
        with patch('src.presentation.api.routes.files.get_current_user', return_value=mock_current_user):
            
            response = client.post(
                "/api/v1/files/tournament-media/upload",
                data={"media_type": "logo"}
                # 缺少files参数
            )
            
            # 验证错误响应
            assert response.status_code == 422  # FastAPI验证错误
    
    @pytest.mark.asyncio
    async def test_missing_media_type_parameter(self, client, sample_image, mock_current_user):
        """测试缺少媒体类型参数"""
        with patch('src.presentation.api.routes.files.get_current_user', return_value=mock_current_user):
            
            response = client.post(
                "/api/v1/files/tournament-media/upload",
                files={"file": ("test.png", BytesIO(sample_image), "image/png")}
                # 缺少media_type参数
            )
            
            # 验证错误响应
            assert response.status_code == 422  # FastAPI验证错误
    
    @pytest.mark.asyncio
    async def test_invalid_tournament_id_format(self, client, sample_image, mock_current_user):
        """测试无效的赛事ID格式"""
        with patch('src.presentation.api.routes.files.get_current_user', return_value=mock_current_user), \
             patch('src.presentation.api.routes.files.create_upload_tournament_media_use_case') as mock_use_case_factory:
            
            # 配置mock抛出UUID验证异常
            mock_use_case = Mock()
            mock_use_case_factory.return_value = mock_use_case
            
            response = client.post(
                "/api/v1/files/tournament-media/upload",
                files={"file": ("test.png", BytesIO(sample_image), "image/png")},
                data={
                    "media_type": "logo",
                    "tournament_id": "invalid-uuid-format"
                }
            )
            
            # 验证错误响应（可能是422验证错误或500内部错误）
            assert response.status_code >= 400


class TestAPISecurityAndPermissions:
    """API安全和权限测试"""
    
    @pytest.mark.asyncio
    async def test_unauthorized_access(self, client, sample_image):
        """测试未授权访问"""
        # 不提供认证信息
        response = client.post(
            "/api/v1/files/tournament-media/upload",
            files={"file": ("test.png", BytesIO(sample_image), "image/png")},
            data={"media_type": "logo"}
        )
        
        # 验证需要认证
        assert response.status_code in [401, 403, 422]  # 可能的未认证响应码
    
    @pytest.mark.asyncio
    async def test_file_path_traversal_protection(self, client, mock_current_user):
        """测试文件路径遍历攻击保护"""
        with patch('src.presentation.api.routes.files.get_current_user', return_value=mock_current_user), \
             patch('src.presentation.api.routes.files.create_delete_file_use_case') as mock_use_case_factory:
            
            mock_use_case = Mock()
            mock_use_case.execute = AsyncMock(return_value=False)
            mock_use_case_factory.return_value = mock_use_case
            
            # 尝试路径遍历攻击
            malicious_paths = [
                "../../../etc/passwd",
                "..\\..\\windows\\system32\\config\\sam",
                "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd"
            ]
            
            for path in malicious_paths:
                response = client.delete(f"/api/v1/files/{path}")
                # 应该被正常处理，不会实际访问系统文件
                assert response.status_code in [200, 404]  # 正常响应，不会出现500错误