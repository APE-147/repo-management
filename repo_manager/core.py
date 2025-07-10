"""
核心管理类 - 重构后的主要功能模块
"""
import json
import logging
import hashlib
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from .config import Config

class RepoManager:
    """仓库管理器主类"""
    
    def __init__(self, config: Optional[Config] = None):
        """初始化仓库管理器"""
        self.config = config or Config()
        self.setup_logging()
        
        # 初始化数据库
        from .database import DatabaseManager
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
        """持续监控模式"""
        self.logger.info("开始持续监控模式...")
        
        import time
        
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
    
    def get_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        return {
            "config_dir": str(self.config.config_dir),
            "data_dir": str(self.config.data_dir),
            "github_username": self.config.github_username,
            "monitor_interval": self.config.monitor_interval,
            "categories": list(self.config.repo_categories.keys()),
            "cache_files": {
                "repo_cache": self.config.repo_cache_file.exists(),
                "github_cache": self.config.github_cache_file.exists(),
                "file_states": self.config.file_states_file.exists()
            }
        }


class FileMonitor:
    """文件监控器"""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.FileMonitor")
    
    def get_file_hash(self, file_path: Path) -> Optional[str]:
        """获取文件的MD5哈希值"""
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
                return hashlib.md5(content).hexdigest()
        except Exception as e:
            self.logger.error(f"获取文件哈希失败 {file_path}: {e}")
            return None
    
    def get_file_info(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """获取文件信息"""
        try:
            stat = file_path.stat()
            return {
                "path": str(file_path),
                "size": stat.st_size,
                "mtime": stat.st_mtime,
                "hash": self.get_file_hash(file_path)
            }
        except Exception as e:
            self.logger.error(f"获取文件信息失败 {file_path}: {e}")
            return None
    
    def load_file_states(self) -> Dict[str, Any]:
        """加载文件状态缓存"""
        if self.config.file_states_file.exists():
            try:
                with open(self.config.file_states_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"加载文件状态失败: {e}")
        return {}
    
    def save_file_states(self, states: Dict[str, Any]):
        """保存文件状态缓存"""
        try:
            with open(self.config.file_states_file, 'w', encoding='utf-8') as f:
                json.dump(states, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"保存文件状态失败: {e}")
    
    def scan_directory(self, directory: Path, category: str) -> List[Dict[str, Any]]:
        """扫描目录中的markdown文件"""
        markdown_files = []
        
        if not directory.exists():
            self.logger.warning(f"目录不存在: {directory}")
            return markdown_files
        
        for md_file in directory.glob("*.md"):
            if md_file.name.lower() != "readme.md":
                file_info = self.get_file_info(md_file)
                if file_info:
                    file_info["category"] = category
                    file_info["name"] = md_file.stem
                    markdown_files.append(file_info)
        
        return markdown_files
    
    def detect_changes(self) -> Dict[str, Any]:
        """检测文件变动"""
        current_states = self.load_file_states()
        new_files = []
        modified_files = []
        deleted_files = []
        
        # 扫描所有分类目录
        current_files = {}
        for category, directory in self.config.repo_categories.items():
            files = self.scan_directory(directory, category)
            for file_info in files:
                current_files[file_info["path"]] = file_info
        
        # 检测新文件和修改的文件
        for file_path, file_info in current_files.items():
            if file_path not in current_states:
                new_files.append(file_info)
                self.logger.info(f"检测到新文件: {file_path}")
            else:
                old_info = current_states[file_path]
                if (file_info["hash"] != old_info.get("hash") or 
                    file_info["mtime"] != old_info.get("mtime")):
                    modified_files.append(file_info)
                    self.logger.info(f"检测到文件修改: {file_path}")
        
        # 检测删除的文件
        for file_path in current_states:
            if file_path not in current_files:
                deleted_files.append(current_states[file_path])
                self.logger.info(f"检测到文件删除: {file_path}")
        
        # 保存当前状态
        self.save_file_states(current_files)
        
        return {
            "new_files": new_files,
            "modified_files": modified_files,
            "deleted_files": deleted_files,
            "timestamp": datetime.now().isoformat()
        }
    
    def get_file_description(self, file_path: str) -> str:
        """从markdown文件中提取描述"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
                
                # 查找第一个标题或非空行作为描述
                for line in lines:
                    line = line.strip()
                    if line.startswith('# '):
                        return line[2:].strip()
                    elif line.startswith('## '):
                        return line[3:].strip()
                    elif line and not line.startswith('#') and len(line) > 10:
                        return line[:100] + "..." if len(line) > 100 else line
                
                # 如果没找到合适的描述，返回默认描述
                file_name = Path(file_path).stem
                return f"Auto-generated repository for {file_name}"
        except Exception as e:
            self.logger.error(f"提取文件描述失败: {e}")
            file_name = Path(file_path).stem
            return f"Auto-generated repository for {file_name}"
    
    def monitor_once(self) -> Optional[Dict[str, Any]]:
        """执行一次监控检查"""
        self.logger.info("开始文件监控检查...")
        changes = self.detect_changes()
        
        if changes["new_files"] or changes["modified_files"] or changes["deleted_files"]:
            self.logger.info(f"检测到变动: 新增{len(changes['new_files'])}个, "
                           f"修改{len(changes['modified_files'])}个, "
                           f"删除{len(changes['deleted_files'])}个文件")
            return changes
        else:
            self.logger.info("未检测到文件变动")
            return None


class RepoCreator:
    """仓库创建器 - 已废弃，项目不再自动创建仓库，只管理现有仓库的索引
    保留此类以保持兼容性，但不在新的流程中使用
    """
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.RepoCreator")
    
    def check_gh_cli(self) -> bool:
        """检查GitHub CLI是否已安装和认证"""
        try:
            result = subprocess.run(['gh', 'auth', 'status'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                self.logger.info("GitHub CLI已认证")
                return True
            else:
                self.logger.error("GitHub CLI未认证，请运行: gh auth login")
                return False
        except FileNotFoundError:
            self.logger.error("GitHub CLI未安装，请安装: brew install gh")
            return False
    
    def load_cache(self) -> Dict[str, Any]:
        """加载仓库缓存"""
        if self.config.repo_cache_file.exists():
            try:
                with open(self.config.repo_cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"加载缓存失败: {e}")
        return {"repos": [], "last_check": None}
    
    def save_cache(self, cache_data: Dict[str, Any]):
        """保存仓库缓存"""
        try:
            with open(self.config.repo_cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"保存缓存失败: {e}")
    
    def create_repository(self, repo_name: str, description: str = "", category: str = "Default") -> bool:
        """创建GitHub仓库"""
        if not self.check_gh_cli():
            return False
        
        try:
            repo_template = self.config.get("repo_template", {})
            
            # 构建gh repo create命令
            cmd = [
                'gh', 'repo', 'create', repo_name,
                '--description', description,
                '--public' if not repo_template.get('private', False) else '--private'
            ]
            
            if repo_template.get('auto_init', True):
                cmd.append('--add-readme')
            
            if repo_template.get('gitignore_template'):
                cmd.extend(['--gitignore', repo_template['gitignore_template']])
            
            if repo_template.get('license_template'):
                cmd.extend(['--license', repo_template['license_template']])
            
            # 执行命令
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                self.logger.info(f"成功创建仓库: {repo_name}")
                
                # 更新缓存
                cache = self.load_cache()
                existing_names = {repo["name"] for repo in cache["repos"]}
                
                if repo_name not in existing_names:
                    cache["repos"].append({
                        "name": repo_name,
                        "description": description,
                        "category": category,
                        "created_at": datetime.now().isoformat(),
                        "url": f"https://github.com/{self.config.github_username}/{repo_name}"
                    })
                    cache["last_check"] = datetime.now().isoformat()
                    self.save_cache(cache)
                
                return True
            else:
                self.logger.error(f"创建仓库失败: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"创建仓库时发生错误: {e}")
            return False


class GitHubDetector:
    """GitHub仓库检测器 - 专注于检测未索引的仓库"""
    
    def __init__(self, config: Config, db_manager):
        self.config = config
        self.db_manager = db_manager
        self.logger = logging.getLogger(f"{__name__}.GitHubDetector")
    
    def get_github_repositories(self) -> List[Dict[str, Any]]:
        """获取GitHub上的所有仓库列表"""
        try:
            cmd = ['gh', 'repo', 'list', self.config.github_username, 
                   '--json', 'name,description,createdAt,url,isPrivate']
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


class IndexUpdater:
    """索引更新器"""
    
    def __init__(self, config: Config, db_manager):
        self.config = config
        self.db_manager = db_manager
        self.logger = logging.getLogger(f"{__name__}.IndexUpdater")
    
    def add_repositories_to_index(self, repositories: List[Dict[str, Any]], target_category: str = "Default"):
        """将仓库添加到指定分类的索引中"""
        if not repositories:
            return
            
        for repo in repositories:
            # 在数据库中标记为已索引
            self.db_manager.mark_repository_indexed(repo["name"], target_category)
            self.logger.info(f"将仓库 {repo['name']} 添加到 {target_category} 索引")
        
        # 更新对应分类的README文件
        self.update_category_index(target_category)
    
    def update_all_categories(self):
        """更新所有分类的索引"""
        for category in self.config.repo_categories.keys():
            self.update_category_index(category)
    
    def update_category_index(self, category: str):
        """更新特定分类的索引"""
        # 从数据库获取该分类的仓库
        category_repos = self.db_manager.get_repositories_by_category(category)
        
        # 更新README文件
        readme_path = self.config.repo_categories[category] / "README.md"
        if readme_path.exists():
            self._update_readme_content(readme_path, category_repos)
            self.logger.info(f"已更新 {category} 分类索引，包含 {len(category_repos)} 个项目")
        else:
            self.logger.warning(f"{category} 分类的README文件不存在: {readme_path}")
    
    def _update_readme_content(self, readme_path: Path, repos: List[Dict[str, Any]]):
        """更新README文件的内容"""
        try:
            # 读取现有内容
            content = readme_path.read_text(encoding='utf-8')
            
            # 生成项目列表
            projects_list = self._generate_projects_list(repos)
            
            # 查找并替换自动生成的内容区域
            start_marker = "<!-- AUTO-GENERATED-CONTENT:START -->"
            end_marker = "<!-- AUTO-GENERATED-CONTENT:END -->"
            
            start_idx = content.find(start_marker)
            end_idx = content.find(end_marker)
            
            if start_idx != -1 and end_idx != -1:
                # 替换内容
                new_content = (
                    content[:start_idx + len(start_marker)] + 
                    "\n" + projects_list + "\n" +
                    content[end_idx:]
                )
                
                # 写回文件
                readme_path.write_text(new_content, encoding='utf-8')
            else:
                self.logger.warning(f"README文件中未找到自动生成内容标记: {readme_path}")
                
        except Exception as e:
            self.logger.error(f"更新README内容失败 {readme_path}: {e}")
    
    def _generate_projects_list(self, repos: List[Dict[str, Any]]) -> str:
        """生成项目列表（bullet list格式）"""
        if not repos:
            return "<!-- 暂无项目 -->"
        
        lines = []
        for repo in repos:
            name = repo.get("name", "Unknown")
            description = repo.get("description", "")
            url = repo.get("url", "")
            created_at = repo.get("created_at", "")
            
            # 格式化创建时间
            if created_at:
                try:
                    if "T" in created_at:
                        dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                        created_at = dt.strftime("%Y-%m-%d")
                except:
                    pass
            
            # 使用bullet list格式
            if description:
                lines.append(f"- **[{name}]({url})** - {description}")
            else:
                lines.append(f"- **[{name}]({url})**")
            
            if created_at:
                lines.append(f"  - 创建时间: {created_at}")
        
        return "\n".join(lines)


class GitManager:
    """Git管理器"""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.GitManager")
    
    def commit_changes(self, message: str):
        """提交更改"""
        try:
            # 获取项目根目录
            project_root = self.config.config_dir.parent
            
            # 检查是否有变更
            result = subprocess.run(
                ['git', 'status', '--porcelain'], 
                cwd=project_root,
                capture_output=True, 
                text=True
            )
            
            if result.returncode == 0 and result.stdout.strip():
                # 有变更，进行提交
                # 添加所有变更
                subprocess.run(['git', 'add', '.'], cwd=project_root, check=True)
                
                # 提交变更
                subprocess.run(['git', 'commit', '-m', message], cwd=project_root, check=True)
                
                self.logger.info(f"Git提交完成: {message}")
            else:
                self.logger.info("没有需要提交的变更")
                
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Git操作失败: {e}")
        except Exception as e:
            self.logger.error(f"提交更改失败: {e}")