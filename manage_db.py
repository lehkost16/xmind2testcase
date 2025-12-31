#!/usr/bin/env python3
"""
数据库管理工具
提供常用的数据库操作命令
"""
import sqlite3
import os
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from app.core.config import settings

def get_db():
    """获取数据库连接"""
    return sqlite3.connect(settings.DATABASE_PATH)

def init_db():
    """初始化数据库"""
    if os.path.exists(settings.DATABASE_PATH):
        response = input(f"数据库 {settings.DATABASE_PATH} 已存在，是否覆盖？(y/N): ")
        if response.lower() != 'y':
            print("操作已取消")
            return
        os.remove(settings.DATABASE_PATH)
    
    conn = get_db()
    with open(settings.SCHEMA_PATH, 'r', encoding='utf-8') as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()
    print(f"✅ 数据库已初始化: {settings.DATABASE_PATH}")

def clear_records():
    """清空所有记录"""
    response = input("确定要清空所有记录吗？(y/N): ")
    if response.lower() != 'y':
        print("操作已取消")
        return
    
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM records")
    conn.commit()
    count = c.rowcount
    conn.close()
    print(f"✅ 已删除 {count} 条记录")

def clear_projects():
    """清空所有项目"""
    response = input("确定要清空所有项目吗？这将同时删除相关的记录。(y/N): ")
    if response.lower() != 'y':
        print("操作已取消")
        return
    
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM records")
    c.execute("DELETE FROM projects")
    conn.commit()
    conn.close()
    print("✅ 已清空所有项目和记录")

def show_stats():
    """显示数据库统计信息"""
    conn = get_db()
    c = conn.cursor()
    
    # 项目统计
    c.execute("SELECT COUNT(*) FROM projects WHERE is_deleted = 0")
    project_count = c.fetchone()[0]
    
    # 记录统计
    c.execute("SELECT COUNT(*) FROM records WHERE is_deleted <> 1")
    record_count = c.fetchone()[0]
    
    # 数据库大小
    db_size = os.path.getsize(settings.DATABASE_PATH) / 1024 / 1024
    
    conn.close()
    
    print("\n" + "="*50)
    print("📊 数据库统计信息")
    print("="*50)
    print(f"项目数量: {project_count}")
    print(f"记录数量: {record_count}")
    print(f"数据库大小: {db_size:.2f} MB")
    print(f"数据库路径: {settings.DATABASE_PATH}")
    print("="*50 + "\n")

def backup_db():
    """备份数据库"""
    import shutil
    from datetime import datetime
    
    backup_dir = Path("backups")
    backup_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"data_backup_{timestamp}.db3"
    
    shutil.copy2(settings.DATABASE_PATH, backup_path)
    print(f"✅ 数据库已备份到: {backup_path}")

def main():
    """主菜单"""
    while True:
        print("\n" + "="*50)
        print("🛠️  XMind2TestCase 数据库管理工具")
        print("="*50)
        print("1. 初始化数据库")
        print("2. 清空所有记录")
        print("3. 清空所有项目")
        print("4. 显示统计信息")
        print("5. 备份数据库")
        print("0. 退出")
        print("="*50)
        
        choice = input("\n请选择操作 (0-5): ").strip()
        
        if choice == '1':
            init_db()
        elif choice == '2':
            clear_records()
        elif choice == '3':
            clear_projects()
        elif choice == '4':
            show_stats()
        elif choice == '5':
            backup_db()
        elif choice == '0':
            print("👋 再见！")
            break
        else:
            print("❌ 无效的选择，请重试")

if __name__ == "__main__":
    main()
