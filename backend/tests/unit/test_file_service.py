"""文件服务单元测试"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from io import BytesIO
from PIL import Image
import aiofiles

from src.infrastructure.services.file_service import FileStorageService
from src.application.use_cases.file_upload import (
    UploadTournamentMediaCommand,
    UploadTournamentMediaUseCase,
    DeleteFileCommand,
    DeleteFileUseCase,
)


class MockUploadFile:
    """模拟UploadFile对象"""
    
    def __init__(self, filename: str, content: bytes, content_type: str):
        self.filename = filename
        self.content_type = content_type
        self.file = BytesIO(content)
        self._content = content
    
    async def read(self, size: int = -1) -> bytes:
        if size == -1:
            return self._content
        return self.file.read(size)
    
    async def seek(self, offset: int) -> None:
        self.file.seek(offset)


@pytest.fixture
def temp_upload_dir():
    """创建临时上传目录"""
    with tempfile.TemporaryDirectory() as temp_dir:
        original_path = FileStorageService.__init__
        
        def mock_init(self):
            self.upload_dir = Path(temp_dir)
            self.tournament_media_dir = self.upload_dir / "tournaments"
            self._ensure_directories()
        
        FileStorageService.__init__ = mock_init
        yield temp_dir
        FileStorageService.__init__ = original_path


@pytest.fixture
def file_service(temp_upload_dir):
    """文件服务实例"""
    return FileStorageService()


@pytest.fixture
def sample_image():
    """创建测试图片"""
    # 创建一个简单的RGB图片
    img = Image.new('RGB', (100, 100), color='red')
    img_bytes = BytesIO()
    img.save(img_bytes, format='PNG')
    return img_bytes.getvalue()


class TestFileStorageService:
    """文件存储服务测试"""
    
    def test_directory_creation(self, temp_upload_dir):
        """测试目录创建"""
        service = FileStorageService()
        
        # 检查目录是否创建
        assert (service.upload_dir / "tournaments").exists()
        assert (service.upload_dir / "tournaments" / "logos").exists()
        assert (service.upload_dir / "tournaments" / "banners").exists()
    
    @pytest.mark.asyncio
    async def test_save_tournament_logo_success(self, file_service, sample_image):
        """测试成功保存赛事Logo"""
        # 准备测试文件
        mock_file = MockUploadFile("test_logo.png", sample_image, "image/png")
        
        # 执行保存
        file_path, file_info = await file_service.save_tournament_media(
            mock_file, "logo", "test-tournament-id"
        )
        
        # 验证结果
        assert file_path.startswith("tournaments/logo/")
        assert file_info["original_name"] == "test_logo.png"
        assert file_info["content_type"] == "image/png"
        assert file_info["tournament_id"] == "test-tournament-id"
        assert file_info["width"] > 0
        assert file_info["height"] > 0
        
        # 验证文件确实被保存
        full_path = file_service.upload_dir / file_path
        assert full_path.exists()
    
    @pytest.mark.asyncio
    async def test_save_tournament_banner_success(self, file_service, sample_image):
        """测试成功保存赛事横幅"""
        # 准备测试文件
        mock_file = MockUploadFile("test_banner.jpg", sample_image, "image/jpeg")
        
        # 执行保存
        file_path, file_info = await file_service.save_tournament_media(
            mock_file, "banner"
        )
        
        # 验证结果
        assert file_path.startswith("tournaments/banner/")
        assert file_info["original_name"] == "test_banner.jpg"
        assert file_info["content_type"] == "image/jpeg"
    
    @pytest.mark.asyncio
    async def test_invalid_file_type_rejection(self, file_service):
        """测试拒绝无效文件类型"""
        # 准备无效文件
        invalid_content = b"This is not an image"
        mock_file = MockUploadFile("test.txt", invalid_content, "text/plain")
        
        # 验证抛出异常
        with pytest.raises(ValueError, match="不支持的文件类型"):
            await file_service.save_tournament_media(mock_file, "logo")
    
    @pytest.mark.asyncio
    async def test_file_size_limit(self, file_service):
        """测试文件大小限制"""
        # 创建大文件内容
        large_content = b"x" * (11 * 1024 * 1024)  # 11MB，超过默认10MB限制
        mock_file = MockUploadFile("large.png", large_content, "image/png")
        
        # 验证抛出异常
        with pytest.raises(ValueError, match="文件大小超限"):
            await file_service.save_tournament_media(mock_file, "logo")
    
    @pytest.mark.asyncio
    async def test_delete_existing_file(self, file_service, sample_image):
        """测试删除存在的文件"""
        # 首先保存一个文件
        mock_file = MockUploadFile("test.png", sample_image, "image/png")
        file_path, _ = await file_service.save_tournament_media(mock_file, "logo")
        
        # 验证文件存在
        full_path = file_service.upload_dir / file_path
        assert full_path.exists()
        
        # 删除文件
        result = await file_service.delete_file(file_path)
        
        # 验证删除成功
        assert result is True
        assert not full_path.exists()
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent_file(self, file_service):
        """测试删除不存在的文件"""
        result = await file_service.delete_file("nonexistent/file.png")
        assert result is False
    
    def test_file_url_generation(self, file_service):
        """测试文件URL生成"""
        url = file_service.get_file_url("tournaments/logo/test.png")
        assert url == "/api/v1/files/tournaments/logo/test.png"
    
    def test_full_path_generation(self, file_service):
        """测试完整路径生成"""
        path = file_service.get_full_path("tournaments/logo/test.png")
        expected = file_service.upload_dir / "tournaments/logo/test.png"
        assert path == expected


class TestUploadTournamentMediaUseCase:
    """赛事媒体上传用例测试"""
    
    @pytest.fixture
    def file_service_mock(self):
        """模拟文件服务"""
        return Mock(spec=FileStorageService)
    
    @pytest.fixture 
    def upload_use_case(self, file_service_mock):
        """上传用例实例"""
        return UploadTournamentMediaUseCase(file_service_mock)
    
    @pytest.mark.asyncio
    async def test_successful_logo_upload(self, upload_use_case, file_service_mock, sample_image):
        """测试成功上传Logo"""
        # 准备测试数据
        mock_file = MockUploadFile("logo.png", sample_image, "image/png")
        command = UploadTournamentMediaCommand(
            file=mock_file,
            media_type="logo",
            uploaded_by="user-123"
        )
        
        # 配置mock返回值
        mock_file_info = {
            "id": "file-123",
            "filename": "logo.png",
            "url": "/api/v1/files/tournaments/logo/logo.png",
            "path": "tournaments/logo/logo.png",
            "size": 1024,
            "content_type": "image/png",
            "width": 100,
            "height": 100,
            "format": "PNG",
            "hash": "abc123"
        }
        file_service_mock.save_tournament_media = AsyncMock(
            return_value=("tournaments/logo/logo.png", mock_file_info)
        )
        
        # 执行上传
        result = await upload_use_case.execute(command)
        
        # 验证结果
        assert result.file_id == "file-123"
        assert result.filename == "logo.png"
        assert result.url == "/api/v1/files/tournaments/logo/logo.png"
        assert result.width == 100
        assert result.height == 100
        
        # 验证mock调用
        file_service_mock.save_tournament_media.assert_called_once_with(
            file=mock_file,
            media_type="logo", 
            tournament_id=None
        )
    
    @pytest.mark.asyncio
    async def test_invalid_media_type(self, upload_use_case, sample_image):
        """测试无效媒体类型"""
        mock_file = MockUploadFile("test.png", sample_image, "image/png")
        command = UploadTournamentMediaCommand(
            file=mock_file,
            media_type="invalid",  # 无效类型
            uploaded_by="user-123"
        )
        
        # 验证抛出异常
        with pytest.raises(ValueError, match="不支持的媒体类型"):
            await upload_use_case.execute(command)
    
    @pytest.mark.asyncio
    async def test_empty_filename(self, upload_use_case, sample_image):
        """测试空文件名"""
        mock_file = MockUploadFile(None, sample_image, "image/png")  # 空文件名
        command = UploadTournamentMediaCommand(
            file=mock_file,
            media_type="logo",
            uploaded_by="user-123"
        )
        
        # 验证抛出异常
        with pytest.raises(ValueError, match="文件名不能为空"):
            await upload_use_case.execute(command)
    
    @pytest.mark.asyncio
    async def test_file_service_error_handling(self, upload_use_case, file_service_mock, sample_image):
        """测试文件服务错误处理"""
        mock_file = MockUploadFile("test.png", sample_image, "image/png")
        command = UploadTournamentMediaCommand(
            file=mock_file,
            media_type="logo",
            uploaded_by="user-123"
        )
        
        # 配置mock抛出异常
        file_service_mock.save_tournament_media = AsyncMock(
            side_effect=Exception("磁盘空间不足")
        )
        
        # 验证异常处理
        with pytest.raises(Exception, match="文件上传失败"):
            await upload_use_case.execute(command)


class TestDeleteFileUseCase:
    """删除文件用例测试"""
    
    @pytest.fixture
    def file_service_mock(self):
        """模拟文件服务"""
        return Mock(spec=FileStorageService)
    
    @pytest.fixture
    def delete_use_case(self, file_service_mock):
        """删除用例实例"""
        return DeleteFileUseCase(file_service_mock)
    
    @pytest.mark.asyncio
    async def test_successful_file_deletion(self, delete_use_case, file_service_mock):
        """测试成功删除文件"""
        command = DeleteFileCommand(
            file_path="tournaments/logo/test.png",
            deleted_by="user-123"
        )
        
        # 配置mock返回成功
        file_service_mock.delete_file = AsyncMock(return_value=True)
        
        # 执行删除
        result = await delete_use_case.execute(command)
        
        # 验证结果
        assert result is True
        file_service_mock.delete_file.assert_called_once_with(
            "tournaments/logo/test.png"
        )
    
    @pytest.mark.asyncio
    async def test_file_deletion_failure(self, delete_use_case, file_service_mock):
        """测试文件删除失败"""
        command = DeleteFileCommand(
            file_path="nonexistent.png",
            deleted_by="user-123"
        )
        
        # 配置mock返回失败
        file_service_mock.delete_file = AsyncMock(return_value=False)
        
        # 执行删除
        result = await delete_use_case.execute(command)
        
        # 验证结果
        assert result is False
    
    @pytest.mark.asyncio
    async def test_file_deletion_exception_handling(self, delete_use_case, file_service_mock):
        """测试删除文件异常处理"""
        command = DeleteFileCommand(
            file_path="test.png",
            deleted_by="user-123"
        )
        
        # 配置mock抛出异常
        file_service_mock.delete_file = AsyncMock(
            side_effect=Exception("权限不足")
        )
        
        # 执行删除 - 应该捕获异常并返回False
        result = await delete_use_case.execute(command)
        assert result is False


class TestFileValidationHelpers:
    """文件验证辅助函数测试"""
    
    def test_file_extension_extraction(self, file_service):
        """测试文件扩展名提取"""
        assert file_service._get_file_extension("test.png") == ".png"
        assert file_service._get_file_extension("image.JPEG") == ".jpeg"
        assert file_service._get_file_extension("no_extension") == ".jpg"
        assert file_service._get_file_extension(None) == ".jpg"
    
    def test_image_type_validation(self, file_service):
        """测试图片类型验证"""
        assert file_service._is_valid_image("image/png") is True
        assert file_service._is_valid_image("image/jpeg") is True
        assert file_service._is_valid_image("image/gif") is True
        assert file_service._is_valid_image("image/webp") is True
        assert file_service._is_valid_image("text/plain") is False
        assert file_service._is_valid_image("application/pdf") is False
        assert file_service._is_valid_image(None) is False
    
    @pytest.mark.asyncio
    async def test_file_size_calculation(self, file_service, sample_image):
        """测试文件大小计算"""
        mock_file = MockUploadFile("test.png", sample_image, "image/png")
        
        size = await file_service._get_file_size(mock_file)
        assert size == len(sample_image)
        
        # 验证文件指针位置恢复
        mock_file.file.seek(0)
        content = mock_file.file.read()
        assert len(content) == len(sample_image)