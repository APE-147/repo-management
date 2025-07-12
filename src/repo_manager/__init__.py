"""
GitHub Repository Management System
自动化GitHub仓库管理系统，支持仓库创建、分类和索引维护
"""

__version__ = "1.0.0"
__author__ = "APE-147"
__email__ = "your-email@example.com"
__description__ = "Automated GitHub repository management system"

from .core.manager import RepoManager
from .services.config import Config
from .services.database import DatabaseManager

__all__ = ["RepoManager", "Config", "DatabaseManager"]