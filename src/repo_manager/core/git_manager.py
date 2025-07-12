"""
Git管理器 - 支持多仓库管理
"""
import logging
import subprocess
from pathlib import Path
from ..services.config import Config

class GitManager:
    """Git管理器 - 支持多仓库管理"""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.GitManager")
        # 远程分类仓库的本地克隆目录
        self.category_repos_dir = self.config.config_dir.parent / "category_repos"
        self.category_repos_dir.mkdir(exist_ok=True)
    
    def clone_or_update_category_repo(self, category: str) -> bool:
        """克隆或更新分类仓库"""
        try:
            repo_url = f"https://github.com/{self.config.github_username}/{category}.git"
            local_path = self.category_repos_dir / category
            
            if local_path.exists():
                # 仓库已存在，确保在默认分支并执行pull
                self.logger.info(f"更新分类仓库: {category}")
                
                # 获取默认分支名称
                default_branch_result = subprocess.run(
                    ['git', 'symbolic-ref', 'refs/remotes/origin/HEAD'], 
                    cwd=local_path, capture_output=True, text=True
                )
                
                if default_branch_result.returncode == 0:
                    default_branch = default_branch_result.stdout.strip().split('/')[-1]
                else:
                    # 如果无法获取默认分支，尝试常见分支名
                    default_branch = 'main'
                    check_main = subprocess.run(
                        ['git', 'rev-parse', '--verify', 'origin/main'], 
                        cwd=local_path, capture_output=True, text=True
                    )
                    if check_main.returncode != 0:
                        default_branch = 'master'
                
                # 切换到默认分支
                subprocess.run(['git', 'checkout', default_branch], cwd=local_path, capture_output=True)
                
                # 拉取最新代码
                result = subprocess.run(['git', 'pull', 'origin', default_branch], 
                                      cwd=local_path, capture_output=True, text=True)
                if result.returncode != 0:
                    self.logger.warning(f"Pull失败: {result.stderr}")
                    return False
            else:
                # 克隆仓库
                self.logger.info(f"克隆分类仓库: {category} from {repo_url}")
                result = subprocess.run(['git', 'clone', repo_url, str(local_path)], 
                                     capture_output=True, text=True)
                if result.returncode != 0:
                    self.logger.error(f"克隆失败: {result.stderr}")
                    return False
            
            return True
        except Exception as e:
            self.logger.error(f"克隆或更新分类仓库失败 {category}: {e}")
            return False
    
    def update_category_readme(self, category: str, content: str) -> bool:
        """更新分类仓库的README.md文件 - 智能合并，只更新自动生成的内容"""
        try:
            local_path = self.category_repos_dir / category
            readme_path = local_path / "README.md"
            
            if not local_path.exists():
                self.logger.error(f"分类仓库目录不存在: {local_path}")
                return False
            
            # 智能合并内容：保留用户编辑，只更新自动生成部分
            merged_content = self._merge_readme_content(readme_path, content)
            
            # 写入合并后的内容
            with open(readme_path, 'w', encoding='utf-8') as f:
                f.write(merged_content)
            
            self.logger.info(f"已更新分类README: {category}")
            return True
        except Exception as e:
            self.logger.error(f"更新分类README失败 {category}: {e}")
            return False
    
    def _merge_readme_content(self, readme_path: Path, new_content: str) -> str:
        """合并README内容：保留用户编辑，只更新AUTO-GENERATED-CONTENT部分"""
        try:
            # 读取现有内容
            if readme_path.exists():
                with open(readme_path, 'r', encoding='utf-8') as f:
                    existing_content = f.read()
            else:
                existing_content = ""
            
            # 从新内容中提取自动生成的部分
            auto_start = "<!-- AUTO-GENERATED-CONTENT:START -->"
            auto_end = "<!-- AUTO-GENERATED-CONTENT:END -->"
            
            # 从新内容中提取自动生成的部分
            new_start_idx = new_content.find(auto_start)
            new_end_idx = new_content.find(auto_end)
            
            if new_start_idx == -1 or new_end_idx == -1:
                # 如果新内容没有标记，直接返回新内容
                return new_content
            
            new_auto_content = new_content[new_start_idx:new_end_idx + len(auto_end)]
            
            # 在现有内容中查找并替换自动生成的部分
            if existing_content:
                existing_start_idx = existing_content.find(auto_start)
                existing_end_idx = existing_content.find(auto_end)
                
                if existing_start_idx != -1 and existing_end_idx != -1:
                    # 保留用户编辑的部分，只替换自动生成的部分
                    before_auto = existing_content[:existing_start_idx]
                    after_auto = existing_content[existing_end_idx + len(auto_end):]
                    merged_content = before_auto + new_auto_content + after_auto
                    return merged_content
            
            # 如果现有内容没有标记，返回新内容
            return new_content
            
        except Exception as e:
            self.logger.error(f"合并README内容失败: {e}")
            return new_content
    
    def commit_and_push_category_repo(self, category: str, message: str) -> bool:
        """提交并推送分类仓库的变更"""
        try:
            local_path = self.category_repos_dir / category
            
            if not local_path.exists():
                self.logger.error(f"分类仓库目录不存在: {local_path}")
                return False
            
            # 获取当前分支名称
            current_branch_result = subprocess.run(
                ['git', 'rev-parse', '--abbrev-ref', 'HEAD'], 
                cwd=local_path, capture_output=True, text=True
            )
            
            if current_branch_result.returncode == 0:
                current_branch = current_branch_result.stdout.strip()
            else:
                current_branch = 'main'  # 默认分支
            
            # 检查是否有变更
            result = subprocess.run(['git', 'status', '--porcelain'], 
                                  cwd=local_path, capture_output=True, text=True)
            
            if result.returncode == 0 and result.stdout.strip():
                # 添加变更
                subprocess.run(['git', 'add', '.'], cwd=local_path, check=True)
                
                # 提交变更
                subprocess.run(['git', 'commit', '-m', message], cwd=local_path, check=True)
                
                # 推送到远程默认分支
                push_result = subprocess.run(['git', 'push', 'origin', current_branch], 
                                           cwd=local_path, capture_output=True, text=True)
                if push_result.returncode != 0:
                    self.logger.error(f"推送失败 {category}: {push_result.stderr}")
                    return False
                
                self.logger.info(f"成功提交并推送分类仓库: {category}")
                return True
            else:
                self.logger.info(f"分类仓库无变更: {category}")
                return True
                
        except subprocess.CalledProcessError as e:
            self.logger.error(f"提交推送分类仓库失败 {category}: {e}")
            return False
        except Exception as e:
            self.logger.error(f"提交推送分类仓库失败 {category}: {e}")
            return False
    
    def commit_changes(self, message: str):
        """提交本地repo-management项目的更改"""
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
                return True
            else:
                self.logger.info("没有需要提交的变更")
                return False
                
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Git操作失败: {e}")
            return False
        except Exception as e:
            self.logger.error(f"提交更改失败: {e}")
            return False