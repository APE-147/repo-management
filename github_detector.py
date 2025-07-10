"""
GitHub仓库检测器 - 检测GitHub上的新仓库并更新索引
"""
import json
import subprocess
import logging
from datetime import datetime
from pathlib import Path
from config import GITHUB_USERNAME, CACHE_FILE

class GitHubDetector:
    def __init__(self):
        self.cache_file = CACHE_FILE
        self.github_cache_file = Path("github_repos.json")
        self.setup_logging()
        
    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def check_gh_cli(self):
        """检查GitHub CLI是否可用"""
        try:
            result = subprocess.run(['gh', 'auth', 'status'], 
                                  capture_output=True, text=True)
            return result.returncode == 0
        except FileNotFoundError:
            self.logger.error("GitHub CLI未安装或不可用")
            return False
    
    def get_github_repositories(self):
        """获取GitHub上的所有仓库列表"""
        if not self.check_gh_cli():
            return []
        
        try:
            # 使用gh CLI获取仓库列表
            cmd = ['gh', 'repo', 'list', GITHUB_USERNAME, '--json', 'name,description,createdAt,url,isPrivate']
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                repos = json.loads(result.stdout)
                self.logger.info(f"从GitHub获取到 {len(repos)} 个仓库")
                return repos
            else:
                self.logger.error(f"获取GitHub仓库列表失败: {result.stderr}")
                return []
                
        except Exception as e:
            self.logger.error(f"获取GitHub仓库时发生错误: {e}")
            return []
    
    def load_github_cache(self):
        """加载GitHub仓库缓存"""
        if self.github_cache_file.exists():
            try:
                with open(self.github_cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"加载GitHub缓存失败: {e}")
        
        return {"repos": [], "last_check": None}
    
    def save_github_cache(self, cache_data):
        """保存GitHub仓库缓存"""
        try:
            with open(self.github_cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
            self.logger.info("GitHub缓存已更新")
        except Exception as e:
            self.logger.error(f"保存GitHub缓存失败: {e}")
    
    def detect_new_repositories(self):
        """检测GitHub上的新仓库"""
        # 获取当前GitHub仓库列表
        current_repos = self.get_github_repositories()
        if not current_repos:
            return []
        
        # 加载缓存的仓库列表
        cache_data = self.load_github_cache()
        cached_repos = cache_data.get("repos", [])
        
        # 创建缓存仓库名称集合用于比较
        cached_repo_names = {repo["name"] for repo in cached_repos}
        
        # 找出新仓库
        new_repos = []
        for repo in current_repos:
            if repo["name"] not in cached_repo_names:
                # 转换仓库信息格式以匹配现有系统
                repo_info = {
                    "name": repo["name"],
                    "description": repo.get("description", ""),
                    "created_at": repo["createdAt"],
                    "url": repo["url"],
                    "category": "Default",  # 所有新项目默认添加到Default分类
                    "source": "github_detected"
                }
                new_repos.append(repo_info)
                self.logger.info(f"检测到新仓库: {repo['name']}")
        
        if new_repos:
            # 更新缓存
            cache_data["repos"] = current_repos
            cache_data["last_check"] = datetime.now().isoformat()
            self.save_github_cache(cache_data)
            
            self.logger.info(f"检测到 {len(new_repos)} 个新仓库")
        else:
            self.logger.info("未检测到新仓库")
        
        return new_repos
    
    def guess_category(self, repo_name, description):
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
    
    def update_local_cache_with_new_repos(self, new_repos):
        """将新检测到的仓库添加到本地缓存"""
        if not new_repos:
            return
        
        try:
            # 加载本地仓库缓存
            if self.cache_file.exists():
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    local_cache = json.load(f)
            else:
                local_cache = {"repos": [], "last_check": None}
            
            # 创建现有仓库名称集合
            existing_names = {repo["name"] for repo in local_cache.get("repos", [])}
            
            # 添加新仓库到本地缓存
            for repo in new_repos:
                if repo["name"] not in existing_names:
                    local_cache["repos"].append(repo)
                    self.logger.info(f"添加新仓库到本地缓存: {repo['name']}")
            
            # 更新时间戳
            local_cache["last_check"] = datetime.now().isoformat()
            
            # 保存本地缓存
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(local_cache, f, indent=2, ensure_ascii=False)
            
            self.logger.info("本地缓存已更新")
            
        except Exception as e:
            self.logger.error(f"更新本地缓存失败: {e}")
    
    def run_detection(self):
        """执行一次完整的检测流程"""
        self.logger.info("开始检测GitHub新仓库...")
        
        # 检测新仓库
        new_repos = self.detect_new_repositories()
        
        if new_repos:
            # 更新本地缓存
            self.update_local_cache_with_new_repos(new_repos)
            
            self.logger.info(f"检测完成，发现 {len(new_repos)} 个新仓库")
            return new_repos
        else:
            self.logger.info("检测完成，未发现新仓库")
            return []

if __name__ == "__main__":
    detector = GitHubDetector()
    new_repos = detector.run_detection()
    if new_repos:
        print("检测到的新仓库:")
        for repo in new_repos:
            print(f"- {repo['name']} ({repo['category']}): {repo['description']}")