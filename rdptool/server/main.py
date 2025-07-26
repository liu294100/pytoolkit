#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
远程桌面工具 - Web服务端
基于FastAPI和WebSocket实现客户端间的通信中继
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Dict, Set, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import uvicorn
from loguru import logger

# 配置日志
logger.add("logs/rdp_server.log", rotation="1 day", retention="7 days")

app = FastAPI(title="远程桌面服务端", version="1.0.0")

# 静态文件服务
import os
static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
templates_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")

app.mount("/static", StaticFiles(directory=static_dir), name="static")

# 模板配置
templates = Jinja2Templates(directory=templates_dir)

class ConnectionManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        # 存储所有活跃连接
        self.active_connections: Dict[str, WebSocket] = {}
        # 存储设备信息
        self.devices: Dict[str, dict] = {}
        # 存储控制关系 {controller_id: controlled_id}
        self.control_sessions: Dict[str, str] = {}
        
    async def connect(self, websocket: WebSocket, device_id: str, device_info: dict):
        """新设备连接"""
        self.active_connections[device_id] = websocket
        self.devices[device_id] = {
            **device_info,
            'connected_at': datetime.now().isoformat(),
            'status': 'online'
        }
        logger.info(f"设备 {device_id} 已连接: {device_info.get('name', 'Unknown')}")
        
        # 广播设备列表更新
        await self.broadcast_device_list()
        
    def disconnect(self, device_id: str):
        """设备断开连接"""
        if device_id in self.active_connections:
            del self.active_connections[device_id]
        if device_id in self.devices:
            del self.devices[device_id]
        
        # 清理控制会话
        sessions_to_remove = []
        for controller, controlled in self.control_sessions.items():
            if controller == device_id or controlled == device_id:
                sessions_to_remove.append(controller)
        
        for session in sessions_to_remove:
            del self.control_sessions[session]
            
        logger.info(f"设备 {device_id} 已断开连接")
        
    async def send_personal_message(self, message: dict, device_id: str):
        """发送消息给指定设备"""
        if device_id in self.active_connections:
            try:
                await self.active_connections[device_id].send_text(json.dumps(message))
                return True
            except Exception as e:
                logger.error(f"发送消息给设备 {device_id} 失败: {e}")
                return False
        return False
        
    async def broadcast_device_list(self):
        """广播设备列表给所有连接的设备"""
        device_list = {
            'type': 'device_list',
            'devices': self.devices
        }
        
        disconnected = []
        for device_id, websocket in self.active_connections.items():
            try:
                await websocket.send_text(json.dumps(device_list))
            except Exception as e:
                logger.error(f"广播给设备 {device_id} 失败: {e}")
                disconnected.append(device_id)
        
        # 清理断开的连接
        for device_id in disconnected:
            self.disconnect(device_id)
            
    async def start_control_session(self, controller_id: str, controlled_id: str, password: str = None):
        """开始控制会话"""
        if controlled_id not in self.active_connections:
            return False, "被控设备不在线"
            
        if controller_id in self.control_sessions:
            return False, "您已经在控制其他设备"
            
        # 向被控设备发送控制请求
        control_request = {
            'type': 'control_request',
            'controller_id': controller_id,
            'controller_name': self.devices.get(controller_id, {}).get('name', 'Unknown'),
            'password': password
        }
        
        success = await self.send_personal_message(control_request, controlled_id)
        if success:
            # 暂时记录控制会话（等待被控端确认）
            self.control_sessions[controller_id] = controlled_id
            return True, "控制请求已发送"
        else:
            return False, "发送控制请求失败"
            
    async def handle_control_response(self, controlled_id: str, controller_id: str, accepted: bool):
        """处理控制响应"""
        response = {
            'type': 'control_response',
            'controlled_id': controlled_id,
            'accepted': accepted
        }
        
        if accepted:
            response['message'] = "控制请求已接受，开始远程控制"
            logger.info(f"控制会话建立: {controller_id} -> {controlled_id}")
        else:
            response['message'] = "控制请求被拒绝"
            # 移除控制会话
            if controller_id in self.control_sessions:
                del self.control_sessions[controller_id]
                
        await self.send_personal_message(response, controller_id)
        
    async def relay_message(self, from_device: str, to_device: str, message: dict):
        """中继消息"""
        message['from_device'] = from_device
        return await self.send_personal_message(message, to_device)

manager = ConnectionManager()

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """主页"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/control", response_class=HTMLResponse)
async def control_page(request: Request):
    """控制页面"""
    return templates.TemplateResponse("control.html", {"request": request})

@app.websocket("/ws/{device_id}")
async def websocket_endpoint(websocket: WebSocket, device_id: str):
    """WebSocket连接端点"""
    await websocket.accept()
    
    try:
        # 创建默认设备信息
        device_info = {
            'name': f'Device_{device_id[-8:]}',
            'type': 'controlled' if 'controlled' in device_id else 'controller',
            'status': 'online'
        }
        
        # 注册设备
        await manager.connect(websocket, device_id, device_info)
        
        # 处理消息循环
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # 如果收到设备信息更新，则更新设备信息
                if message.get('type') == 'device_info':
                    manager.devices[device_id].update(message)
                    await manager.broadcast_device_list()
                else:
                    await handle_message(device_id, message)
                
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                logger.error(f"设备 {device_id} 发送了无效的JSON数据")
            except Exception as e:
                logger.error(f"处理设备 {device_id} 消息时出错: {e}")
                
    except Exception as e:
        logger.error(f"WebSocket连接错误: {e}")
    finally:
        manager.disconnect(device_id)
        await manager.broadcast_device_list()

async def handle_message(device_id: str, message: dict):
    """处理收到的消息"""
    msg_type = message.get('type')
    
    if msg_type == 'control_request':
        # 控制请求
        target_id = message.get('target_id')
        password = message.get('password')
        success, msg = await manager.start_control_session(device_id, target_id, password)
        
        response = {
            'type': 'control_request_result',
            'success': success,
            'message': msg
        }
        await manager.send_personal_message(response, device_id)
        
    elif msg_type == 'control_response':
        # 控制响应
        controller_id = message.get('controller_id')
        accepted = message.get('accepted', False)
        await manager.handle_control_response(device_id, controller_id, accepted)
        
    elif msg_type in ['screen_data', 'mouse_event', 'keyboard_event', 'audio_data']:
        # 中继控制数据
        if device_id in manager.control_sessions:
            # 控制端发送给被控端
            target_id = manager.control_sessions[device_id]
            await manager.relay_message(device_id, target_id, message)
        else:
            # 被控端发送给控制端
            for controller_id, controlled_id in manager.control_sessions.items():
                if controlled_id == device_id:
                    await manager.relay_message(device_id, controller_id, message)
                    break
                    
    elif msg_type == 'end_control':
        # 结束控制
        if device_id in manager.control_sessions:
            controlled_id = manager.control_sessions[device_id]
            del manager.control_sessions[device_id]
            
            # 通知被控端
            end_message = {'type': 'control_ended'}
            await manager.send_personal_message(end_message, controlled_id)
            
        # 检查是否是被控端主动结束
        for controller_id, controlled_id in list(manager.control_sessions.items()):
            if controlled_id == device_id:
                del manager.control_sessions[controller_id]
                # 通知控制端
                end_message = {'type': 'control_ended'}
                await manager.send_personal_message(end_message, controller_id)
                break

@app.get("/api/devices")
async def get_devices():
    """获取设备列表API"""
    return {"devices": manager.devices}

@app.get("/api/sessions")
async def get_sessions():
    """获取控制会话列表API"""
    return {"sessions": manager.control_sessions}

if __name__ == "__main__":
    import os
    
    # 创建日志目录
    os.makedirs("logs", exist_ok=True)
    
    logger.info("启动远程桌面服务端...")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )