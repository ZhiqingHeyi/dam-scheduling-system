"""
AIWARE 数据库连接管理
"""
import pymysql
from pymysql.cursors import DictCursor
from dataclasses import dataclass
from typing import Optional


@dataclass
class AIWAREDBConfig:
    """AIWARE数据库配置"""
    host: str = "192.168.1.88"
    port: int = 3306
    user: str = "root"
    password: str = "!Tmhc20170717"
    database: str = "aiware"
    charset: str = "utf8mb4"
    
    def to_connection_dict(self) -> dict:
        """转换为连接参数字典"""
        return {
            "host": self.host,
            "port": self.port,
            "user": self.user,
            "password": self.password,
            "database": self.database,
            "charset": self.charset,
            "cursorclass": DictCursor
        }


class AIWAREConnection:
    """AIWARE数据库连接管理器"""
    
    _instance = None
    _config: Optional[AIWAREDBConfig] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def set_config(cls, config: AIWAREDBConfig):
        """设置全局配置"""
        cls._config = config
    
    @classmethod
    def get_connection(cls) -> pymysql.Connection:
        """获取数据库连接"""
        if cls._config is None:
            cls._config = AIWAREDBConfig()
        return pymysql.connect(**cls._config.to_connection_dict())
    
    @classmethod
    def test_connection(cls) -> bool:
        """测试数据库连接"""
        try:
            conn = cls.get_connection()
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            conn.close()
            return True
        except Exception as e:
            print(f"数据库连接测试失败: {e}")
            return False
    
    @classmethod
    def init_database(cls) -> bool:
        """初始化数据库（创建表结构）"""
        try:
            conn = cls.get_connection()
            with conn.cursor() as cursor:
                # 读取并执行SQL脚本
                import os
                sql_file = os.path.join(
                    os.path.dirname(os.path.dirname(__file__)),
                    'sql', 'create_aiware_tables.sql'
                )
                if os.path.exists(sql_file):
                    with open(sql_file, 'r', encoding='utf-8') as f:
                        sql_content = f.read()
                    
                    # 分割并执行每个SQL语句
                    statements = sql_content.split(';')
                    for statement in statements:
                        statement = statement.strip()
                        if statement and not statement.startswith('--'):
                            try:
                                cursor.execute(statement)
                            except Exception as e:
                                print(f"执行SQL失败: {e}")
                                print(f"SQL: {statement[:100]}...")
                    
                    conn.commit()
                    print("数据库初始化成功")
                    return True
                else:
                    print(f"SQL文件不存在: {sql_file}")
                    return False
                    
        except Exception as e:
            print(f"数据库初始化失败: {e}")
            return False
        finally:
            conn.close()


def get_aiware_connection() -> pymysql.Connection:
    """获取AIWARE数据库连接的便捷函数"""
    return AIWAREConnection.get_connection()


def test_aiware_connection() -> bool:
    """测试AIWARE数据库连接的便捷函数"""
    return AIWAREConnection.test_connection()


def init_aiware_database() -> bool:
    """初始化AIWARE数据库的便捷函数"""
    return AIWAREConnection.init_database()
