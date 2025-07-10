#!/usr/bin/env python3
"""
清理缓存中的重复仓库记录
"""
import json
from pathlib import Path

def clean_repo_cache():
    """清理仓库缓存中的重复记录"""
    cache_file = Path("repo_cache.json")
    
    if not cache_file.exists():
        print("缓存文件不存在")
        return
    
    # 读取缓存
    with open(cache_file, 'r', encoding='utf-8') as f:
        cache_data = json.load(f)
    
    # 去重处理
    repos = cache_data.get("repos", [])
    unique_repos = {}
    
    # 使用仓库名称作为key，保留最新的记录
    for repo in repos:
        repo_name = repo["name"]
        if repo_name not in unique_repos:
            unique_repos[repo_name] = repo
        else:
            # 比较创建时间，保留更新的记录
            existing_time = unique_repos[repo_name]["created_at"]
            current_time = repo["created_at"]
            
            # 如果当前记录更新，替换
            if current_time > existing_time:
                unique_repos[repo_name] = repo
    
    # 转换回列表
    cleaned_repos = list(unique_repos.values())
    
    print(f"原始记录数: {len(repos)}")
    print(f"去重后记录数: {len(cleaned_repos)}")
    
    # 更新缓存
    cache_data["repos"] = cleaned_repos
    
    # 保存清理后的缓存
    with open(cache_file, 'w', encoding='utf-8') as f:
        json.dump(cache_data, f, indent=2, ensure_ascii=False)
    
    print("缓存清理完成")

if __name__ == "__main__":
    clean_repo_cache()