"""
GitHub Repository Manager - Setup Script
自动化GitHub仓库管理系统的安装脚本
"""

from setuptools import setup, find_packages
from pathlib import Path

# 读取README文件
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding='utf-8')

# 读取requirements.txt
requirements = []
requirements_file = this_directory / "requirements.txt"
if requirements_file.exists():
    requirements = requirements_file.read_text().splitlines()

setup(
    name="github_repo_manager",
    version="1.0.0",
    author="APE-147",
    author_email="your-email@example.com",
    description="Automated GitHub repository management system",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/APE-147/github-repo-manager",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Software Development :: Version Control :: Git",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.8",
    install_requires=[
        # 基础依赖，大部分功能使用标准库
        "requests>=2.25.0",  # 如果需要HTTP请求
    ],
    extras_require={
        "dev": [
            "pytest>=6.0",
            "black>=21.0",
            "flake8>=3.8",
            "mypy>=0.812",
        ]
    },
    entry_points={
        "console_scripts": [
            "repo-manager=repo_manager.cli:main",
        ],
    },
    package_data={
        "repo_manager": [
            "templates/*.plist",
            "templates/*.md",
        ],
    },
    include_package_data=True,
    zip_safe=False,
    keywords="github automation repository management cli",
    project_urls={
        "Bug Reports": "https://github.com/APE-147/github-repo-manager/issues",
        "Source": "https://github.com/APE-147/github-repo-manager",
        "Documentation": "https://github.com/APE-147/github-repo-manager/wiki",
    },
)