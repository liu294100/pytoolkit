// 远程桌面Web客户端JavaScript

class RemoteDesktopClient {
    constructor() {
        this.websocket = null;
        this.deviceId = this.generateDeviceId();
        this.deviceName = this.getDeviceName();
        this.isConnected = false;
        this.isControlling = false;
        this.controlledDevice = null;
        this.availableDevices = {};
        this.scale = 1.0;
        this.remoteResolution = { width: 1920, height: 1080 };
        
        this.canvas = document.getElementById('remote-screen');
        this.ctx = this.canvas.getContext('2d');
        
        this.init();
    }
    
    generateDeviceId() {
        // 生成基于浏览器的设备ID
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        ctx.textBaseline = 'top';
        ctx.font = '14px Arial';
        ctx.fillText('Browser fingerprint', 2, 2);
        const fingerprint = canvas.toDataURL().slice(-50);
        return `web_${fingerprint.replace(/[^a-zA-Z0-9]/g, '').slice(0, 12)}`;
    }
    
    getDeviceName() {
        const saved = localStorage.getItem('deviceName');
        if (saved) return saved;
        
        const userAgent = navigator.userAgent;
        let deviceName = 'Web浏览器';
        
        if (userAgent.includes('Chrome')) deviceName = 'Chrome浏览器';
        else if (userAgent.includes('Firefox')) deviceName = 'Firefox浏览器';
        else if (userAgent.includes('Safari')) deviceName = 'Safari浏览器';
        else if (userAgent.includes('Edge')) deviceName = 'Edge浏览器';
        
        return deviceName;
    }
    
    init() {
        // 初始化设备名称输入框
        document.getElementById('device-name').value = this.deviceName;
        
        // 绑定事件
        this.bindEvents();
        
        // 自动连接（如果之前连接过）
        const autoConnect = localStorage.getItem('autoConnect');
        if (autoConnect === 'true') {
            setTimeout(() => this.connect(), 1000);
        }
    }
    
    bindEvents() {
        // 画布事件
        this.canvas.addEventListener('mousedown', (e) => this.onMouseDown(e));
        this.canvas.addEventListener('mousemove', (e) => this.onMouseMove(e));
        this.canvas.addEventListener('mouseup', (e) => this.onMouseUp(e));
        this.canvas.addEventListener('wheel', (e) => this.onMouseWheel(e));
        this.canvas.addEventListener('contextmenu', (e) => e.preventDefault());
        this.canvas.addEventListener('dblclick', (e) => this.onDoubleClick(e));
        
        // 键盘事件
        document.addEventListener('keydown', (e) => this.onKeyDown(e));
        document.addEventListener('keyup', (e) => this.onKeyUp(e));
        
        // 设备名称保存
        document.getElementById('device-name').addEventListener('change', (e) => {
            this.deviceName = e.target.value;
            localStorage.setItem('deviceName', this.deviceName);
        });
        
        // 阻止某些默认快捷键
        document.addEventListener('keydown', (e) => {
            if (this.isControlling) {
                // 阻止一些可能干扰的快捷键
                if ((e.ctrlKey && (e.key === 'w' || e.key === 't' || e.key === 'n')) ||
                    (e.altKey && e.key === 'F4') ||
                    e.key === 'F5' || e.key === 'F11' || e.key === 'F12') {
                    e.preventDefault();
                }
            }
        });
    }
    
    connect() {
        if (this.isConnected) {
            this.disconnect();
            return;
        }
        
        const serverUrl = document.getElementById('server-url').value.trim();
        let wsUrl;
        
        if (serverUrl.startsWith('ws://') || serverUrl.startsWith('wss://')) {
            wsUrl = `${serverUrl}/ws/${this.deviceId}`;
        } else {
            const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
            wsUrl = `${protocol}//${serverUrl}/ws/${this.deviceId}`;
        }
        
        this.updateConnectionStatus('连接中...', 'warning');
        
        try {
            this.websocket = new WebSocket(wsUrl);
            
            this.websocket.onopen = () => {
                this.isConnected = true;
                this.updateConnectionStatus('已连接', 'success');
                document.getElementById('connect-btn').innerHTML = '<i class="bi bi-plug-fill"></i> 断开';
                
                // 发送设备信息
                this.sendMessage({
                    type: 'device_info',
                    name: this.deviceName,
                    device_type: 'controller',
                    os: navigator.platform,
                    browser: this.getBrowserInfo()
                });
                
                localStorage.setItem('autoConnect', 'true');
            };
            
            this.websocket.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.handleMessage(data);
                } catch (e) {
                    console.error('解析消息失败:', e);
                }
            };
            
            this.websocket.onclose = () => {
                this.isConnected = false;
                this.isControlling = false;
                this.updateConnectionStatus('未连接', 'secondary');
                document.getElementById('connect-btn').innerHTML = '<i class="bi bi-plug"></i> 连接';
                this.clearDeviceList();
                this.hideRemoteScreen();
            };
            
            this.websocket.onerror = (error) => {
                console.error('WebSocket错误:', error);
                this.updateConnectionStatus('连接错误', 'danger');
            };
            
        } catch (error) {
            console.error('连接失败:', error);
            this.updateConnectionStatus('连接失败', 'danger');
        }
    }
    
    disconnect() {
        if (this.websocket) {
            this.websocket.close();
            this.websocket = null;
        }
        localStorage.setItem('autoConnect', 'false');
    }
    
    sendMessage(message) {
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
            this.websocket.send(JSON.stringify(message));
        }
    }
    
    handleMessage(data) {
        const msgType = data.type;
        
        switch (msgType) {
            case 'device_list':
                this.updateDeviceList(data.devices);
                break;
                
            case 'control_request_result':
                this.handleControlRequestResult(data.success, data.message);
                break;
                
            case 'control_response':
                this.handleControlResponse(data.accepted, data.message);
                break;
                
            case 'screen_data':
                this.updateRemoteScreen(data);
                break;
                
            case 'control_ended':
                this.handleControlEnded();
                break;
                
            default:
                console.log('未知消息类型:', msgType);
        }
    }
    
    updateConnectionStatus(text, type) {
        const statusElement = document.getElementById('connection-status');
        statusElement.textContent = text;
        statusElement.className = `badge bg-${type}`;
    }
    
    updateDeviceList(devices) {
        this.availableDevices = devices;
        const deviceList = document.getElementById('device-list');
        deviceList.innerHTML = '';
        
        const controlledDevices = Object.entries(devices).filter(
            ([id, info]) => info.device_type === 'controlled'
        );
        
        if (controlledDevices.length === 0) {
            deviceList.innerHTML = `
                <div class="list-group-item text-center text-muted py-4">
                    <i class="bi bi-devices fs-1"></i>
                    <p class="mt-2 mb-0">暂无可用设备</p>
                </div>
            `;
            return;
        }
        
        controlledDevices.forEach(([deviceId, deviceInfo]) => {
            const deviceItem = document.createElement('div');
            deviceItem.className = 'list-group-item list-group-item-action';
            deviceItem.style.cursor = 'pointer';
            
            const statusIcon = deviceInfo.status === 'online' ? 
                '<i class="bi bi-circle-fill text-success"></i>' : 
                '<i class="bi bi-circle-fill text-secondary"></i>';
            
            deviceItem.innerHTML = `
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <h6 class="mb-1">${deviceInfo.name}</h6>
                        <small class="text-muted">${deviceInfo.os || 'Unknown OS'}</small>
                    </div>
                    <div class="text-end">
                        ${statusIcon}
                        <small class="d-block text-muted">${deviceInfo.status}</small>
                    </div>
                </div>
            `;
            
            deviceItem.addEventListener('click', () => {
                if (!this.isControlling && deviceInfo.status === 'online') {
                    this.requestControl(deviceId, deviceInfo.name);
                }
            });
            
            deviceList.appendChild(deviceItem);
        });
    }
    
    clearDeviceList() {
        const deviceList = document.getElementById('device-list');
        deviceList.innerHTML = `
            <div class="list-group-item text-center text-muted py-4">
                <i class="bi bi-wifi-off fs-1"></i>
                <p class="mt-2 mb-0">请先连接服务器</p>
            </div>
        `;
    }
    
    requestControl(deviceId, deviceName) {
        document.getElementById('target-device-name').textContent = deviceName;
        const modal = new bootstrap.Modal(document.getElementById('control-request-modal'));
        modal.show();
        
        // 保存目标设备信息
        this.targetDevice = { id: deviceId, name: deviceName };
    }
    
    sendControlRequest() {
        const password = document.getElementById('control-password').value;
        
        this.sendMessage({
            type: 'control_request',
            target_id: this.targetDevice.id,
            password: password || null
        });
        
        // 关闭模态框
        const modal = bootstrap.Modal.getInstance(document.getElementById('control-request-modal'));
        modal.hide();
        
        // 清空密码
        document.getElementById('control-password').value = '';
    }
    
    handleControlRequestResult(success, message) {
        if (success) {
            this.showNotification(message, 'info');
        } else {
            this.showNotification(message, 'error');
        }
    }
    
    handleControlResponse(accepted, message) {
        if (accepted) {
            this.isControlling = true;
            this.controlledDevice = this.targetDevice;
            this.showRemoteScreen();
            this.showNotification('控制请求已接受，开始远程控制', 'success');
            
            // 更新UI
            document.getElementById('controlled-device-name').textContent = `- ${this.controlledDevice.name}`;
            document.getElementById('end-control-btn').style.display = 'inline-block';
            document.getElementById('shortcut-toggle').style.display = 'block';
        } else {
            this.showNotification('控制请求被拒绝', 'error');
        }
    }
    
    updateRemoteScreen(data) {
        if (!this.isControlling) return;
        
        const img = new Image();
        img.onload = () => {
            // 更新远程分辨率信息
            this.remoteResolution = {
                width: data.original_width,
                height: data.original_height
            };
            
            // 设置画布大小
            const scaledWidth = data.width * this.scale;
            const scaledHeight = data.height * this.scale;
            
            this.canvas.width = scaledWidth;
            this.canvas.height = scaledHeight;
            
            // 绘制图像
            this.ctx.drawImage(img, 0, 0, scaledWidth, scaledHeight);
        };
        
        img.src = `data:image/jpeg;base64,${data.data}`;
    }
    
    showRemoteScreen() {
        document.getElementById('remote-screen-container').style.display = 'none';
        this.canvas.style.display = 'block';
    }
    
    hideRemoteScreen() {
        document.getElementById('remote-screen-container').style.display = 'flex';
        this.canvas.style.display = 'none';
        document.getElementById('controlled-device-name').textContent = '';
        document.getElementById('end-control-btn').style.display = 'none';
        document.getElementById('shortcut-toggle').style.display = 'none';
        document.getElementById('shortcut-panel').style.display = 'none';
    }
    
    handleControlEnded() {
        this.isControlling = false;
        this.controlledDevice = null;
        this.hideRemoteScreen();
        this.showNotification('远程控制已结束', 'info');
    }
    
    endControl() {
        if (this.isControlling) {
            this.sendMessage({ type: 'end_control' });
        }
    }
    
    // 鼠标事件处理
    onMouseDown(event) {
        if (!this.isControlling) return;
        
        const coords = this.getRemoteCoords(event);
        const button = event.button === 0 ? 'left' : (event.button === 2 ? 'right' : 'middle');
        
        this.sendMessage({
            type: 'mouse_event',
            event_type: 'click',
            x: coords.x,
            y: coords.y,
            button: button
        });
        
        event.preventDefault();
    }
    
    onMouseMove(event) {
        if (!this.isControlling) return;
        
        const coords = this.getRemoteCoords(event);
        
        this.sendMessage({
            type: 'mouse_event',
            event_type: 'move',
            x: coords.x,
            y: coords.y
        });
    }
    
    onMouseUp(event) {
        // 鼠标抬起事件（如果需要）
    }
    
    onMouseWheel(event) {
        if (!this.isControlling) return;
        
        const coords = this.getRemoteCoords(event);
        const scrollY = event.deltaY > 0 ? -1 : 1;
        
        this.sendMessage({
            type: 'mouse_event',
            event_type: 'scroll',
            x: coords.x,
            y: coords.y,
            scroll_y: scrollY
        });
        
        event.preventDefault();
    }
    
    onDoubleClick(event) {
        if (!this.isControlling) return;
        
        const coords = this.getRemoteCoords(event);
        
        this.sendMessage({
            type: 'mouse_event',
            event_type: 'double_click',
            x: coords.x,
            y: coords.y,
            button: 'left'
        });
        
        event.preventDefault();
    }
    
    getRemoteCoords(event) {
        const rect = this.canvas.getBoundingClientRect();
        const canvasX = event.clientX - rect.left;
        const canvasY = event.clientY - rect.top;
        
        // 转换为远程坐标
        const remoteX = Math.round(canvasX / this.scale);
        const remoteY = Math.round(canvasY / this.scale);
        
        return { x: remoteX, y: remoteY };
    }
    
    // 键盘事件处理
    onKeyDown(event) {
        if (!this.isControlling) return;
        
        // 转换键名
        const key = this.convertKeyName(event.key, event.code);
        
        this.sendMessage({
            type: 'keyboard_event',
            event_type: 'press',
            key: key
        });
        
        // 阻止某些默认行为
        if (this.shouldPreventDefault(event)) {
            event.preventDefault();
        }
    }
    
    onKeyUp(event) {
        // 键盘抬起事件（如果需要）
    }
    
    convertKeyName(key, code) {
        // 转换特殊键名
        const keyMap = {
            ' ': 'space',
            'Enter': 'enter',
            'Backspace': 'backspace',
            'Tab': 'tab',
            'Escape': 'esc',
            'ArrowUp': 'up',
            'ArrowDown': 'down',
            'ArrowLeft': 'left',
            'ArrowRight': 'right',
            'Control': 'ctrl',
            'Alt': 'alt',
            'Shift': 'shift',
            'Meta': 'win'
        };
        
        return keyMap[key] || key.toLowerCase();
    }
    
    shouldPreventDefault(event) {
        // 需要阻止默认行为的键
        const preventKeys = [
            'Tab', 'F1', 'F2', 'F3', 'F4', 'F5', 'F6', 'F7', 'F8', 'F9', 'F10', 'F11', 'F12'
        ];
        
        return preventKeys.includes(event.key) || 
               (event.ctrlKey && ['w', 't', 'n', 'r'].includes(event.key));
    }
    
    sendKeyCombo(keys) {
        if (!this.isControlling) return;
        
        this.sendMessage({
            type: 'keyboard_event',
            event_type: 'press',
            key: keys
        });
    }
    
    // 缩放控制
    setScale(scale) {
        this.scale = scale;
        // 重新绘制当前屏幕（如果有的话）
        if (this.isControlling && this.canvas.width > 0) {
            // 触发重绘
            this.canvas.style.transform = `scale(${scale})`;
            this.canvas.style.transformOrigin = 'top left';
        }
    }
    
    fitToWindow() {
        if (!this.isControlling) return;
        
        const container = document.querySelector('.card-body');
        const containerWidth = container.clientWidth;
        const containerHeight = container.clientHeight;
        
        const scaleX = containerWidth / this.remoteResolution.width;
        const scaleY = containerHeight / this.remoteResolution.height;
        const scale = Math.min(scaleX, scaleY, 1.0); // 不放大，只缩小
        
        this.setScale(scale);
    }
    
    // 工具方法
    getBrowserInfo() {
        const userAgent = navigator.userAgent;
        if (userAgent.includes('Chrome')) return 'Chrome';
        if (userAgent.includes('Firefox')) return 'Firefox';
        if (userAgent.includes('Safari')) return 'Safari';
        if (userAgent.includes('Edge')) return 'Edge';
        return 'Unknown';
    }
    
    showNotification(message, type) {
        // 简单的通知实现
        const alertClass = {
            'success': 'alert-success',
            'error': 'alert-danger',
            'info': 'alert-info',
            'warning': 'alert-warning'
        }[type] || 'alert-info';
        
        const notification = document.createElement('div');
        notification.className = `alert ${alertClass} alert-dismissible fade show position-fixed`;
        notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
        notification.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(notification);
        
        // 自动移除
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 5000);
    }
}

// 全局实例
let rdpClient;

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    rdpClient = new RemoteDesktopClient();
});

// 全局函数（供HTML调用）
function toggleConnection() {
    rdpClient.connect();
}

function refreshDevices() {
    // 设备列表会自动刷新
    rdpClient.showNotification('正在刷新设备列表...', 'info');
}

function sendControlRequest() {
    rdpClient.sendControlRequest();
}

function endControl() {
    rdpClient.endControl();
}

function setScale(scale) {
    rdpClient.setScale(scale);
}

function fitToWindow() {
    rdpClient.fitToWindow();
}

function sendKeyCombo(keys) {
    rdpClient.sendKeyCombo(keys);
}

function toggleShortcutPanel() {
    const panel = document.getElementById('shortcut-panel');
    panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
}