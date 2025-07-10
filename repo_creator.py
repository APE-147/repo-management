"""
GitHub仓库创建器
"""
import json
import subprocess
import logging
from datetime import datetime
from pathlib import Path
from config import GITHUB_USERNAME, REPO_TEMPLATE, CACHE_FILE

class RepoCreator:
    def __init__(self):
        self.cache_file = CACHE_FILE
        self.setup_logging()
        
    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def load_cache(self):
        """加载仓库缓存"""
        if self.cache_file.exists():
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"repos": [], "last_check": None}
    
    def save_cache(self, cache_data):
        """保存仓库缓存"""
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, indent=2, ensure_ascii=False)
    
    def check_gh_cli(self):
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
    
    def create_repository(self, repo_name, description="", category="Default"):
        """创建GitHub仓库"""
        if not self.check_gh_cli():
            return False
            
        try:
            # 构建gh repo create命令
            cmd = [
                'gh', 'repo', 'create', repo_name,
                '--description', description,
                '--public' if not REPO_TEMPLATE['private'] else '--private'
            ]
            
            if REPO_TEMPLATE['auto_init']:
                cmd.append('--add-readme')
            
            if REPO_TEMPLATE['gitignore_template']:
                cmd.extend(['--gitignore', REPO_TEMPLATE['gitignore_template']])
            
            if REPO_TEMPLATE['license_template']:
                cmd.extend(['--license', REPO_TEMPLATE['license_template']])
            
            # 执行命令
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                self.logger.info(f"成功创建仓库: {repo_name}")
                
                # 更新缓存
                cache = self.load_cache()
                cache["repos"].append({
                    "name": repo_name,
                    "description": description,
                    "category": category,
                    "created_at": datetime.now().isoformat(),
                    "url": f"https://github.com/{GITHUB_USERNAME}/{repo_name}"
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
    
    def scan_markdown_files(self, directory):
        """扫描目录中的markdown文件"""
        markdown_files = []
        for md_file in Path(directory).glob("*.md"):
            if md_file.name.lower() != "readme.md":
                markdown_files.append({
                    "file": md_file,
                    "name": md_file.stem,
                    "path": str(md_file)
                })
        return markdown_files
    
    def get_file_description(self, md_file):
        """从markdown文件中提取描述"""
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
                
                # 查找第一个非空行作为描述
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        return line
                
                # 如果没找到，返回文件名
                return f"Auto-generated repository for {md_file.stem}"
        except Exception:
            return f"Auto-generated repository for {md_file.stem}"

if __name__ == "__main__":
    creator = RepoCreator()
    
    # 测试创建仓库
    creator.create_repository("test-repo", "测试仓库", "Default")