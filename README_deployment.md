# Repository Management System

## 功能实现原理

```mermaid
graph TD
    A[deploy.sh] --> B[生成scan_folders.json]
    A --> C[创建LaunchAgent]
    A --> D[设置PROJECT_DATA_DIR]
    
    E[main.py] --> F[Config加载]
    F --> G[读取scan_folders.json]
    F --> H[设置数据目录]
    
    I[文件监控] --> J[扫描配置目录]
    J --> K[发现Git仓库]
    K --> L[数据库存储]
    
    M[GitHub同步] --> N[检查远程仓库]
    N --> O[创建/更新仓库]
    O --> P[分类管理]
    
    Q[LaunchAgent] --> R[定时运行]
    R --> S[自动监控]
    S --> T[日志记录]
    
    subgraph "数据目录结构"
        U[~/Developer/Code/Data/srv/repo_management/]
        U --> V[config.json]
        U --> W[scan_folders.json]
        U --> X[logs/]
        U --> Y[repo_index/]
        U --> Z[data/cache/]
    end
```

## 文件引用关系

```mermaid
graph LR
    A[deploy.sh] --> B[src/repo_manager/services/config.py]
    B --> C[src/repo_manager/core/manager.py]
    C --> D[src/repo_manager/core/file_monitor.py]
    D --> E[src/repo_manager/services/database.py]
    E --> F[src/repo_manager/core/git_manager.py]
    
    G[scan_folders.json] --> B
    H[config.json] --> B
    I[LaunchAgent plist] --> J[main.py]
    J --> C
    
    K[PROJECT_DATA_DIR] --> B
    K --> E
    K --> L[logs/]
    K --> M[repo_index/]
```

## 部署说明

1. **运行部署脚本**：
   ```bash
   ./deploy.sh
   ```

2. **配置文件**：
   - `scan_folders.json`: 定义扫描目录和排除规则
   - `config.json`: 项目配置（GitHub用户名等）

3. **数据目录**：
   - 位置：`~/Developer/Code/Data/srv/repo_management/`
   - 包含：配置文件、日志、缓存、仓库索引

4. **服务管理**：
   - LaunchAgent 自动启动
   - 后台监控文件变化
   - 定时同步 GitHub 仓库

## 新架构特性

- ✅ 使用 PROJECT_DATA_DIR 环境变量
- ✅ 符合新的文件结构规范
- ✅ 支持用户自定义扫描目录
- ✅ 规范化数据目录命名
- ✅ 统一的部署脚本模板