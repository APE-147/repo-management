#!/usr/bin/env python3
"""
Git管理器 - 处理本地git操作和自动提交
"""
import subprocess
import logging
from pathlib import Path
from datetime import datetime
from config import BASE_DIR, GITHUB_USERNAME

class GitManager:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.base_dir = BASE_DIR
        
    def is_git_repo(self, path=None):
        """检查目录是否为git仓库"""
        check_path = path or self.base_dir
        git_dir = Path(check_path) / '.git'
        return git_dir.exists()
    
    def init_repo(self, path=None):
        """初始化git仓库"""
        work_dir = path or self.base_dir
        try:
            if not self.is_git_repo(work_dir):
                result = subprocess.run(
                    ['git', 'init'],
                    cwd=work_dir,
                    capture_output=True,
                    text=True,
                    check=True
                )
                self.logger.info(f"Git仓库初始化成功: {work_dir}")
                return True
            else:
                self.logger.info(f"Git仓库已存在: {work_dir}")
                return True
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Git仓库初始化失败: {e}")
            return False
    
    def add_files(self, files=None, path=None):
        """添加文件到git暂存区"""
        work_dir = path or self.base_dir
        try:
            if files is None:
                # 添加所有变更
                cmd = ['git', 'add', '.']
            else:
                # 添加指定文件
                cmd = ['git', 'add'] + files
            
            result = subprocess.run(
                cmd,
                cwd=work_dir,
                capture_output=True,
                text=True,
                check=True
            )
            self.logger.info(f"文件已添加到git暂存区: {files or '所有文件'}")
            return True
        except subprocess.CalledProcessError as e:
            self.logger.error(f"添加文件到git失败: {e}")
            return False
    
    def commit(self, message, path=None):
        """提交变更到git"""
        work_dir = path or self.base_dir
        try:
            result = subprocess.run(
                ['git', 'commit', '-m', message],
                cwd=work_dir,
                capture_output=True,
                text=True,
                check=True
            )
            self.logger.info(f"Git提交成功: {message}")
            return True
        except subprocess.CalledProcessError as e:
            if "nothing to commit" in e.stdout or "nothing to commit" in e.stderr:
                self.logger.info("没有需要提交的变更")
                return True
            else:
                self.logger.error(f"Git提交失败: {e}")
                return False
    
    def push(self, path=None):
        """推送到远程仓库"""
        work_dir = path or self.base_dir
        try:
            # 首先检查是否有远程仓库
            result = subprocess.run(
                ['git', 'remote', '-v'],
                cwd=work_dir,
                capture_output=True,
                text=True
            )
            
            if not result.stdout.strip():
                self.logger.warning("没有配置远程仓库，跳过push操作")
                return True
            
            # 推送到远程仓库（推送到master分支）
            result = subprocess.run(
                ['git', 'push', 'origin', 'main:master'],
                cwd=work_dir,
                capture_output=True,
                text=True,
                check=True
            )
            self.logger.info("Git推送成功")
            return True
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Git推送失败: {e}")
            return False
    
    def get_status(self, path=None):
        """获取git状态"""
        work_dir = path or self.base_dir
        try:
            result = subprocess.run(
                ['git', 'status', '--porcelain'],
                cwd=work_dir,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            self.logger.error(f"获取git状态失败: {e}")
            return None
    
    def has_changes(self, path=None):
        """检查是否有未提交的变更"""
        status = self.get_status(path)
        return bool(status)
    
    def auto_commit_and_push(self, message_prefix="Auto-update", path=None):
        """自动提交并推送变更"""
        work_dir = path or self.base_dir
        
        # 检查是否为git仓库，如果不是则初始化
        if not self.is_git_repo(work_dir):
            if not self.init_repo(work_dir):
                return False
        
        # 检查是否有变更
        if not self.has_changes(work_dir):
            self.logger.info("没有检测到变更，跳过提交")
            return True
        
        # 生成提交消息
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        commit_message = f"{message_prefix}: {timestamp}"
        
        # 执行提交流程
        success = True
        success &= self.add_files(path=work_dir)
        success &= self.commit(commit_message, path=work_dir)
        
        if success:
            # 尝试推送到远程仓库
            self.push(path=work_dir)
        
        return success
    
    def setup_remote(self, repo_name, path=None):
        """设置远程仓库"""
        work_dir = path or self.base_dir
        remote_url = f"https://github.com/{GITHUB_USERNAME}/{repo_name}.git"
        
        try:
            # 检查是否已有远程仓库
            result = subprocess.run(
                ['git', 'remote', 'get-url', 'origin'],
                cwd=work_dir,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                self.logger.info(f"远程仓库已存在: {result.stdout.strip()}")
                return True
            
            # 添加远程仓库
            result = subprocess.run(
                ['git', 'remote', 'add', 'origin', remote_url],
                cwd=work_dir,
                capture_output=True,
                text=True,
                check=True
            )
            self.logger.info(f"远程仓库设置成功: {remote_url}")
            return True
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"设置远程仓库失败: {e}")
            return False
    
    def setup_category_repos(self, categories):
        """为所有分类文件夹设置独立的git仓库"""
        success_count = 0
        
        for category_name, category_path in categories.items():
            self.logger.info(f"设置分类仓库: {category_name}")
            
            # 确保目录存在
            if not category_path.exists():
                self.logger.warning(f"分类目录不存在: {category_path}")
                continue
            
            # 初始化git仓库
            if not self.init_repo(category_path):
                self.logger.error(f"初始化git仓库失败: {category_name}")
                continue
            
            # 设置远程仓库（仓库名为首字母大写的分类名）
            repo_name = category_name.capitalize()
            if not self.setup_remote(repo_name, category_path):
                self.logger.error(f"设置远程仓库失败: {category_name}")
                continue
            
            # 执行初始提交和推送
            if self.auto_commit_and_push(f"Initialize {category_name} repository", category_path):
                # 设置main分支并推送
                try:
                    subprocess.run(['git', 'branch', '-M', 'main'], cwd=category_path, check=True)
                    subprocess.run(['git', 'push', '-u', 'origin', 'main'], cwd=category_path, check=True)
                    self.logger.info(f"分类仓库推送成功: {category_name}")
                except subprocess.CalledProcessError as e:
                    self.logger.warning(f"推送失败但仓库已设置: {category_name}")
                success_count += 1
                self.logger.info(f"分类仓库设置成功: {category_name}")
            else:
                self.logger.error(f"初始提交失败: {category_name}")
        
        self.logger.info(f"成功设置 {success_count}/{len(categories)} 个分类仓库")
        return success_count == len(categories)
    
    def sync_category_changes(self, category_name, category_path):
        """同步单个分类的变更"""
        try:
            # 检查是否为git仓库
            if not self.is_git_repo(category_path):
                self.logger.warning(f"分类目录不是git仓库: {category_name}")
                return False
            
            # 检查是否有变更
            if not self.has_changes(category_path):
                return True
            
            # 提交并推送变更
            commit_message = f"Update {category_name} repository content"
            return self.auto_commit_and_push(commit_message, category_path)
            
        except Exception as e:
            self.logger.error(f"同步分类变更失败 {category_name}: {e}")
            return False