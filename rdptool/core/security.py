#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
安全加密模块

提供数据加密和身份验证功能：
- AES/RSA加密
- 数字签名和验证
- 密钥交换和管理
- 身份认证和授权
"""

import os
import json
import time
import hashlib
import secrets
import logging
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass
from enum import Enum

try:
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.primitives import hashes, serialization, padding
    from cryptography.hazmat.primitives.asymmetric import rsa, padding as asym_padding
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.backends import default_backend
    import base64
except ImportError:
    # 如果cryptography不可用，使用基础加密
    try:
        from Crypto.Cipher import AES
        from Crypto.PublicKey import RSA
        from Crypto.Random import get_random_bytes
        from Crypto.Util.Padding import pad, unpad
        import base64
    except ImportError:
        AES = None
        RSA = None

logger = logging.getLogger(__name__)

class EncryptionType(Enum):
    """加密类型"""
    NONE = "none"
    AES_256_CBC = "aes_256_cbc"
    AES_256_GCM = "aes_256_gcm"
    RSA_2048 = "rsa_2048"
    RSA_4096 = "rsa_4096"

class AuthMethod(Enum):
    """认证方法"""
    NONE = "none"
    PASSWORD = "password"
    TOKEN = "token"
    CERTIFICATE = "certificate"
    TWO_FACTOR = "two_factor"

@dataclass
class SecurityConfig:
    """安全配置"""
    encryption_type: EncryptionType = EncryptionType.AES_256_CBC
    auth_method: AuthMethod = AuthMethod.PASSWORD
    key_size: int = 256
    session_timeout: int = 3600  # 1小时
    max_failed_attempts: int = 5
    require_encryption: bool = True
    enable_compression: bool = True

@dataclass
class SessionInfo:
    """会话信息"""
    session_id: str
    user_id: str
    created_time: float
    last_activity: float
    encryption_key: Optional[bytes] = None
    is_authenticated: bool = False
    failed_attempts: int = 0

class SecurityManager:
    """安全管理器"""
    
    def __init__(self, config: SecurityConfig):
        self.config = config
        self.sessions: Dict[str, SessionInfo] = {}
        self.users: Dict[str, Dict[str, Any]] = {}  # 用户数据库
        self.rsa_keys: Optional[Tuple[Any, Any]] = None  # (private_key, public_key)
        
        # 初始化加密
        self._init_encryption()
        
        # 加载用户数据
        self._load_users()
    
    def _init_encryption(self):
        """初始化加密"""
        try:
            if self.config.encryption_type in [EncryptionType.RSA_2048, EncryptionType.RSA_4096]:
                self._generate_rsa_keys()
            
            logger.info(f"加密初始化成功: {self.config.encryption_type.value}")
            
        except Exception as e:
            logger.error(f"加密初始化失败: {e}")
            if self.config.require_encryption:
                raise
    
    def _generate_rsa_keys(self):
        """生成RSA密钥对"""
        try:
            key_size = 2048 if self.config.encryption_type == EncryptionType.RSA_2048 else 4096
            
            if 'cryptography' in globals():
                # 使用cryptography库
                private_key = rsa.generate_private_key(
                    public_exponent=65537,
                    key_size=key_size,
                    backend=default_backend()
                )
                public_key = private_key.public_key()
                self.rsa_keys = (private_key, public_key)
            
            elif RSA:
                # 使用pycryptodome库
                key = RSA.generate(key_size)
                self.rsa_keys = (key, key.publickey())
            
            else:
                logger.error("没有可用的RSA加密库")
                
        except Exception as e:
            logger.error(f"生成RSA密钥失败: {e}")
            raise
    
    def _load_users(self):
        """加载用户数据"""
        # 默认管理员用户
        admin_password = self._hash_password("admin123")
        self.users["admin"] = {
            "password_hash": admin_password,
            "role": "admin",
            "permissions": ["all"],
            "created_time": time.time()
        }
        
        # 默认普通用户
        user_password = self._hash_password("user123")
        self.users["user"] = {
            "password_hash": user_password,
            "role": "user",
            "permissions": ["view", "control"],
            "created_time": time.time()
        }
    
    def _hash_password(self, password: str, salt: Optional[bytes] = None) -> str:
        """哈希密码"""
        if salt is None:
            salt = os.urandom(32)
        
        # 使用PBKDF2进行密码哈希
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        
        key = kdf.derive(password.encode('utf-8'))
        
        # 返回salt+hash的base64编码
        return base64.b64encode(salt + key).decode('ascii')
    
    def _verify_password(self, password: str, password_hash: str) -> bool:
        """验证密码"""
        try:
            # 解码hash
            decoded = base64.b64decode(password_hash.encode('ascii'))
            salt = decoded[:32]
            stored_key = decoded[32:]
            
            # 计算输入密码的hash
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
                backend=default_backend()
            )
            
            key = kdf.derive(password.encode('utf-8'))
            
            # 比较
            return secrets.compare_digest(stored_key, key)
            
        except Exception as e:
            logger.error(f"密码验证失败: {e}")
            return False
    
    def authenticate(self, username: str, password: str, 
                    client_info: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """用户认证"""
        try:
            # 检查用户是否存在
            if username not in self.users:
                logger.warning(f"用户不存在: {username}")
                return None
            
            user_data = self.users[username]
            
            # 验证密码
            if not self._verify_password(password, user_data["password_hash"]):
                logger.warning(f"密码错误: {username}")
                return None
            
            # 创建会话
            session_id = self._generate_session_id()
            current_time = time.time()
            
            session = SessionInfo(
                session_id=session_id,
                user_id=username,
                created_time=current_time,
                last_activity=current_time,
                is_authenticated=True
            )
            
            # 生成会话密钥
            if self.config.encryption_type != EncryptionType.NONE:
                session.encryption_key = self._generate_session_key()
            
            self.sessions[session_id] = session
            
            logger.info(f"用户认证成功: {username}, 会话: {session_id}")
            return session_id
            
        except Exception as e:
            logger.error(f"认证失败: {e}")
            return None
    
    def _generate_session_id(self) -> str:
        """生成会话ID"""
        return secrets.token_urlsafe(32)
    
    def _generate_session_key(self) -> bytes:
        """生成会话密钥"""
        key_length = self.config.key_size // 8  # 转换为字节
        return os.urandom(key_length)
    
    def validate_session(self, session_id: str) -> bool:
        """验证会话"""
        if session_id not in self.sessions:
            return False
        
        session = self.sessions[session_id]
        current_time = time.time()
        
        # 检查会话是否过期
        if current_time - session.created_time > self.config.session_timeout:
            self.logout(session_id)
            return False
        
        # 更新最后活动时间
        session.last_activity = current_time
        return session.is_authenticated
    
    def logout(self, session_id: str):
        """登出"""
        if session_id in self.sessions:
            user_id = self.sessions[session_id].user_id
            del self.sessions[session_id]
            logger.info(f"用户登出: {user_id}, 会话: {session_id}")
    
    def encrypt_data(self, data: bytes, session_id: str) -> Optional[bytes]:
        """加密数据"""
        if self.config.encryption_type == EncryptionType.NONE:
            return data
        
        if session_id not in self.sessions:
            logger.error("无效的会话ID")
            return None
        
        session = self.sessions[session_id]
        if not session.encryption_key:
            logger.error("会话密钥不存在")
            return None
        
        try:
            if self.config.encryption_type == EncryptionType.AES_256_CBC:
                return self._encrypt_aes_cbc(data, session.encryption_key)
            elif self.config.encryption_type == EncryptionType.AES_256_GCM:
                return self._encrypt_aes_gcm(data, session.encryption_key)
            else:
                logger.error(f"不支持的加密类型: {self.config.encryption_type}")
                return None
                
        except Exception as e:
            logger.error(f"数据加密失败: {e}")
            return None
    
    def decrypt_data(self, encrypted_data: bytes, session_id: str) -> Optional[bytes]:
        """解密数据"""
        if self.config.encryption_type == EncryptionType.NONE:
            return encrypted_data
        
        if session_id not in self.sessions:
            logger.error("无效的会话ID")
            return None
        
        session = self.sessions[session_id]
        if not session.encryption_key:
            logger.error("会话密钥不存在")
            return None
        
        try:
            if self.config.encryption_type == EncryptionType.AES_256_CBC:
                return self._decrypt_aes_cbc(encrypted_data, session.encryption_key)
            elif self.config.encryption_type == EncryptionType.AES_256_GCM:
                return self._decrypt_aes_gcm(encrypted_data, session.encryption_key)
            else:
                logger.error(f"不支持的加密类型: {self.config.encryption_type}")
                return None
                
        except Exception as e:
            logger.error(f"数据解密失败: {e}")
            return None
    
    def _encrypt_aes_cbc(self, data: bytes, key: bytes) -> bytes:
        """AES CBC加密"""
        # 生成随机IV
        iv = os.urandom(16)
        
        if 'cryptography' in globals():
            # 使用cryptography库
            cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
            encryptor = cipher.encryptor()
            
            # PKCS7填充
            padder = padding.PKCS7(128).padder()
            padded_data = padder.update(data) + padder.finalize()
            
            encrypted = encryptor.update(padded_data) + encryptor.finalize()
            
        elif AES:
            # 使用pycryptodome库
            cipher = AES.new(key, AES.MODE_CBC, iv)
            encrypted = cipher.encrypt(pad(data, AES.block_size))
        
        else:
            raise RuntimeError("没有可用的AES加密库")
        
        # 返回IV + 加密数据
        return iv + encrypted
    
    def _decrypt_aes_cbc(self, encrypted_data: bytes, key: bytes) -> bytes:
        """AES CBC解密"""
        # 提取IV和加密数据
        iv = encrypted_data[:16]
        ciphertext = encrypted_data[16:]
        
        if 'cryptography' in globals():
            # 使用cryptography库
            cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
            decryptor = cipher.decryptor()
            
            padded_data = decryptor.update(ciphertext) + decryptor.finalize()
            
            # 去除PKCS7填充
            unpadder = padding.PKCS7(128).unpadder()
            data = unpadder.update(padded_data) + unpadder.finalize()
            
        elif AES:
            # 使用pycryptodome库
            cipher = AES.new(key, AES.MODE_CBC, iv)
            data = unpad(cipher.decrypt(ciphertext), AES.block_size)
        
        else:
            raise RuntimeError("没有可用的AES加密库")
        
        return data
    
    def _encrypt_aes_gcm(self, data: bytes, key: bytes) -> bytes:
        """AES GCM加密"""
        # 生成随机nonce
        nonce = os.urandom(12)
        
        if 'cryptography' in globals():
            # 使用cryptography库
            cipher = Cipher(algorithms.AES(key), modes.GCM(nonce), backend=default_backend())
            encryptor = cipher.encryptor()
            
            ciphertext = encryptor.update(data) + encryptor.finalize()
            
            # 返回nonce + tag + 加密数据
            return nonce + encryptor.tag + ciphertext
        
        else:
            raise RuntimeError("AES GCM需要cryptography库")
    
    def _decrypt_aes_gcm(self, encrypted_data: bytes, key: bytes) -> bytes:
        """AES GCM解密"""
        # 提取nonce, tag和加密数据
        nonce = encrypted_data[:12]
        tag = encrypted_data[12:28]
        ciphertext = encrypted_data[28:]
        
        if 'cryptography' in globals():
            # 使用cryptography库
            cipher = Cipher(algorithms.AES(key), modes.GCM(nonce, tag), backend=default_backend())
            decryptor = cipher.decryptor()
            
            data = decryptor.update(ciphertext) + decryptor.finalize()
            return data
        
        else:
            raise RuntimeError("AES GCM需要cryptography库")
    
    def get_public_key(self) -> Optional[str]:
        """获取公钥"""
        if not self.rsa_keys:
            return None
        
        try:
            if 'cryptography' in globals():
                public_key = self.rsa_keys[1]
                pem = public_key.public_key_pem()
                return pem.decode('utf-8')
            elif RSA:
                public_key = self.rsa_keys[1]
                return public_key.export_key().decode('utf-8')
        except Exception as e:
            logger.error(f"获取公钥失败: {e}")
        
        return None
    
    def add_user(self, username: str, password: str, role: str = "user", 
                permissions: List[str] = None) -> bool:
        """添加用户"""
        try:
            if username in self.users:
                logger.warning(f"用户已存在: {username}")
                return False
            
            if permissions is None:
                permissions = ["view", "control"]
            
            password_hash = self._hash_password(password)
            
            self.users[username] = {
                "password_hash": password_hash,
                "role": role,
                "permissions": permissions,
                "created_time": time.time()
            }
            
            logger.info(f"用户添加成功: {username}")
            return True
            
        except Exception as e:
            logger.error(f"添加用户失败: {e}")
            return False
    
    def remove_user(self, username: str) -> bool:
        """删除用户"""
        if username in self.users:
            del self.users[username]
            
            # 删除相关会话
            sessions_to_remove = []
            for session_id, session in self.sessions.items():
                if session.user_id == username:
                    sessions_to_remove.append(session_id)
            
            for session_id in sessions_to_remove:
                del self.sessions[session_id]
            
            logger.info(f"用户删除成功: {username}")
            return True
        
        return False
    
    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取会话信息"""
        if session_id not in self.sessions:
            return None
        
        session = self.sessions[session_id]
        user_data = self.users.get(session.user_id, {})
        
        return {
            'session_id': session.session_id,
            'user_id': session.user_id,
            'role': user_data.get('role', 'unknown'),
            'permissions': user_data.get('permissions', []),
            'created_time': session.created_time,
            'last_activity': session.last_activity,
            'is_authenticated': session.is_authenticated
        }
    
    def cleanup_expired_sessions(self):
        """清理过期会话"""
        current_time = time.time()
        expired_sessions = []
        
        for session_id, session in self.sessions.items():
            if current_time - session.created_time > self.config.session_timeout:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            self.logout(session_id)
        
        if expired_sessions:
            logger.info(f"清理过期会话: {len(expired_sessions)}个")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            'active_sessions': len(self.sessions),
            'total_users': len(self.users),
            'encryption_type': self.config.encryption_type.value,
            'auth_method': self.config.auth_method.value,
            'session_timeout': self.config.session_timeout,
            'require_encryption': self.config.require_encryption
        }

# 工具函数
def create_security_manager(**kwargs) -> SecurityManager:
    """创建安全管理器"""
    config = SecurityConfig(**kwargs)
    return SecurityManager(config)

def generate_random_password(length: int = 12) -> str:
    """生成随机密码"""
    import string
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))