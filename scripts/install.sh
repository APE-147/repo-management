#!/bin/bash
# GitHub Repository Manager Installation Script
# 自动化GitHub仓库管理系统安装脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查操作系统
detect_os() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        OS="linux"
    else
        log_error "不支持的操作系统: $OSTYPE"
        exit 1
    fi
    log_info "检测到操作系统: $OS"
}

# 检查 Python 版本
check_python() {
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
        log_info "Python 版本: $PYTHON_VERSION"
        
        # 检查版本是否 >= 3.8
        if python3 -c 'import sys; exit(0 if sys.version_info >= (3, 8) else 1)'; then
            log_success "Python 版本满足要求 (>= 3.8)"
        else
            log_error "Python 版本必须 >= 3.8，当前版本: $PYTHON_VERSION"
            exit 1
        fi
    else
        log_error "未找到 Python3，请先安装 Python 3.8+"
        exit 1
    fi
}

# 检查 Git
check_git() {
    if command -v git &> /dev/null; then
        GIT_VERSION=$(git --version)
        log_success "Git 已安装: $GIT_VERSION"
    else
        log_error "未找到 Git，请先安装 Git"
        exit 1
    fi
}

# 检查 GitHub CLI
check_gh_cli() {
    if command -v gh &> /dev/null; then
        GH_VERSION=$(gh --version | head -n1)
        log_success "GitHub CLI 已安装: $GH_VERSION"
        
        # 检查认证状态
        if gh auth status &> /dev/null; then
            log_success "GitHub CLI 已认证"
        else
            log_warning "GitHub CLI 未认证，请稍后运行: gh auth login"
        fi
    else
        log_warning "未找到 GitHub CLI，将尝试自动安装..."
        install_gh_cli
    fi
}

# 安装 GitHub CLI
install_gh_cli() {
    case $OS in
        "macos")
            if command -v brew &> /dev/null; then
                log_info "使用 Homebrew 安装 GitHub CLI..."
                brew install gh
            else
                log_error "请先安装 Homebrew 或手动安装 GitHub CLI"
                exit 1
            fi
            ;;
        "linux")
            log_info "安装 GitHub CLI..."
            curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
            sudo chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg
            echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
            sudo apt update
            sudo apt install gh
            ;;
    esac
}

# 创建数据目录
create_data_directory() {
    DATA_DIR="$HOME/Developer/Code/Script_data/repo_manager"
    log_info "创建数据目录: $DATA_DIR"
    mkdir -p "$DATA_DIR"
    log_success "数据目录创建完成"
}

# 安装依赖
install_dependencies() {
    log_info "安装 Python 依赖..."
    
    # 检查是否在虚拟环境中
    if [[ -n "$VIRTUAL_ENV" ]]; then
        log_info "检测到虚拟环境: $VIRTUAL_ENV"
        pip install --upgrade pip
        pip install typer[all] rich requests
    else
        log_info "使用系统 Python 安装依赖"
        python3 -m pip install --user --upgrade pip
        python3 -m pip install --user typer[all] rich requests
    fi
    
    log_success "依赖安装完成"
}

# 安装应用
install_app() {
    log_info "安装 repo-manager 应用..."
    
    # 检查是否在虚拟环境中
    if [[ -n "$VIRTUAL_ENV" ]]; then
        pip install -e .
    else
        python3 -m pip install --user -e .
    fi
    
    log_success "应用安装完成"
}

# 初始化应用
initialize_app() {
    log_info "初始化应用..."
    
    # 检查 GITHUB_USERNAME 环境变量
    if [[ -z "$GITHUB_USERNAME" ]]; then
        log_warning "未设置 GITHUB_USERNAME 环境变量"
        echo -n "请输入您的 GitHub 用户名: "
        read -r github_username
        if [[ -n "$github_username" ]]; then
            export GITHUB_USERNAME="$github_username"
            # 添加到 shell 配置文件
            case $SHELL in
                */zsh)
                    echo "export GITHUB_USERNAME=\"$github_username\"" >> ~/.zshrc
                    log_info "已添加到 ~/.zshrc"
                    ;;
                */bash)
                    echo "export GITHUB_USERNAME=\"$github_username\"" >> ~/.bashrc
                    log_info "已添加到 ~/.bashrc"
                    ;;
            esac
        fi
    else
        log_success "GitHub 用户名: $GITHUB_USERNAME"
    fi
    
    # 运行初始化
    repo-manager init
    
    log_success "应用初始化完成"
}

# 设置自动启动 (仅 macOS)
setup_autostart() {
    if [[ "$OS" == "macos" ]]; then
        echo -n "是否设置开机自动启动? (y/N): "
        read -r setup_autostart
        if [[ "$setup_autostart" =~ ^[Yy]$ ]]; then
            log_info "设置开机自动启动..."
            repo-manager autostart --enable
            log_success "自动启动设置完成"
        fi
    fi
}

# 显示完成信息
show_completion_info() {
    log_success "🎉 安装完成!"
    echo ""
    echo "可用命令:"
    echo "  repo-manager init      # 初始化系统"
    echo "  repo-manager scan      # 执行一次扫描"
    echo "  repo-manager monitor   # 持续监控模式"
    echo "  repo-manager status    # 查看状态"
    echo "  repo-manager --help    # 查看帮助"
    echo ""
    echo "数据目录: $DATA_DIR"
    echo ""
    if [[ -z "$(command -v gh)" ]] || ! gh auth status &> /dev/null; then
        log_warning "请先认证 GitHub CLI: gh auth login"
    fi
    echo ""
    log_info "开始监控: repo-manager monitor"
}

# 主函数
main() {
    echo "=== GitHub Repository Manager 安装脚本 ==="
    echo ""
    
    detect_os
    check_python
    check_git
    check_gh_cli
    create_data_directory
    install_dependencies
    install_app
    initialize_app
    setup_autostart
    show_completion_info
}

# 运行主函数
main "$@"