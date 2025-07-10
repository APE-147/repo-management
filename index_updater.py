"""
索引更新器 - 自动更新README文件中的项目链接
"""
import re
import json
from datetime import datetime
from pathlib import Path
from config import REPO_CATEGORIES, README_MARKERS, GITHUB_USERNAME
import logging

class IndexUpdater:
    def __init__(self):
        self.setup_logging()
        
    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def read_readme(self, readme_path):
        """读取README文件内容"""
        try:
            with open(readme_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            self.logger.error(f"读取README文件失败: {e}")
            return None
    
    def write_readme(self, readme_path, content):
        """写入README文件内容"""
        try:
            with open(readme_path, 'w', encoding='utf-8') as f:
                f.write(content)
            self.logger.info(f"更新README文件: {readme_path}")
            return True
        except Exception as e:
            self.logger.error(f"写入README文件失败: {e}")
            return False
    
    def generate_project_list(self, category, repos):
        """生成项目列表Markdown"""
        if not repos:
            return f"{README_MARKERS['start']}\n<!-- 暂无项目 -->\n{README_MARKERS['end']}"
        
        # 按创建时间排序，最新的在前
        sorted_repos = sorted(repos, key=lambda x: x.get('created_at', ''), reverse=True)
        
        content = [README_MARKERS['start']]
        
        for repo in sorted_repos:
            repo_url = f"https://github.com/{GITHUB_USERNAME}/{repo['name']}"
            description = repo.get("description", "")
            created_at = repo.get("created_at", "")
            
            # 使用简单的bullet list格式
            content.append(f"- **[{repo['name']}]({repo_url})** - {description}")
            if created_at:
                content.append(f"  - 创建时间: {created_at}")
        
        content.append(README_MARKERS['end'])
        
        return '\n'.join(content)
    
    def generate_default_comprehensive_list(self, all_repos_by_category):
        """为Default目录生成综合项目列表"""
        if not any(repos for repos in all_repos_by_category.values()):
            return f"{README_MARKERS['start']}\n<!-- 暂无项目 -->\n{README_MARKERS['end']}"
        
        content = [README_MARKERS['start']]
        
        # 收集所有仓库并按创建时间排序（最新的在前）
        all_repos = []
        for category, repos in all_repos_by_category.items():
            for repo in repos:
                repo_with_category = repo.copy()
                repo_with_category['category'] = category
                all_repos.append(repo_with_category)
        
        # 按创建时间排序，最新的在前
        sorted_repos = sorted(all_repos, key=lambda x: x.get('created_at', ''), reverse=True)
        
        # 按分类分组显示
        categories_shown = set()
        for category in ["Crawler", "Script", "Trading", "Default"]:
            category_repos = [repo for repo in sorted_repos if repo.get('category') == category]
            if category_repos:
                if category == "Default":
                    content.append(f"\n## Other Projects")
                else:
                    content.append(f"\n## {category} Projects")
                
                for repo in category_repos:
                    repo_url = f"https://github.com/{GITHUB_USERNAME}/{repo['name']}"
                    description = repo.get("description", "")
                    created_at = repo.get("created_at", "")
                    
                    content.append(f"- **[{repo['name']}]({repo_url})** - {description}")
                    if created_at:
                        content.append(f"  - 创建时间: {created_at}")
                
                categories_shown.add(category)
        
        content.append(README_MARKERS['end'])
        
        return '\n'.join(content)
    
    def update_category_readme(self, category, repos, all_repos_by_category=None):
        """更新特定分类的README文件"""
        if category not in REPO_CATEGORIES:
            self.logger.error(f"未知的分类: {category}")
            return False
        
        readme_path = REPO_CATEGORIES[category] / "README.md"
        
        if not readme_path.exists():
            self.logger.error(f"README文件不存在: {readme_path}")
            return False
        
        # 读取现有内容
        content = self.read_readme(readme_path)
        if content is None:
            return False
        
        # 生成新的项目列表
        if category == "Default" and all_repos_by_category:
            # 为Default目录生成综合索引
            new_project_list = self.generate_default_comprehensive_list(all_repos_by_category)
        else:
            # 为其他分类生成常规列表
            new_project_list = self.generate_project_list(category, repos)
        
        # 查找并替换自动生成的内容
        start_marker = README_MARKERS['start']
        end_marker = README_MARKERS['end']
        
        # 使用正则表达式查找和替换
        pattern = f"{re.escape(start_marker)}.*?{re.escape(end_marker)}"
        
        if re.search(pattern, content, re.DOTALL):
            # 替换现有内容
            new_content = re.sub(pattern, new_project_list, content, flags=re.DOTALL)
        else:
            # 如果没有找到标记，在文件末尾添加
            new_content = content + "\n\n" + new_project_list
        
        # 写回文件
        return self.write_readme(readme_path, new_content)
    
    def update_all_categories(self, repo_data):
        """更新所有分类的README文件"""
        # 按分类整理仓库数据
        categorized_repos = {}
        for category in REPO_CATEGORIES.keys():
            categorized_repos[category] = []
        
        # 分类仓库
        for repo in repo_data.get("repos", []):
            category = repo.get("category", "Default")
            if category in categorized_repos:
                categorized_repos[category].append(repo)
            else:
                categorized_repos["Default"].append(repo)
        
        # 更新每个分类的README
        success_count = 0
        for category, repos in categorized_repos.items():
            if category == "Default":
                # 为Default分类传递完整的分类数据
                if self.update_category_readme(category, repos, categorized_repos):
                    success_count += 1
                else:
                    self.logger.error(f"更新分类 {category} 失败")
            else:
                if self.update_category_readme(category, repos):
                    success_count += 1
                else:
                    self.logger.error(f"更新分类 {category} 失败")
        
        self.logger.info(f"成功更新 {success_count} 个分类的README文件")
        return success_count == len(REPO_CATEGORIES)

if __name__ == "__main__":
    updater = IndexUpdater()
    
    # 测试数据
    test_data = {
        "repos": [
            {
                "name": "test-repo-1",
                "description": "测试仓库1",
                "category": "Default",
                "created_at": "2024-07-10T10:00:00"
            }
        ]
    }
    
    updater.update_all_categories(test_data)