"""
数据库管理模块 - 使用SQLite存储仓库索引关系
"""
import sqlite3
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.logger = logging.getLogger(f"{__name__}.DatabaseManager")
        self.init_database()
    
    def init_database(self):
        """初始化数据库"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 创建仓库表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS repositories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT,
                    url TEXT,
                    category TEXT NOT NULL,
                    created_at TEXT,
                    is_indexed BOOLEAN DEFAULT 0,
                    added_to_index_at TEXT,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 创建GitHub查询缓存表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS github_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cache_key TEXT UNIQUE NOT NULL,
                    data TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL
                )
            ''')
            
            # 创建索引
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_category ON repositories(category)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_indexed ON repositories(is_indexed)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_name ON repositories(name)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_cache_key ON github_cache(cache_key)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_expires_at ON github_cache(expires_at)')
            
            conn.commit()
            self.logger.info("数据库初始化完成")
    
    def get_connection(self):
        """获取数据库连接"""
        return sqlite3.connect(self.db_path)
    
    def add_repository(self, name: str, description: str, url: str, category: str, 
                      created_at: str, is_indexed: bool = False) -> bool:
        """添加仓库记录"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO repositories 
                    (name, description, url, category, created_at, is_indexed, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (name, description, url, category, created_at, is_indexed, 
                      datetime.now().isoformat()))
                conn.commit()
                self.logger.info(f"添加仓库: {name} ({category})")
                return True
        except Exception as e:
            self.logger.error(f"添加仓库失败 {name}: {e}")
            return False
    
    def get_repositories_by_category(self, category: str) -> List[Dict[str, Any]]:
        """获取指定分类的仓库列表"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT name, description, url, category, created_at, is_indexed, added_to_index_at
                    FROM repositories 
                    WHERE category = ? AND is_indexed = 1
                    ORDER BY added_to_index_at DESC, created_at DESC
                ''', (category,))
                
                repos = []
                for row in cursor.fetchall():
                    repos.append({
                        'name': row[0],
                        'description': row[1],
                        'url': row[2],
                        'category': row[3],
                        'created_at': row[4],
                        'is_indexed': row[5],
                        'added_to_index_at': row[6]
                    })
                return repos
        except Exception as e:
            self.logger.error(f"获取分类仓库失败 {category}: {e}")
            return []
    
    def get_unindexed_repositories(self) -> List[Dict[str, Any]]:
        """获取未索引的仓库列表"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT name, description, url, category, created_at
                    FROM repositories 
                    WHERE is_indexed = 0
                    ORDER BY created_at DESC
                ''')
                
                repos = []
                for row in cursor.fetchall():
                    repos.append({
                        'name': row[0],
                        'description': row[1],
                        'url': row[2],
                        'category': row[3],
                        'created_at': row[4]
                    })
                return repos
        except Exception as e:
            self.logger.error(f"获取未索引仓库失败: {e}")
            return []
    
    def mark_repository_indexed(self, name: str, category: str) -> bool:
        """标记仓库为已索引"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE repositories 
                    SET is_indexed = 1, category = ?, added_to_index_at = ?, updated_at = ?
                    WHERE name = ?
                ''', (category, datetime.now().isoformat(), datetime.now().isoformat(), name))
                conn.commit()
                self.logger.info(f"标记仓库已索引: {name} -> {category}")
                return True
        except Exception as e:
            self.logger.error(f"标记仓库索引失败 {name}: {e}")
            return False
    
    def repository_exists(self, name: str) -> bool:
        """检查仓库是否存在"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT 1 FROM repositories WHERE name = ?', (name,))
                return cursor.fetchone() is not None
        except Exception as e:
            self.logger.error(f"检查仓库存在性失败 {name}: {e}")
            return False
    
    def get_indexed_repository_names(self) -> set:
        """获取所有已索引仓库的名称集合"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT name FROM repositories WHERE is_indexed = 1')
                return {row[0] for row in cursor.fetchall()}
        except Exception as e:
            self.logger.error(f"获取已索引仓库名称失败: {e}")
            return set()
    
    def update_repository_category(self, name: str, category: str) -> bool:
        """更新仓库分类"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE repositories 
                    SET category = ?, updated_at = ?
                    WHERE name = ?
                ''', (category, datetime.now().isoformat(), name))
                conn.commit()
                self.logger.info(f"更新仓库分类: {name} -> {category}")
                return True
        except Exception as e:
            self.logger.error(f"更新仓库分类失败 {name}: {e}")
            return False
    
    def get_all_repositories(self) -> List[Dict[str, Any]]:
        """获取所有仓库"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT name, description, url, category, created_at, is_indexed, added_to_index_at
                    FROM repositories 
                    ORDER BY is_indexed DESC, added_to_index_at DESC, created_at DESC
                ''')
                
                repos = []
                for row in cursor.fetchall():
                    repos.append({
                        'name': row[0],
                        'description': row[1],
                        'url': row[2],
                        'category': row[3],
                        'created_at': row[4],
                        'is_indexed': row[5],
                        'added_to_index_at': row[6]
                    })
                return repos
        except Exception as e:
            self.logger.error(f"获取所有仓库失败: {e}")
            return []
    
    def set_cache(self, cache_key: str, data: str, expires_at: str) -> bool:
        """设置缓存"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO github_cache 
                    (cache_key, data, created_at, expires_at)
                    VALUES (?, ?, ?, ?)
                ''', (cache_key, data, datetime.now().isoformat(), expires_at))
                conn.commit()
                self.logger.debug(f"缓存已设置: {cache_key}")
                return True
        except Exception as e:
            self.logger.error(f"设置缓存失败 {cache_key}: {e}")
            return False
    
    def get_cache(self, cache_key: str) -> Optional[str]:
        """获取缓存（如果未过期）"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT data FROM github_cache 
                    WHERE cache_key = ? AND expires_at > ?
                ''', (cache_key, datetime.now().isoformat()))
                
                result = cursor.fetchone()
                if result:
                    self.logger.debug(f"缓存命中: {cache_key}")
                    return result[0]
                else:
                    self.logger.debug(f"缓存未命中或已过期: {cache_key}")
                    return None
        except Exception as e:
            self.logger.error(f"获取缓存失败 {cache_key}: {e}")
            return None
    
    def clear_expired_cache(self) -> int:
        """清理过期缓存"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    DELETE FROM github_cache 
                    WHERE expires_at <= ?
                ''', (datetime.now().isoformat(),))
                deleted_count = cursor.rowcount
                conn.commit()
                if deleted_count > 0:
                    self.logger.info(f"清理了 {deleted_count} 个过期缓存项")
                return deleted_count
        except Exception as e:
            self.logger.error(f"清理过期缓存失败: {e}")
            return 0