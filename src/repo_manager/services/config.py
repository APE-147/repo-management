"""
配置管理模块 - 处理用户配置和数据目录
"""
import os
import json
from pathlib import Path
from typing import Dict, Any, Optional

class Config:
    """配置管理器，负责处理用户配置和数据目录"""
    
    def __init__(self, config_dir: Optional[str] = None):
        """
        初始化配置管理器
        
        Args:
            config_dir: 自定义配置目录路径，如果为None则使用默认路径
        """
        if config_dir:
            self.config_dir = Path(config_dir)
        else:
            # 使用新的数据目录位置
            self.config_dir = Path.home() / "Developer" / "Code" / "Script_data" / "repo_manager"
        
        self.config_file = self.config_dir / "config.json"
        self.data_dir = self.config_dir / "data"
        
        # 设置repo_index目录为项目根目录下的repo_index
        project_root = self.config_dir.parent
        self.repo_index_dir = project_root / "repo_index"
        
        # 创建必要的目录
        self._ensure_directories()
        
        # 加载配置
        self._config = self._load_config()
    
    def _ensure_directories(self):
        """确保所有必要的目录存在"""
        directories = [
            self.config_dir,
            self.data_dir,
            self.repo_index_dir,
            self.repo_index_dir / "Default",
            self.repo_index_dir / "Crawler", 
            self.repo_index_dir / "Script",
            self.repo_index_dir / "Trading"
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                pass
        
        # 返回默认配置
        return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "github_username": os.getenv("GITHUB_USERNAME", ""),
            "monitor_interval": 60,
            "file_monitor_interval": 3,  # 文件监控间隔（秒）
            "commit_delay": 5,  # 检测到变动后延迟提交时间（秒）
            "github_cache_interval": 300,  # GitHub查询缓存间隔（秒，5分钟）
            "repo_template": {
                "private": False,
                "auto_init": True,
                "gitignore_template": "Python",
                "license_template": "mit"
            },
            "categories": {
                "Default": "Default projects",
                "Crawler": "Web scraping and crawling projects",
                "Script": "Automation scripts and tools",
                "Trading": "Trading and financial projects"
            },
            "log_level": "INFO",
            "auto_update_interval": 3600
        }
    
    def save_config(self):
        """保存配置到文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            raise RuntimeError(f"保存配置失败: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        return self._config.get(key, default)
    
    def set(self, key: str, value: Any):
        """设置配置值"""
        self._config[key] = value
    
    def update(self, config_dict: Dict[str, Any]):
        """批量更新配置"""
        self._config.update(config_dict)
    
    @property
    def github_username(self) -> str:
        """获取GitHub用户名"""
        return self.get("github_username", "")
    
    @github_username.setter
    def github_username(self, value: str):
        """设置GitHub用户名"""
        self.set("github_username", value)
    
    @property
    def monitor_interval(self) -> int:
        """获取监控间隔（秒）"""
        return self.get("monitor_interval", 60)
    
    @property
    def file_monitor_interval(self) -> int:
        """获取文件监控间隔（秒）"""
        return self.get("file_monitor_interval", 3)
    
    @property
    def commit_delay(self) -> int:
        """获取提交延迟时间（秒）"""
        return self.get("commit_delay", 5)
    
    @property
    def github_cache_interval(self) -> int:
        """获取GitHub缓存间隔（秒）"""
        return self.get("github_cache_interval", 300)
    
    @property
    def repo_categories(self) -> Dict[str, Path]:
        """获取仓库分类目录映射"""
        categories = self.get("categories", {})
        return {
            name: self.repo_index_dir / name 
            for name in categories.keys()
        }
    
    @property
    def cache_dir(self) -> Path:
        """获取缓存目录"""
        return self.data_dir / "cache"
    
    @property
    def log_dir(self) -> Path:
        """获取日志目录"""
        return self.data_dir / "logs"
    
    @property
    def repo_cache_file(self) -> Path:
        """获取仓库缓存文件路径"""
        self.cache_dir.mkdir(exist_ok=True)
        return self.cache_dir / "repo_cache.json"
    
    @property
    def github_cache_file(self) -> Path:
        """获取GitHub缓存文件路径"""
        self.cache_dir.mkdir(exist_ok=True)
        return self.cache_dir / "github_repos.json"
    
    @property
    def file_states_file(self) -> Path:
        """获取文件状态缓存文件路径"""
        self.cache_dir.mkdir(exist_ok=True)
        return self.cache_dir / "file_states.json"
    
    @property
    def log_file(self) -> Path:
        """获取日志文件路径"""
        self.log_dir.mkdir(exist_ok=True)
        return self.log_dir / "repo_manager.log"
    
    def initialize_data_files(self):
        """初始化数据文件"""
        # 为每个分类创建README.md文件
        for category, description in self.get("categories", {}).items():
            readme_path = self.repo_index_dir / category / "README.md"
            if not readme_path.exists():
                content = f"""# {category} Projects

{description}

## Project List

<!-- 自动生成的项目列表将在此处更新 -->

---

*This file is automatically maintained by the repo-management system.*

<!-- AUTO-GENERATED-CONTENT:START -->
<!-- AUTO-GENERATED-CONTENT:END -->
"""
                readme_path.write_text(content, encoding='utf-8')
        
        # 创建空的缓存文件
        cache_files = [
            self.repo_cache_file,
            self.github_cache_file,
            self.file_states_file
        ]
        
        for cache_file in cache_files:
            if not cache_file.exists():
                cache_file.write_text('{"repos": [], "last_check": null}', encoding='utf-8')
    
    def validate_config(self) -> bool:
        """验证配置是否有效"""
        required_keys = ["github_username"]
        
        for key in required_keys:
            if not self.get(key):
                return False
        
        return True
    
    def setup_wizard(self):
        """配置向导"""
        print("=== GitHub Repository Manager 配置向导 ===\n")
        
        # GitHub用户名
        current_username = self.github_username
        if current_username:
            print(f"当前GitHub用户名: {current_username}")
            if input("是否更改? (y/N): ").lower() != 'y':
                username = current_username
            else:
                username = input("请输入新的GitHub用户名: ").strip()
        else:
            username = input("请输入GitHub用户名: ").strip()
        
        if username:
            self.github_username = username
        
        # 监控间隔
        current_interval = self.monitor_interval
        print(f"\n当前监控间隔: {current_interval}秒")
        if input("是否更改? (y/N): ").lower() == 'y':
            try:
                interval = int(input("请输入监控间隔（秒）: "))
                self.set("monitor_interval", interval)
            except ValueError:
                print("输入无效，使用默认值")
        
        # 保存配置
        self.save_config()
        
        # 初始化数据文件
        self.initialize_data_files()
        
        print(f"\n配置已保存到: {self.config_file}")
        print(f"数据目录: {self.data_dir}")
        print("\n配置完成！")