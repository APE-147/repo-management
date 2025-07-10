#!/usr/bin/env python3
"""
GitHub仓库自动管理系统 - 主控制器
"""
import time
import signal
import sys
import logging
from datetime import datetime
from pathlib import Path

from config import MONITOR_INTERVAL, LOG_FILE, REPO_CATEGORIES
from repo_creator import RepoCreator
from file_monitor import FileMonitor
from index_updater import IndexUpdater
from git_manager import GitManager
from github_detector import GitHubDetector

class RepoManager:
    def __init__(self):
        self.setup_logging()
        self.running = True
        
        # 初始化组件
        self.file_monitor = FileMonitor()
        self.repo_creator = RepoCreator()
        self.index_updater = IndexUpdater()
        self.git_manager = GitManager()
        self.github_detector = GitHubDetector()
        
        # 设置信号处理
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
    def setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(LOG_FILE, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def signal_handler(self, signum, frame):
        """处理退出信号"""
        self.logger.info(f"收到信号 {signum}，准备退出...")
        self.running = False
    
    def process_new_files(self, new_files):
        """处理新增的markdown文件"""
        self.logger.info(f"处理 {len(new_files)} 个新文件")
        
        for file_info in new_files:
            file_name = file_info['name']
            category = file_info['category']
            file_path = file_info['path']
            
            # 获取文件描述
            description = self.file_monitor.get_file_description(file_path)
            
            # 创建GitHub仓库
            self.logger.info(f"为文件 {file_name} 创建仓库 (分类: {category})")
            success = self.repo_creator.create_repository(
                repo_name=file_name,
                description=description,
                category=category
            )
            
            if success:
                self.logger.info(f"成功创建仓库: {file_name}")
            else:
                self.logger.error(f"创建仓库失败: {file_name}")
    
    def process_modified_files(self, modified_files):
        """处理修改的markdown文件"""
        self.logger.info(f"处理 {len(modified_files)} 个修改文件")
        
        # 对于修改的文件，可以考虑更新仓库描述
        for file_info in modified_files:
            file_name = file_info['name']
            file_path = file_info['path']
            
            # 获取新的描述
            new_description = self.file_monitor.get_file_description(file_path)
            self.logger.info(f"文件 {file_name} 已修改，新描述: {new_description}")
            
            # 这里可以添加更新GitHub仓库描述的逻辑
            # 需要使用GitHub API或gh CLI的repo edit命令
    
    def process_deleted_files(self, deleted_files):
        """处理删除的markdown文件"""
        self.logger.info(f"处理 {len(deleted_files)} 个删除文件")
        
        # 对于删除的文件，记录日志但不删除GitHub仓库
        # 因为仓库可能包含有价值的代码和历史记录
        for file_info in deleted_files:
            file_name = file_info['name']
            self.logger.warning(f"markdown文件已删除: {file_name}，但保留GitHub仓库")
    
    def update_indices(self):
        """更新所有README索引"""
        self.logger.info("更新README索引文件...")
        
        # 加载仓库数据
        cache_data = self.repo_creator.load_cache()
        
        # 更新所有分类的README
        success = self.index_updater.update_all_categories(cache_data)
        
        if success:
            self.logger.info("README索引更新成功")
            # 自动提交并推送变更
            self.auto_commit_changes()
        else:
            self.logger.error("README索引更新失败")
        
        return success
    
    def auto_commit_changes(self):
        """自动提交本地变更到git - 同步所有分类仓库"""
        self.logger.info("检查并提交本地变更...")
        
        # 主仓库的变更
        main_success = self.git_manager.auto_commit_and_push("Update repository indices")
        if main_success:
            self.logger.info("主仓库变更已自动提交")
        
        # 分类仓库的变更
        category_success_count = 0
        for category_name, category_path in REPO_CATEGORIES.items():
            if self.git_manager.sync_category_changes(category_name, category_path):
                category_success_count += 1
        
        self.logger.info(f"成功同步 {category_success_count}/{len(REPO_CATEGORIES)} 个分类仓库")
        
        return main_success and category_success_count == len(REPO_CATEGORIES)
    
    def check_github_repositories(self):
        """检查GitHub新仓库并更新索引"""
        self.logger.info("检查GitHub新仓库...")
        
        try:
            # 检测新仓库
            new_repos = self.github_detector.run_detection()
            
            if new_repos:
                self.logger.info(f"检测到 {len(new_repos)} 个新仓库")
                return True
            else:
                self.logger.info("未检测到新仓库")
                return False
                
        except Exception as e:
            self.logger.error(f"检查GitHub仓库时发生错误: {e}")
            return False

    def run_once(self):
        """执行一次完整的监控和处理流程"""
        try:
            # 监控文件变化
            changes = self.file_monitor.monitor_once()
            
            has_changes = False
            
            if changes:
                # 处理新文件
                if changes['new_files']:
                    self.process_new_files(changes['new_files'])
                    has_changes = True
                
                # 处理修改文件
                if changes['modified_files']:
                    self.process_modified_files(changes['modified_files'])
                    has_changes = True
                
                # 处理删除文件
                if changes['deleted_files']:
                    self.process_deleted_files(changes['deleted_files'])
                    has_changes = True
            
            # 检查GitHub新仓库
            github_changes = self.check_github_repositories()
            
            # 如果有任何变化，更新索引
            if has_changes or github_changes:
                self.update_indices()
            
            return True
            
        except Exception as e:
            self.logger.error(f"执行监控流程时发生错误: {e}")
            return False
    
    def run_continuous(self):
        """持续运行监控"""
        self.logger.info("开始持续监控模式...")
        self.logger.info(f"监控间隔: {MONITOR_INTERVAL} 秒")
        
        while self.running:
            try:
                self.run_once()
                
                if self.running:
                    time.sleep(MONITOR_INTERVAL)
                    
            except KeyboardInterrupt:
                self.logger.info("收到中断信号，退出监控...")
                break
            except Exception as e:
                self.logger.error(f"监控过程中发生错误: {e}")
                if self.running:
                    time.sleep(MONITOR_INTERVAL)
        
        self.logger.info("监控已停止")
    
    def initial_scan(self):
        """初始扫描 - 检查现有文件并创建缺失的仓库"""
        self.logger.info("执行初始扫描...")
        
        # 强制检测所有文件
        changes = self.file_monitor.detect_changes()
        
        if changes and changes['new_files']:
            self.logger.info(f"初始扫描发现 {len(changes['new_files'])} 个文件")
            self.process_new_files(changes['new_files'])
            self.update_indices()
        else:
            self.logger.info("初始扫描未发现新文件")
    
    def setup_category_repositories(self):
        """设置所有分类仓库"""
        self.logger.info("开始设置分类仓库...")
        
        # 为每个分类创建GitHub仓库
        from repo_creator import RepoCreator
        creator = RepoCreator()
        
        for category_name, category_path in REPO_CATEGORIES.items():
            repo_name = category_name.capitalize()
            description = f"{category_name} category repository index"
            
            self.logger.info(f"创建GitHub仓库: {repo_name}")
            creator.create_repository(repo_name, description, category_name)
        
        # 设置本地git仓库并推送
        success = self.git_manager.setup_category_repos(REPO_CATEGORIES)
        
        if success:
            self.logger.info("所有分类仓库设置成功")
        else:
            self.logger.warning("部分分类仓库设置失败")
        
        return success

def main():
    """主函数"""
    print("GitHub仓库自动管理系统")
    print("=" * 50)
    
    manager = RepoManager()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "scan":
            # 执行一次扫描
            print("执行一次性扫描...")
            manager.initial_scan()
            manager.run_once()
            
        elif command == "init":
            # 初始化扫描
            print("执行初始化扫描...")
            manager.initial_scan()
            
        elif command == "update":
            # 仅更新索引
            print("更新README索引...")
            manager.update_indices()
            
        elif command == "setup-repos":
            # 设置分类仓库
            print("设置分类仓库...")
            manager.setup_category_repositories()
            
        else:
            print(f"未知命令: {command}")
            print("可用命令: scan, init, update, setup-repos")
            sys.exit(1)
    else:
        # 持续监控模式
        print("启动持续监控模式...")
        print("按 Ctrl+C 退出")
        manager.run_continuous()

if __name__ == "__main__":
    main()