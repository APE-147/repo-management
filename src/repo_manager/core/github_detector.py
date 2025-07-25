"""
GitHub仓库检测器 - 专注于检测未索引的仓库
"""
import json
import logging
import subprocess
from datetime import datetime, timedelta
from typing import Dict, List, Any
from ..services.config import Config

class GitHubDetector:
    """GitHub仓库检测器 - 专注于检测未索引的仓库"""
    
    def __init__(self, config: Config, db_manager):
        self.config = config
        self.db_manager = db_manager
        self.logger = logging.getLogger(f"{__name__}.GitHubDetector")
    
    def get_github_repositories(self) -> List[Dict[str, Any]]:
        """获取GitHub上的所有仓库列表（带缓存）"""
        from datetime import datetime, timedelta
        
        cache_key = f"github_repos_{self.config.github_username}"
        
        # 先尝试从缓存获取
        cached_data = self.db_manager.get_cache(cache_key)
        if cached_data:
            try:
                repos = json.loads(cached_data)
                self.logger.info(f"从缓存获取到 {len(repos)} 个仓库")
                return repos
            except json.JSONDecodeError:
                self.logger.warning("缓存数据格式错误，重新从GitHub获取")
        
        # 缓存不存在或已过期，从GitHub获取
        try:
            cmd = ['gh', 'repo', 'list', self.config.github_username, 
                   '--json', 'name,description,createdAt,url,isPrivate']
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                repos = json.loads(result.stdout)
                self.logger.info(f"从GitHub获取到 {len(repos)} 个仓库")
                
                # 保存到缓存
                expires_at = (datetime.now() + timedelta(seconds=self.config.github_cache_interval)).isoformat()
                self.db_manager.set_cache(cache_key, result.stdout, expires_at)
                
                return repos
            else:
                self.logger.error(f"获取GitHub仓库列表失败: {result.stderr}")
                return []
                
        except Exception as e:
            self.logger.error(f"获取GitHub仓库时发生错误: {e}")
            return []
    
    def detect_unindexed_repositories(self) -> List[Dict[str, Any]]:
        """检测未索引的仓库"""
        current_repos = self.get_github_repositories()
        if not current_repos:
            return []
        
        # 获取当前已索引的仓库名称
        indexed_repo_names = self.get_indexed_repository_names_from_readmes()
        
        # 找出未索引的仓库
        unindexed_repos = []
        for repo in current_repos:
            repo_name = repo["name"]
            
            # 跳过索引仓库本身
            if repo_name in ["Default", "Crawler", "Script", "Trading"]:
                continue
                
            # 如果仓库未在任何README中索引，则添加到未索引列表
            if repo_name not in indexed_repo_names:
                repo_info = {
                    "name": repo_name,
                    "description": repo.get("description", ""),
                    "created_at": repo["createdAt"],
                    "url": repo["url"],
                    "category": self.guess_category(repo_name, repo.get("description", "")),
                    "source": "github_detected"
                }
                unindexed_repos.append(repo_info)
                self.logger.info(f"检测到未索引仓库: {repo_name}")
        
        # 将未索引的仓库添加到数据库
        for repo in unindexed_repos:
            self.db_manager.add_repository(
                name=repo["name"],
                description=repo["description"],
                url=repo["url"],
                category=repo["category"],
                created_at=repo["created_at"],
                is_indexed=False
            )
        
        if unindexed_repos:
            self.logger.info(f"检测到 {len(unindexed_repos)} 个未索引仓库")
        
        return unindexed_repos
    
    def get_indexed_repository_names_from_readmes(self) -> set:
        """从所有README文件中提取已索引的仓库名称"""
        indexed_repos = set()
        
        for category, directory in self.config.repo_categories.items():
            readme_path = directory / "README.md"
            if readme_path.exists():
                try:
                    content = readme_path.read_text(encoding='utf-8')
                    # 使用正则表达式提取GitHub仓库链接
                    import re
                    # 匹配形式如: [repo-name](https://github.com/username/repo-name)
                    pattern = r'\[([^\]]+)\]\(https://github\.com/[^/]+/([^)]+)\)'
                    matches = re.findall(pattern, content)
                    
                    for match in matches:
                        # match[1] 是仓库名称
                        repo_name = match[1]
                        indexed_repos.add(repo_name)
                        self.logger.debug(f"从 {category} README中发现已索引仓库: {repo_name}")
                        
                except Exception as e:
                    self.logger.error(f"读取README文件失败 {readme_path}: {e}")
        
        self.logger.info(f"从 README文件中找到 {len(indexed_repos)} 个已索引仓库")
        return indexed_repos
    
    def guess_category(self, repo_name: str, description: str) -> str:
        """根据仓库名称和描述猜测分类"""
        name_lower = repo_name.lower()
        desc_lower = description.lower()
        
        # 根据关键字判断分类
        if any(keyword in name_lower or keyword in desc_lower 
               for keyword in ["trade", "trading", "crypto", "finance", "market", "stock"]):
            return "Trading"
        elif any(keyword in name_lower or keyword in desc_lower 
                 for keyword in ["script", "automation", "tool", "utility", "auto"]):
            return "Script"
        elif any(keyword in name_lower or keyword in desc_lower 
                 for keyword in ["crawler", "scrape", "spider", "crawl", "scraping"]):
            return "Crawler"
        else:
            return "Default"