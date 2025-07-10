"""
配置文件 - GitHub仓库自动管理系统
"""
import os
from pathlib import Path

# 基础路径配置
BASE_DIR = Path("/Users/ns/Developer/Code/Local/Script/desktop/repo-management")
REPO_CATEGORIES = {
    "Default": BASE_DIR / "Default",
    "Crawler": BASE_DIR / "Crawler", 
    "Script": BASE_DIR / "Script",
    "Trading": BASE_DIR / "Trading"
}

# GitHub配置
GITHUB_USERNAME = "APE-147"
GITHUB_TOKEN_ENV = "GITHUB_TOKEN"

# 监控配置
MONITOR_INTERVAL = 60  # 秒
CACHE_FILE = BASE_DIR / "repo_cache.json"
LOG_FILE = BASE_DIR / "automation.log"

# 仓库模板配置
REPO_TEMPLATE = {
    "private": False,
    "auto_init": True,
    "gitignore_template": "Python",
    "license_template": "mit"
}

# README模板配置
README_MARKERS = {
    "start": "<!-- AUTO-GENERATED-CONTENT:START -->",
    "end": "<!-- AUTO-GENERATED-CONTENT:END -->"
}