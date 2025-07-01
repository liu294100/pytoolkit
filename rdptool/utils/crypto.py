#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
加密解密工具模块

提供数据加密和解密功能：
- 对称加密（AES）
- 非对称加密（RSA）
- 哈希算法
- 密钥生成和管理
"""

import os
import hashlib
import hmac
import base64
from typing import Tuple, Optional, Union, Dict, Any
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import hashes, serialization, padding
from cryptography.hazmat.primitives.asymmetric import rsa, padding as asym_padding
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidSignature
import secrets
import json
from datetime import datetime, timedelta

class CryptoError(Exception):
    """加密相关异常"""
    pass

class AESCrypto:
    """
    AES加密解密类
    
    支持多种AES模式和密钥长度
    """
    
    def __init__(self, key: bytes, mode: str = 'CBC'):
        """
        初始化AES加密器
        
        Args:
            key: 加密密钥（16、24或32字节）
            mode: 加密模式（CBC、GCM、CTR）
        """
        self.key = key
        self.mode = mode.upper()
        
        # 验证密钥长度
        if len(key) not in [16, 24, 32]:
            raise CryptoError("AES密钥长度必须是16、24或32字节")
    
    def encrypt(self, plaintext: bytes) -> Dict[str, bytes]:
        """
        加密数据
        
        Args:
            plaintext: 明文数据
        
        Returns:
            包含密文和相关参数的字典
        """
        try:
            if self.mode == 'CBC':
                return self._encrypt_cbc(plaintext)
            elif self.mode == 'GCM':
                return self._encrypt_gcm(plaintext)
            elif self.mode == 'CTR':
                return self._encrypt_ctr(plaintext)
            else:
                raise CryptoError(f"不支持的加密模式: {self.mode}")
        except Exception as e:
            raise CryptoError(f"加密失败: {e}")
    
    def decrypt(self, encrypted_data: Dict[str, bytes]) -> bytes:
        """
        解密数据
        
        Args:
            encrypted_data: 加密数据字典
        
        Returns:
            明文数据
        """
        try:
            if self.mode == 'CBC':
                return self._decrypt_cbc(encrypted_data)
            elif self.mode == 'GCM':
                return self._decrypt_gcm(encrypted_data)
            elif self.mode == 'CTR':
                return self._decrypt_ctr(encrypted_data)
            else:
                raise CryptoError(f"不支持的解密模式: {self.mode}")
        except Exception as e:
            raise CryptoError(f"解密失败: {e}")
    
    def _encrypt_cbc(self, plaintext: bytes) -> Dict[str, bytes]:
        """CBC模式加密"""
        # 生成随机IV
        iv = os.urandom(16)
        
        # 填充数据
        padder = padding.PKCS7(128).padder()
        padded_data = padder.update(plaintext) + padder.finalize()
        
        # 加密
        cipher = Cipher(algorithms.AES(self.key), modes.CBC(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(padded_data) + encryptor.finalize()
        
        return {
            'ciphertext': ciphertext,
            'iv': iv,
            'mode': 'CBC'
        }
    
    def _decrypt_cbc(self, encrypted_data: Dict[str, bytes]) -> bytes:
        """CBC模式解密"""
        ciphertext = encrypted_data['ciphertext']
        iv = encrypted_data['iv']
        
        # 解密
        cipher = Cipher(algorithms.AES(self.key), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        padded_plaintext = decryptor.update(ciphertext) + decryptor.finalize()
        
        # 去除填充
        unpadder = padding.PKCS7(128).unpadder()
        plaintext = unpadder.update(padded_plaintext) + unpadder.finalize()
        
        return plaintext
    
    def _encrypt_gcm(self, plaintext: bytes) -> Dict[str, bytes]:
        """GCM模式加密"""
        # 生成随机nonce
        nonce = os.urandom(12)
        
        # 加密
        cipher = Cipher(algorithms.AES(self.key), modes.GCM(nonce), backend=default_backend())
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(plaintext) + encryptor.finalize()
        
        return {
            'ciphertext': ciphertext,
            'nonce': nonce,
            'tag': encryptor.tag,
            'mode': 'GCM'
        }
    
    def _decrypt_gcm(self, encrypted_data: Dict[str, bytes]) -> bytes:
        """GCM模式解密"""
        ciphertext = encrypted_data['ciphertext']
        nonce = encrypted_data['nonce']
        tag = encrypted_data['tag']
        
        # 解密
        cipher = Cipher(algorithms.AES(self.key), modes.GCM(nonce, tag), backend=default_backend())
        decryptor = cipher.decryptor()
        plaintext = decryptor.update(ciphertext) + decryptor.finalize()
        
        return plaintext
    
    def _encrypt_ctr(self, plaintext: bytes) -> Dict[str, bytes]:
        """CTR模式加密"""
        # 生成随机nonce
        nonce = os.urandom(16)
        
        # 加密
        cipher = Cipher(algorithms.AES(self.key), modes.CTR(nonce), backend=default_backend())
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(plaintext) + encryptor.finalize()
        
        return {
            'ciphertext': ciphertext,
            'nonce': nonce,
            'mode': 'CTR'
        }
    
    def _decrypt_ctr(self, encrypted_data: Dict[str, bytes]) -> bytes:
        """CTR模式解密"""
        ciphertext = encrypted_data['ciphertext']
        nonce = encrypted_data['nonce']
        
        # 解密
        cipher = Cipher(algorithms.AES(self.key), modes.CTR(nonce), backend=default_backend())
        decryptor = cipher.decryptor()
        plaintext = decryptor.update(ciphertext) + decryptor.finalize()
        
        return plaintext

class RSACrypto:
    """
    RSA加密解密类
    
    支持RSA非对称加密和数字签名
    """
    
    def __init__(self, key_size: int = 2048):
        """
        初始化RSA加密器
        
        Args:
            key_size: 密钥长度（位）
        """
        self.key_size = key_size
        self.private_key = None
        self.public_key = None
    
    def generate_key_pair(self) -> Tuple[bytes, bytes]:
        """
        生成RSA密钥对
        
        Returns:
            (私钥, 公钥) 的PEM格式字节串
        """
        try:
            # 生成私钥
            self.private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=self.key_size,
                backend=default_backend()
            )
            
            # 获取公钥
            self.public_key = self.private_key.public_key()
            
            # 序列化密钥
            private_pem = self.private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
            
            public_pem = self.public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            
            return private_pem, public_pem
            
        except Exception as e:
            raise CryptoError(f"生成RSA密钥对失败: {e}")
    
    def load_private_key(self, private_key_pem: bytes, password: Optional[bytes] = None):
        """
        加载私钥
        
        Args:
            private_key_pem: PEM格式私钥
            password: 私钥密码
        """
        try:
            self.private_key = serialization.load_pem_private_key(
                private_key_pem,
                password=password,
                backend=default_backend()
            )
            self.public_key = self.private_key.public_key()
        except Exception as e:
            raise CryptoError(f"加载私钥失败: {e}")
    
    def load_public_key(self, public_key_pem: bytes):
        """
        加载公钥
        
        Args:
            public_key_pem: PEM格式公钥
        """
        try:
            self.public_key = serialization.load_pem_public_key(
                public_key_pem,
                backend=default_backend()
            )
        except Exception as e:
            raise CryptoError(f"加载公钥失败: {e}")
    
    def encrypt(self, plaintext: bytes) -> bytes:
        """
        使用公钥加密数据
        
        Args:
            plaintext: 明文数据
        
        Returns:
            密文数据
        """
        if not self.public_key:
            raise CryptoError("未加载公钥")
        
        try:
            ciphertext = self.public_key.encrypt(
                plaintext,
                asym_padding.OAEP(
                    mgf=asym_padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            return ciphertext
        except Exception as e:
            raise CryptoError(f"RSA加密失败: {e}")
    
    def decrypt(self, ciphertext: bytes) -> bytes:
        """
        使用私钥解密数据
        
        Args:
            ciphertext: 密文数据
        
        Returns:
            明文数据
        """
        if not self.private_key:
            raise CryptoError("未加载私钥")
        
        try:
            plaintext = self.private_key.decrypt(
                ciphertext,
                asym_padding.OAEP(
                    mgf=asym_padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            return plaintext
        except Exception as e:
            raise CryptoError(f"RSA解密失败: {e}")
    
    def sign(self, data: bytes) -> bytes:
        """
        使用私钥签名数据
        
        Args:
            data: 要签名的数据
        
        Returns:
            签名
        """
        if not self.private_key:
            raise CryptoError("未加载私钥")
        
        try:
            signature = self.private_key.sign(
                data,
                asym_padding.PSS(
                    mgf=asym_padding.MGF1(hashes.SHA256()),
                    salt_length=asym_padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return signature
        except Exception as e:
            raise CryptoError(f"RSA签名失败: {e}")
    
    def verify(self, data: bytes, signature: bytes) -> bool:
        """
        使用公钥验证签名
        
        Args:
            data: 原始数据
            signature: 签名
        
        Returns:
            验证结果
        """
        if not self.public_key:
            raise CryptoError("未加载公钥")
        
        try:
            self.public_key.verify(
                signature,
                data,
                asym_padding.PSS(
                    mgf=asym_padding.MGF1(hashes.SHA256()),
                    salt_length=asym_padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return True
        except InvalidSignature:
            return False
        except Exception as e:
            raise CryptoError(f"RSA验证失败: {e}")

class HashUtils:
    """
    哈希工具类
    
    提供各种哈希算法
    """
    
    @staticmethod
    def sha256(data: bytes) -> bytes:
        """SHA256哈希"""
        return hashlib.sha256(data).digest()
    
    @staticmethod
    def sha256_hex(data: bytes) -> str:
        """SHA256哈希（十六进制）"""
        return hashlib.sha256(data).hexdigest()
    
    @staticmethod
    def md5(data: bytes) -> bytes:
        """MD5哈希"""
        return hashlib.md5(data).digest()
    
    @staticmethod
    def md5_hex(data: bytes) -> str:
        """MD5哈希（十六进制）"""
        return hashlib.md5(data).hexdigest()
    
    @staticmethod
    def hmac_sha256(key: bytes, data: bytes) -> bytes:
        """HMAC-SHA256"""
        return hmac.new(key, data, hashlib.sha256).digest()
    
    @staticmethod
    def hmac_sha256_hex(key: bytes, data: bytes) -> str:
        """HMAC-SHA256（十六进制）"""
        return hmac.new(key, data, hashlib.sha256).hexdigest()
    
    @staticmethod
    def pbkdf2(password: bytes, salt: bytes, iterations: int = 100000, key_length: int = 32) -> bytes:
        """
        PBKDF2密钥派生
        
        Args:
            password: 密码
            salt: 盐值
            iterations: 迭代次数
            key_length: 密钥长度
        
        Returns:
            派生的密钥
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=key_length,
            salt=salt,
            iterations=iterations,
            backend=default_backend()
        )
        return kdf.derive(password)

class KeyManager:
    """
    密钥管理器
    
    提供密钥生成、存储和管理功能
    """
    
    def __init__(self, key_store_path: Optional[str] = None):
        self.key_store_path = key_store_path
        self.keys: Dict[str, Any] = {}
    
    def generate_aes_key(self, key_size: int = 256) -> bytes:
        """
        生成AES密钥
        
        Args:
            key_size: 密钥长度（位）
        
        Returns:
            AES密钥
        """
        key_bytes = key_size // 8
        return secrets.token_bytes(key_bytes)
    
    def generate_salt(self, length: int = 16) -> bytes:
        """
        生成随机盐值
        
        Args:
            length: 盐值长度
        
        Returns:
            随机盐值
        """
        return secrets.token_bytes(length)
    
    def derive_key_from_password(self, password: str, salt: Optional[bytes] = None) -> Tuple[bytes, bytes]:
        """
        从密码派生密钥
        
        Args:
            password: 密码
            salt: 盐值（如果为None则生成新的）
        
        Returns:
            (密钥, 盐值)
        """
        if salt is None:
            salt = self.generate_salt()
        
        password_bytes = password.encode('utf-8')
        key = HashUtils.pbkdf2(password_bytes, salt)
        
        return key, salt
    
    def store_key(self, key_id: str, key_data: Dict[str, Any]):
        """
        存储密钥
        
        Args:
            key_id: 密钥标识
            key_data: 密钥数据
        """
        self.keys[key_id] = {
            **key_data,
            'created_at': datetime.now().isoformat(),
            'key_id': key_id
        }
    
    def get_key(self, key_id: str) -> Optional[Dict[str, Any]]:
        """
        获取密钥
        
        Args:
            key_id: 密钥标识
        
        Returns:
            密钥数据
        """
        return self.keys.get(key_id)
    
    def delete_key(self, key_id: str) -> bool:
        """
        删除密钥
        
        Args:
            key_id: 密钥标识
        
        Returns:
            是否成功删除
        """
        if key_id in self.keys:
            del self.keys[key_id]
            return True
        return False
    
    def save_key_store(self, password: Optional[str] = None):
        """
        保存密钥库
        
        Args:
            password: 加密密码
        """
        if not self.key_store_path:
            raise CryptoError("未指定密钥库路径")
        
        try:
            # 序列化密钥数据
            key_data = json.dumps(self.keys, default=str).encode('utf-8')
            
            if password:
                # 加密密钥库
                key, salt = self.derive_key_from_password(password)
                aes = AESCrypto(key, 'GCM')
                encrypted_data = aes.encrypt(key_data)
                
                # 保存加密数据
                store_data = {
                    'encrypted': True,
                    'salt': base64.b64encode(salt).decode('ascii'),
                    'data': base64.b64encode(encrypted_data['ciphertext']).decode('ascii'),
                    'nonce': base64.b64encode(encrypted_data['nonce']).decode('ascii'),
                    'tag': base64.b64encode(encrypted_data['tag']).decode('ascii')
                }
            else:
                # 明文保存
                store_data = {
                    'encrypted': False,
                    'data': base64.b64encode(key_data).decode('ascii')
                }
            
            with open(self.key_store_path, 'w', encoding='utf-8') as f:
                json.dump(store_data, f, indent=2)
                
        except Exception as e:
            raise CryptoError(f"保存密钥库失败: {e}")
    
    def load_key_store(self, password: Optional[str] = None):
        """
        加载密钥库
        
        Args:
            password: 解密密码
        """
        if not self.key_store_path or not os.path.exists(self.key_store_path):
            return
        
        try:
            with open(self.key_store_path, 'r', encoding='utf-8') as f:
                store_data = json.load(f)
            
            if store_data.get('encrypted', False):
                if not password:
                    raise CryptoError("密钥库已加密，需要提供密码")
                
                # 解密密钥库
                salt = base64.b64decode(store_data['salt'])
                key, _ = self.derive_key_from_password(password, salt)
                
                aes = AESCrypto(key, 'GCM')
                encrypted_data = {
                    'ciphertext': base64.b64decode(store_data['data']),
                    'nonce': base64.b64decode(store_data['nonce']),
                    'tag': base64.b64decode(store_data['tag'])
                }
                
                key_data = aes.decrypt(encrypted_data)
            else:
                # 明文数据
                key_data = base64.b64decode(store_data['data'])
            
            # 反序列化密钥数据
            self.keys = json.loads(key_data.decode('utf-8'))
            
        except Exception as e:
            raise CryptoError(f"加载密钥库失败: {e}")

# 便捷函数
def encrypt_data(data: bytes, key: bytes, algorithm: str = 'AES', mode: str = 'GCM') -> Dict[str, Any]:
    """
    加密数据
    
    Args:
        data: 要加密的数据
        key: 加密密钥
        algorithm: 加密算法
        mode: 加密模式
    
    Returns:
        加密结果
    """
    if algorithm.upper() == 'AES':
        aes = AESCrypto(key, mode)
        encrypted = aes.encrypt(data)
        # 转换为base64编码
        result = {}
        for k, v in encrypted.items():
            if isinstance(v, bytes):
                result[k] = base64.b64encode(v).decode('ascii')
            else:
                result[k] = v
        return result
    else:
        raise CryptoError(f"不支持的加密算法: {algorithm}")

def decrypt_data(encrypted_data: Dict[str, Any], key: bytes, algorithm: str = 'AES', mode: str = 'GCM') -> bytes:
    """
    解密数据
    
    Args:
        encrypted_data: 加密数据
        key: 解密密钥
        algorithm: 加密算法
        mode: 加密模式
    
    Returns:
        解密后的数据
    """
    if algorithm.upper() == 'AES':
        aes = AESCrypto(key, mode)
        # 转换base64编码
        decoded_data = {}
        for k, v in encrypted_data.items():
            if k in ['ciphertext', 'iv', 'nonce', 'tag'] and isinstance(v, str):
                decoded_data[k] = base64.b64decode(v)
            else:
                decoded_data[k] = v
        return aes.decrypt(decoded_data)
    else:
        raise CryptoError(f"不支持的解密算法: {algorithm}")

def generate_key(algorithm: str = 'AES', key_size: int = 256) -> bytes:
    """
    生成密钥
    
    Args:
        algorithm: 算法类型
        key_size: 密钥长度（位）
    
    Returns:
        生成的密钥
    """
    if algorithm.upper() == 'AES':
        return secrets.token_bytes(key_size // 8)
    else:
        raise CryptoError(f"不支持的算法: {algorithm}")

# 导出功能
__all__ = [
    'CryptoError',
    'AESCrypto',
    'RSACrypto',
    'HashUtils',
    'KeyManager',
    'encrypt_data',
    'decrypt_data',
    'generate_key'
]