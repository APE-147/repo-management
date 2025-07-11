# Default Projects

Default projects

## Project List


我感觉需要有一个结构图串联我的项目

### GitHub 管理

readme-flat: 本地双向同步 obsidian, 支持双向同步 markdown reeadme 的编辑, 保留自定义 readme 文件的层级结构

auto-match-pull: 匹配指定位置下的所有同名 GitHub 项目, 自动 pull, 忽略 index repo, 个人使用

repo-management: 一旦有新项目添加至 GitHub, 自动添加链接至 index 项目的 readme, 一旦repo index 的 readme 有变更, 自动push

整体流程
Obsidian 对[readme]目录下的文件进行编辑 -> readme-flat 同步更改至源地址 -> 如果是 index repo markdown -> repo-management 自动push
       -> 如果是其他项目 repo -> 本地记录更改

auto-match-pull: 
1. 未提交的更改: 会被stash保存，pull后自动恢复
2. 已提交但未推送: 不会丢失，可能产生merge commit
3. 工作目录干净: 正常pull，无影响

```mermaid
flowchart TD
%% ---------- 整体流程 ----------
subgraph SYNC["整体流程"]
    Obsidian["Obsidian 本地编辑"] 
    ReadmeFlat["readme-flat 同步"] 
    Decision["是否为 index repo?"]
    RepoMgmt["repo-management 自动 push"] 
    LocalRecord["本地记录其他项目更改"]
    GitHub["GitHub 远端"]

    Obsidian－－"编辑 [readme] 目录"－－＞ReadmeFlat
    ReadmeFlat－－"同步到源地址"－－＞Decision
    Decision－－"是"－－＞RepoMgmt
    Decision－－"否"－－＞LocalRecord
    RepoMgmt－－"push 到远端"－－＞GitHub
    LocalRecord－－"等待后续处理"－－＞GitHub
end

%% ---------- auto-match-pull 逻辑 ----------
subgraph AMP["auto-match-pull 流程"]
    Uncommit["工作目录有未提交更改"]
    Stash["stash 保存"]
    Pull1["pull 更新"]
    Restore["stash pop 恢复"]

    Committed["已提交但未 push"]
    Pull2["pull 可能产生 merge commit"]

    Clean["工作目录干净"]
    Pull3["正常 pull"]

    Uncommit－－"自动 stash"－－＞Stash
    Stash－－"拉取远端"－－＞Pull1
    Pull1－－"恢复改动"－－＞Restore

    Committed－－"拉取远端"－－＞Pull2

    Clean－－"拉取远端"－－＞Pull3
end

%% ---------- 可选着色 ----------
classDef layerStyle fill:#e0e0ff,stroke:#000080,color:#000080,font-weight:bold;
class GitHub layerStyle

```


<!-- 自动生成的项目列表将在此处更新 -->

---

*This file is automatically maintained by the repo-management system.*

<!-- AUTO-GENERATED-CONTENT:START -->
- **[readme-flat](https://github.com/APE-147/readme-flat)**
  - 创建时间: 2025-07-10
- **[auto-match-pull](https://github.com/APE-147/auto-match-pull)**
  - 创建时间: 2025-07-10
- **[repo-management](https://github.com/APE-147/repo-management)**
  - 创建时间: 2025-07-10
<!-- AUTO-GENERATED-CONTENT:END -->
