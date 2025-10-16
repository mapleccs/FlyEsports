"""WebSocket端到端测试"""

import asyncio
import json
from uuid import uuid4
import pytest
import websockets
from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK

from tests.conftest import test_user_token


class TestWebSocketConnections:
    """WebSocket连接测试"""
    
    @pytest.mark.asyncio
    async def test_websocket_match_connection_without_token(self):
        """测试无token的WebSocket连接应该被拒绝"""
        match_id = str(uuid4())
        uri = f"ws://localhost:8000/ws/matches/{match_id}"
        
        with pytest.raises((ConnectionClosedError, ConnectionClosedOK)):
            async with websockets.connect(uri) as websocket:
                # 应该在连接时就被拒绝
                await websocket.recv()
    
    @pytest.mark.asyncio
    async def test_websocket_match_connection_with_invalid_token(self):
        """测试无效token的WebSocket连接应该被拒绝"""
        match_id = str(uuid4())
        uri = f"ws://localhost:8000/ws/matches/{match_id}?token=invalid_token"
        
        with pytest.raises((ConnectionClosedError, ConnectionClosedOK)):
            async with websockets.connect(uri) as websocket:
                await websocket.recv()
    
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="需要有效的JWT token和真实的match_id")
    async def test_websocket_match_connection_with_valid_token(self, test_user_token):
        """测试有效token的WebSocket连接"""
        # 这个测试需要先创建一个真实的比赛
        match_id = str(uuid4())  # 实际应该是真实存在的match_id
        uri = f"ws://localhost:8000/ws/matches/{match_id}?token={test_user_token}"
        
        try:
            async with websockets.connect(uri) as websocket:
                # 应该接收到初始状态消息
                initial_message = await websocket.recv()
                message_data = json.loads(initial_message)
                
                assert message_data["type"] == "match_status"
                assert "data" in message_data
                assert "match_id" in message_data["data"]
                assert "status" in message_data["data"]
                
                # 发送心跳消息
                ping_message = {
                    "type": "ping",
                    "timestamp": "2025-01-01T00:00:00Z"
                }
                await websocket.send(json.dumps(ping_message))
                
                # 应该接收到pong回复
                pong_response = await websocket.recv()
                pong_data = json.loads(pong_response)
                
                assert pong_data["type"] == "pong"
                assert pong_data["timestamp"] == ping_message["timestamp"]
                
        except ConnectionClosedError as e:
            # 如果是因为match不存在而关闭连接，这是预期的
            assert e.code == 4004
            assert "Match not found" in str(e)
    
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="需要管理员权限的JWT token")
    async def test_websocket_admin_stats_connection(self, admin_user_token):
        """测试管理员统计WebSocket连接"""
        uri = f"ws://localhost:8000/ws/admin/stats?token={admin_user_token}"
        
        async with websockets.connect(uri) as websocket:
            # 应该接收到初始统计信息
            initial_message = await websocket.recv()
            message_data = json.loads(initial_message)
            
            assert message_data["type"] == "connection_stats"
            assert "data" in message_data
            
            stats_data = message_data["data"]
            assert "total_connections" in stats_data
            assert "users_online" in stats_data
            assert "active_rooms" in stats_data
            
            # 请求最新统计信息
            request_message = {"type": "get_stats"}
            await websocket.send(json.dumps(request_message))
            
            # 应该接收到统计信息回复
            response = await websocket.recv()
            response_data = json.loads(response)
            
            assert response_data["type"] == "connection_stats"
            assert "data" in response_data


class TestWebSocketMessaging:
    """WebSocket消息处理测试"""
    
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="需要完整的环境设置")
    async def test_room_messaging(self, test_user_token):
        """测试房间消息广播"""
        match_id = str(uuid4())
        uri = f"ws://localhost:8000/ws/matches/{match_id}?token={test_user_token}"
        
        # 模拟两个用户连接到同一个房间
        async def user_connection(user_token, user_name):
            user_uri = f"ws://localhost:8000/ws/matches/{match_id}?token={user_token}"
            async with websockets.connect(user_uri) as websocket:
                # 忽略初始状态消息
                await websocket.recv()
                
                return websocket
        
        # 这里需要更复杂的测试设置来模拟多用户场景
        pass


if __name__ == "__main__":
    # 简单的运行脚本，用于开发时快速测试
    asyncio.run(test_websocket_basic_connection())


async def test_websocket_basic_connection():
    """基础WebSocket连接测试（用于开发调试）"""
    match_id = str(uuid4())
    uri = f"ws://localhost:8000/ws/matches/{match_id}"
    
    print(f"测试WebSocket连接到: {uri}")
    
    try:
        async with websockets.connect(uri) as websocket:
            print("连接成功！")
            message = await websocket.recv()
            print(f"接收到消息: {message}")
    except Exception as e:
        print(f"连接失败: {e}")
        print("这是预期的，因为没有提供有效的token")