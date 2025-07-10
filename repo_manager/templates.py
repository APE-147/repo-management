"""
模板文件生成器
"""
import sys
from pathlib import Path
from .config import Config

def create_launchd_plist(config: Config) -> str:
    """创建macOS LaunchAgent plist文件"""
    
    # 获取当前Python执行路径
    python_executable = sys.executable
    
    # 获取repo-manager命令路径
    import shutil
    repo_manager_path = shutil.which('repo-manager')
    if not repo_manager_path:
        # 如果找不到，使用python -m方式
        repo_manager_path = python_executable
        program_arguments = [python_executable, '-m', 'repo_manager.cli', 'monitor']
    else:
        program_arguments = [repo_manager_path, 'monitor']
    
    # 如果指定了自定义配置目录
    if config.config_dir != Path.home() / ".repo-manager":
        program_arguments.extend(['--config-dir', str(config.config_dir)])
    
    plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.github.repo-manager</string>
    
    <key>ProgramArguments</key>
    <array>
        {''.join(f'<string>{arg}</string>' for arg in program_arguments)}
    </array>
    
    <key>RunAtLoad</key>
    <true/>
    
    <key>KeepAlive</key>
    <true/>
    
    <key>StandardOutPath</key>
    <string>{config.log_dir}/launchd.out.log</string>
    
    <key>StandardErrorPath</key>
    <string>{config.log_dir}/launchd.err.log</string>
    
    <key>WorkingDirectory</key>
    <string>{config.data_dir}</string>
    
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin</string>
        <key>HOME</key>
        <string>{Path.home()}</string>
    </dict>
    
    <key>ThrottleInterval</key>
    <integer>60</integer>
    
    <key>StartInterval</key>
    <integer>{config.monitor_interval}</integer>
    
    <key>ProcessType</key>
    <string>Background</string>
</dict>
</plist>"""
    
    return plist_content

def create_readme_template(category: str, description: str) -> str:
    """创建README模板"""
    return f"""# {category} Projects

{description}

## Project List

<!-- 自动生成的项目列表将在此处更新 -->

## Recently Added

<!-- 最近添加的项目将显示在此处 -->

---

*This file is automatically maintained by the repo-management system.*

<!-- AUTO-GENERATED-CONTENT:START -->
<!-- AUTO-GENERATED-CONTENT:END -->
"""

def create_gitignore_template() -> str:
    """创建.gitignore模板"""
    return """# Repository Manager
*.log
.DS_Store
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
env/
pip-log.txt
pip-delete-this-directory.txt
.tox
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
*.py,cover
.hypothesis/
.pytest_cache/

# Cache files
repo_cache.json
github_repos.json
file_states.json

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db
"""

def create_requirements_template() -> str:
    """创建requirements.txt模板"""
    return """# GitHub Repository Manager Dependencies
# Most functionality uses Python standard library
# Optional dependencies for enhanced features:

requests>=2.25.0        # For HTTP requests (optional)
"""