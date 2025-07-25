"""
索引更新器
"""
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
from ..services.config import Config
from .git_manager import GitManager

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
        """更新特定分类的索引（本地和远程）"""
        # 从数据库获取该分类的仓库
        category_repos = self.db_manager.get_repositories_by_category(category)
        
        # 1. 更新本地repo_index README文件
        readme_path = self.config.repo_categories[category] / "README.md"
        if readme_path.exists():
            self._update_readme_content(readme_path, category_repos)
            self.logger.info(f"已更新本地 {category} 分类索引，包含 {len(category_repos)} 个项目")
        else:
            self.logger.warning(f"{category} 分类的README文件不存在: {readme_path}")
        
        # 2. 更新远程分类仓库
        self._update_remote_category_repo(category, category_repos)
    
    def _update_remote_category_repo(self, category: str, repos: List[Dict[str, Any]]):
        """更新远程分类仓库"""
        try:
            # 创建GitManager实例用于远程仓库操作
            git_manager = GitManager(self.config)
            
            # 克隆或更新远程仓库
            if not git_manager.clone_or_update_category_repo(category):
                self.logger.error(f"无法克隆或更新远程仓库: {category}")
                return
            
            # 生成README内容
            readme_content = self._generate_full_readme_content(category, repos)
            
            # 更新远程仓库的README
            if git_manager.update_category_readme(category, readme_content):
                # 提交并推送变更
                commit_message = f"Auto-update: {len(repos)} repositories indexed"
                if git_manager.commit_and_push_category_repo(category, commit_message):
                    self.logger.info(f"成功更新远程 {category} 仓库")
                else:
                    self.logger.error(f"推送远程 {category} 仓库失败")
            else:
                self.logger.error(f"更新远程 {category} README失败")
                
        except Exception as e:
            self.logger.error(f"更新远程分类仓库失败 {category}: {e}")
    
    def _generate_full_readme_content(self, category: str, repos: List[Dict[str, Any]]) -> str:
        """生成README内容用于远程仓库 - 只提供最小模板，主要用于智能合并"""
        category_descriptions = {
            "Default": "Default projects",
            "Crawler": "Web scraping and crawling projects", 
            "Script": "Automation scripts and tools",
            "Trading": "Trading and financial projects"
        }
        
        description = category_descriptions.get(category, f"{category} projects")
        projects_list = self._generate_projects_list(repos)
        
        # 只生成带有AUTO-GENERATED-CONTENT标记的最小模板
        # 智能合并机制会保留用户的自定义内容
        return f"""# {category} Projects

{description}

## Project List

<!-- 自动生成的项目列表将在此处更新 -->

---

*This file is automatically maintained by the repo-management system.*

<!-- AUTO-GENERATED-CONTENT:START -->
{projects_list}
<!-- AUTO-GENERATED-CONTENT:END -->
"""
    
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