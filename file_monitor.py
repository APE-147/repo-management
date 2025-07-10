"""
文件监控器 - 监控markdown文件变动
"""
import os
import json
import time
import hashlib
from datetime import datetime
from pathlib import Path
from config import REPO_CATEGORIES, CACHE_FILE
import logging

class FileMonitor:
    def __init__(self):
        self.cache_file = CACHE_FILE
        self.setup_logging()
        self.file_states = {}
        
    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def get_file_hash(self, file_path):
        """获取文件的MD5哈希值"""
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
                return hashlib.md5(content).hexdigest()
        except Exception as e:
            self.logger.error(f"获取文件哈希失败: {e}")
            return None
    
    def get_file_info(self, file_path):
        """获取文件信息"""
        try:
            stat = os.stat(file_path)
            return {
                "path": str(file_path),
                "size": stat.st_size,
                "mtime": stat.st_mtime,
                "hash": self.get_file_hash(file_path)
            }
        except Exception as e:
            self.logger.error(f"获取文件信息失败: {e}")
            return None
    
    def load_file_states(self):
        """加载文件状态缓存"""
        cache_file = self.cache_file.parent / "file_states.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"加载文件状态失败: {e}")
        return {}
    
    def save_file_states(self, states):
        """保存文件状态缓存"""
        cache_file = self.cache_file.parent / "file_states.json"
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(states, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"保存文件状态失败: {e}")
    
    def scan_directory(self, directory, category):
        """扫描目录中的markdown文件"""
        markdown_files = []
        directory_path = Path(directory)
        
        if not directory_path.exists():
            self.logger.warning(f"目录不存在: {directory}")
            return markdown_files
        
        for md_file in directory_path.glob("*.md"):
            if md_file.name.lower() != "readme.md":
                file_info = self.get_file_info(md_file)
                if file_info:
                    file_info["category"] = category
                    file_info["name"] = md_file.stem
                    markdown_files.append(file_info)
        
        return markdown_files
    
    def detect_changes(self):
        """检测文件变动"""
        current_states = self.load_file_states()
        new_files = []
        modified_files = []
        deleted_files = []
        
        # 扫描所有分类目录
        current_files = {}
        for category, directory in REPO_CATEGORIES.items():
            files = self.scan_directory(directory, category)
            for file_info in files:
                current_files[file_info["path"]] = file_info
        
        # 检测新文件和修改的文件
        for file_path, file_info in current_files.items():
            if file_path not in current_states:
                # 新文件
                new_files.append(file_info)
                self.logger.info(f"检测到新文件: {file_path}")
            else:
                # 检查是否修改
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
    
    def get_file_description(self, file_path):
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
    
    def monitor_once(self):
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

if __name__ == "__main__":
    monitor = FileMonitor()
    
    # 测试监控
    changes = monitor.monitor_once()
    if changes:
        print("检测到变动:")
        print(json.dumps(changes, indent=2, ensure_ascii=False))