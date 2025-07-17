#!/bin/bash

# Repository Management System Deployment Script
# 符合 ~/.env_common 规范的部署脚本

# 安全检查模板
source ~/.env_common || {
    echo "错误: ~/.env_common 文件不存在"
    exit 1
}

# 获取项目数据目录
slug=$(slugify "$(basename "$PWD")")
PROJECT_DIR=$(get_project_data "$slug")

# 脚本信息
SCRIPT_NAME="Repository Management System"
SCRIPT_VERSION="1.1.0"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# 检查系统要求
check_requirements() {
    log_info "检查系统要求..."
    
    # Python 3.8+
    if ! python3 --version &> /dev/null; then
        log_error "Python 3.8+ 是必需的"
        exit 1
    fi
    
    # Git
    if ! git --version &> /dev/null; then
        log_error "Git 是必需的"
        exit 1
    fi
    
    # GitHub CLI
    if ! gh --version &> /dev/null; then
        log_error "GitHub CLI (gh) 是必需的，请先安装并认证"
        exit 1
    fi
    
    # 检查 GitHub 认证
    if ! gh auth status &> /dev/null; then
        log_error "GitHub CLI 未认证，请运行: gh auth login"
        exit 1
    fi
    
    log_success "系统要求检查通过"
}

# 创建项目数据目录
create_project_directory() {
    log_info "创建项目数据目录: $PROJECT_DIR"
    
    # 创建主目录
    mkdir -p "$PROJECT_DIR"
    
    # 创建配置目录
    mkdir -p "$PROJECT_DIR/config"
    
    # 创建数据目录
    mkdir -p "$PROJECT_DIR/data"
    mkdir -p "$PROJECT_DIR/data/logs"
    mkdir -p "$PROJECT_DIR/data/cache"
    
    # 创建仓库索引目录
    mkdir -p "$PROJECT_DIR/repo_index"
    mkdir -p "$PROJECT_DIR/repo_index/Default"
    mkdir -p "$PROJECT_DIR/repo_index/Crawler"
    mkdir -p "$PROJECT_DIR/repo_index/Script"
    mkdir -p "$PROJECT_DIR/repo_index/Trading"
    
    # 创建远程仓库克隆目录
    mkdir -p "$PROJECT_DIR/category_repos"
    
    log_success "项目目录创建完成"
}

# 安装 Python 依赖
install_dependencies() {
    log_info "安装 Python 依赖..."
    
    cd "$SCRIPT_DIR"
    
    # 检查是否在虚拟环境中
    if [[ -n "$VIRTUAL_ENV" ]]; then
        log_info "检测到虚拟环境: $VIRTUAL_ENV"
        pip install -e . || {
            log_error "依赖安装失败"
            exit 1
        }
    else
        log_info "使用系统 Python 环境"
        # 使用 --break-system-packages 标志来绕过外部管理环境限制
        python3 -m pip install -e . --break-system-packages || {
            log_error "依赖安装失败"
            exit 1
        }
    fi
    
    log_success "依赖安装完成"
}

# 初始化配置
initialize_config() {
    log_info "初始化配置..."
    
    # 设置 GitHub 用户名
    if [[ -z "$GITHUB_USERNAME" ]]; then
        log_warning "GITHUB_USERNAME 环境变量未设置，尝试从 GitHub CLI 获取..."
        GITHUB_USERNAME=$(gh api user --jq .login 2>/dev/null)
        if [[ -z "$GITHUB_USERNAME" ]]; then
            log_error "无法获取 GitHub 用户名，请设置 GITHUB_USERNAME 环境变量"
            exit 1
        fi
    fi
    
    log_info "使用 GitHub 用户名: $GITHUB_USERNAME"
    
    # 初始化 repo-manager
    GITHUB_USERNAME="$GITHUB_USERNAME" repo-manager init --config-dir "$PROJECT_DIR/config" --force
    
    log_success "配置初始化完成"
}

# 创建 launchd 服务配置
create_launchd_service() {
    log_info "创建 launchd 服务配置..."
    
    local service_name="com.repo-management.monitor"
    local plist_path="$HOME/Library/LaunchAgents/$service_name.plist"
    
    # 创建 plist 内容
    cat > "$plist_path" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$service_name</string>
    <key>ProgramArguments</key>
    <array>
        <string>$(which repo-manager)</string>
        <string>monitor</string>
        <string>--config-dir</string>
        <string>$PROJECT_DIR/config</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$PROJECT_DIR</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$PROJECT_DIR/data/logs/stdout.log</string>
    <key>StandardErrorPath</key>
    <string>$PROJECT_DIR/data/logs/stderr.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>GITHUB_USERNAME</key>
        <string>$GITHUB_USERNAME</string>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:$(dirname $(which repo-manager))</string>
    </dict>
    <key>ThrottleInterval</key>
    <integer>60</integer>
</dict>
</plist>
EOF
    
    log_success "创建 launchd 服务配置: $plist_path"
}

# 启动服务
start_service() {
    log_info "启动服务..."
    
    local service_name="com.repo-management.monitor"
    local plist_path="$HOME/Library/LaunchAgents/$service_name.plist"
    
    # 卸载旧服务（如果存在）
    launchctl unload "$plist_path" 2>/dev/null || true
    
    # 加载新服务
    launchctl load "$plist_path" || {
        log_error "服务启动失败"
        exit 1
    }
    
    log_success "服务启动成功"
}

# 验证部署
verify_deployment() {
    log_info "验证部署..."
    
    # 检查目录结构
    if [[ ! -d "$PROJECT_DIR/config" ]]; then
        log_error "配置目录不存在"
        exit 1
    fi
    
    if [[ ! -d "$PROJECT_DIR/data" ]]; then
        log_error "数据目录不存在"
        exit 1
    fi
    
    # 测试命令
    repo-manager --help &> /dev/null || {
        log_error "repo-manager 命令不可用"
        exit 1
    }
    
    # 检查服务状态
    local service_name="com.repo-management.monitor"
    if launchctl list | grep -q "$service_name"; then
        log_success "服务运行正常"
    else
        log_warning "服务未运行，可能需要手动启动"
    fi
    
    log_success "部署验证完成"
}

# 显示部署信息
show_deployment_info() {
    log_info "部署信息:"
    echo
    echo "项目名称: $SCRIPT_NAME"
    echo "版本: $SCRIPT_VERSION"
    echo "项目目录: $PROJECT_DIR"
    echo "配置目录: $PROJECT_DIR/config"
    echo "数据目录: $PROJECT_DIR/data"
    echo "日志目录: $PROJECT_DIR/data/logs"
    echo
    echo "常用命令:"
    echo "  查看状态: repo-manager status --config-dir $PROJECT_DIR/config"
    echo "  手动扫描: repo-manager scan --config-dir $PROJECT_DIR/config"
    echo "  查看日志: tail -f $PROJECT_DIR/data/logs/stdout.log"
    echo "  停止服务: launchctl unload ~/Library/LaunchAgents/com.repo-management.monitor.plist"
    echo
}

# 主函数
main() {
    log_info "开始部署 $SCRIPT_NAME v$SCRIPT_VERSION"
    echo
    
    check_requirements
    create_project_directory
    install_dependencies
    initialize_config
    create_launchd_service
    start_service
    verify_deployment
    
    echo
    log_success "部署完成！"
    echo
    show_deployment_info
}

# 错误处理
trap 'log_error "部署过程中发生错误，退出代码: $?"' ERR

# 执行主函数
main "$@"