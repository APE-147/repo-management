"""
Core module - Main business logic
"""

from .manager import RepoManager
from .file_monitor import FileMonitor
from .github_detector import GitHubDetector
from .index_updater import IndexUpdater
from .git_manager import GitManager

__all__ = [
    "RepoManager",
    "FileMonitor", 
    "GitHubDetector",
    "IndexUpdater",
    "GitManager"
]