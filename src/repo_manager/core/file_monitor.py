"""
文件监控器
"""
import json
import logging
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from ..services.config import Config

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
    
    def monitor_readme_files_continuous(self, git_manager):
        """持续监控README.md文件变动，检测到变动后延迟提交"""
        import time
        from pathlib import Path
        
        self.logger.info(f"开始持续监控README.md文件 (间隔: {self.config.file_monitor_interval}秒)")
        
        # 记录README文件状态
        readme_states = {}
        
        def get_readme_files_state():
            """获取所有README.md文件的状态"""
            states = {}
            for category in self.config.repo_categories:
                readme_path = self.config.repo_index_dir / category / "README.md"
                if readme_path.exists():
                    states[str(readme_path)] = {
                        "mtime": readme_path.stat().st_mtime,
                        "size": readme_path.stat().st_size
                    }
            return states
        
        # 初始化状态
        readme_states = get_readme_files_state()
        pending_commit = False
        commit_timer = None
        
        try:
            while True:
                current_states = get_readme_files_state()
                
                # 检测是否有变动
                changes_detected = False
                for file_path, current_state in current_states.items():
                    if file_path not in readme_states or readme_states[file_path] != current_state:
                        self.logger.info(f"检测到README文件变动: {file_path}")
                        changes_detected = True
                        break
                
                # 检测删除的文件
                for file_path in readme_states:
                    if file_path not in current_states:
                        self.logger.info(f"检测到README文件删除: {file_path}")
                        changes_detected = True
                        break
                
                if changes_detected:
                    readme_states = current_states
                    pending_commit = True
                    commit_timer = time.time() + self.config.commit_delay
                    self.logger.info(f"将在 {self.config.commit_delay} 秒后自动提交")
                
                # 检查是否需要提交
                if pending_commit and commit_timer and time.time() >= commit_timer:
                    self.logger.info("执行延迟提交...")
                    try:
                        if git_manager.commit_changes("Auto-update: README files modified"):
                            self.logger.info("README文件变动已自动提交")
                        else:
                            self.logger.info("没有需要提交的变更")
                    except Exception as e:
                        self.logger.error(f"自动提交失败: {e}")
                    
                    pending_commit = False
                    commit_timer = None
                
                time.sleep(self.config.file_monitor_interval)
                
        except KeyboardInterrupt:
            self.logger.info("README文件监控已停止")
        except Exception as e:
            self.logger.error(f"README文件监控出错: {e}")