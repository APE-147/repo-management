#!/usr/bin/env python3
"""
README文件监控测试脚本
"""
import time
import threading
from repo_manager.config import Config
from repo_manager.database import DatabaseManager
from repo_manager.core import FileMonitor, GitManager

def test_readme_monitor():
    print("开始测试README文件监控...")
    
    # 初始化配置和组件
    config = Config()
    db_manager = DatabaseManager(config.data_dir / "repositories.db")
    file_monitor = FileMonitor(config)
    git_manager = GitManager(config)
    
    # 启动监控线程（后台运行）
    monitor_thread = threading.Thread(
        target=file_monitor.monitor_readme_files_continuous,
        args=(git_manager,),
        daemon=True
    )
    monitor_thread.start()
    
    print("README文件监控已启动")
    print(f"文件监控间隔: {config.file_monitor_interval}秒")
    print(f"提交延迟: {config.commit_delay}秒")
    print("请在另一个终端中修改README文件，观察自动提交效果")
    print("按 Ctrl+C 停止测试")
    
    try:
        # 主线程保持运行
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n测试已停止")

if __name__ == "__main__":
    test_readme_monitor()