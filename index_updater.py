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
        """生成项目列表HTML"""
        if not repos:
            return f"{README_MARKERS['start']}\n<!-- 暂无项目 -->\n{README_MARKERS['end']}"
        
        html_content = [README_MARKERS['start']]
        html_content.append('<div class="project-list">')
        
        for repo in repos:
            repo_url = f"https://github.com/{GITHUB_USERNAME}/{repo['name']}"
            html_content.append(f'  <div class="project-item">')
            html_content.append(f'    <h3><a href="{repo_url}" target="_blank">{repo["name"]}</a></h3>')
            html_content.append(f'    <p>{repo.get("description", "")}</p>')
            html_content.append(f'    <p><small>创建时间: {repo.get("created_at", "")}</small></p>')
            html_content.append(f'  </div>')
        
        html_content.append('</div>')
        html_content.append(README_MARKERS['end'])
        
        return '\n'.join(html_content)
    
    def update_category_readme(self, category, repos):
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