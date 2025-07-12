"""
核心管理类 - 重构后的主要功能模块
"""
import logging
from datetime import datetime
from typing import Dict, Optional, Any
from ..services.config import Config
from .file_monitor import FileMonitor
from .github_detector import GitHubDetector
from .index_updater import IndexUpdater
from .git_manager import GitManager

class RepoManager:
    """仓库管理器主类"""
    
    def __init__(self, config: Optional[Config] = None):
        """初始化仓库管理器"""
        self.config = config or Config()
        self.setup_logging()
        
        # 初始化数据库
        from ..services.database import DatabaseManager
        db_path = self.config.data_dir / "repositories.db"
        self.db_manager = DatabaseManager(db_path)
        
        # 初始化各个组件
        self.file_monitor = FileMonitor(self.config)
        self.github_detector = GitHubDetector(self.config, self.db_manager)
        self.index_updater = IndexUpdater(self.config, self.db_manager)
        self.git_manager = GitManager(self.config)
    
    def setup_logging(self):
        """设置日志"""
        log_level = getattr(logging, self.config.get("log_level", "INFO"))
        
        # 配置日志格式
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # 文件日志
        file_handler = logging.FileHandler(self.config.log_file, encoding='utf-8')
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        
        # 控制台日志
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        
        # 设置根日志器
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(log_level)
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        # 避免重复日志
        self.logger.propagate = False
    
    def initialize(self):
        """初始化系统"""
        self.logger.info("初始化 GitHub Repository Manager...")
        
        # 检查配置
        if not self.config.validate_config():
            self.logger.error("配置无效，运行配置向导...")
            self.config.setup_wizard()
        
        # 初始化数据文件
        self.config.initialize_data_files()
        
        # 检查GitHub CLI
        try:
            import subprocess
            result = subprocess.run(['gh', 'auth', 'status'], capture_output=True, text=True)
            if result.returncode != 0:
                self.logger.error("GitHub CLI未认证，请运行: gh auth login")
                return False
        except FileNotFoundError:
            self.logger.error("GitHub CLI未安装，请先安装 GitHub CLI")
            return False
        
        self.logger.info("初始化完成")
        return True
    
    def scan_once(self):
        """执行一次完整扫描"""
        self.logger.info("开始执行完整扫描...")
        
        # 1. 检测文件变动
        changes = self.file_monitor.monitor_once()
        
        # 2. 检测GitHub上未索引的仓库
        unindexed_repos = self.github_detector.detect_unindexed_repositories()
        
        # 3. 将未索引的仓库添加到Default分类
        if unindexed_repos:
            self.index_updater.add_repositories_to_index(unindexed_repos, "Default")
        
        # 4. 更新所有分类的索引
        self.index_updater.update_all_categories()
        
        # 5. 提交更改
        self.git_manager.commit_changes("Auto-update: scan complete")
        
        self.logger.info("完整扫描完成")
        
        return {
            "file_changes": changes,
            "unindexed_repos": unindexed_repos,
            "timestamp": datetime.now().isoformat()
        }
    
    def update_indices_only(self):
        """仅更新索引"""
        self.logger.info("开始更新索引...")
        
        # 检测未索引的仓库
        unindexed_repos = self.github_detector.detect_unindexed_repositories()
        
        # 将未索引的仓库添加到Default分类
        if unindexed_repos:
            self.index_updater.add_repositories_to_index(unindexed_repos, "Default")
        
        # 更新索引
        self.index_updater.update_all_categories()
        
        # 提交更改
        if unindexed_repos:
            self.git_manager.commit_changes(f"Auto-update: added {len(unindexed_repos)} new repositories to index")
        
        self.logger.info("索引更新完成")
        return unindexed_repos
    
    def monitor_continuous(self):
        """持续监控模式 - 集成README文件监控和GitHub查询"""
        self.logger.info("开始持续监控模式...")
        
        import threading
        import time
        
        # 启动README文件监控线程
        file_monitor_thread = threading.Thread(
            target=self.file_monitor.monitor_readme_files_continuous,
            args=(self.git_manager,),
            daemon=True
        )
        file_monitor_thread.start()
        self.logger.info("README文件监控线程已启动")
        
        # 清理过期缓存
        self.db_manager.clear_expired_cache()
        
        try:
            while True:
                try:
                    result = self.scan_once()
                    
                    # 休眠
                    time.sleep(self.config.monitor_interval)
                    
                except KeyboardInterrupt:
                    self.logger.info("收到中断信号，停止监控")
                    break
                except Exception as e:
                    self.logger.error(f"监控过程中发生错误: {e}")
                    time.sleep(60)  # 出错后等待1分钟再继续
                    
        except Exception as e:
            self.logger.error(f"持续监控模式失败: {e}")
        finally:
            self.logger.info("主监控线程已停止")
    
    def get_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        return {
            "config_dir": str(self.config.config_dir),
            "data_dir": str(self.config.data_dir),
            "github_username": self.config.github_username,
            "monitor_interval": self.config.monitor_interval,
            "file_monitor_interval": self.config.file_monitor_interval,
            "commit_delay": self.config.commit_delay,
            "github_cache_interval": self.config.github_cache_interval,
            "categories": list(self.config.repo_categories.keys()),
            "cache_files": {
                "repo_cache": self.config.repo_cache_file.exists(),
                "github_cache": self.config.github_cache_file.exists(),
                "file_states": self.config.file_states_file.exists()
            }
        }