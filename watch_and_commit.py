#!/usr/bin/env python3
"""
檔案監控與自動提交系統
當偵測到檔案變更時，自動執行 git 提交
"""

import os
import subprocess
import time
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class AutoCommitHandler(FileSystemEventHandler):
    def __init__(self, repo_path):
        self.repo_path = Path(repo_path)
        self.last_commit_time = 0
        self.debounce_time = 3  # 3秒內的變更合併為一次提交
        
    def on_modified(self, event):
        if event.is_directory:
            return
            
        # 只監控 Python 檔案
        if not event.src_path.endswith('.py'):
            return
            
        # 防止頻繁提交
        current_time = time.time()
        if current_time - self.last_commit_time < self.debounce_time:
            return
            
        print(f"🔍 偵測到檔案變更: {event.src_path}")
        self.last_commit_time = current_time
        
        # 等待檔案寫入完成
        time.sleep(1)
        
        # 執行自動提交
        self.auto_commit()
    
    def auto_commit(self):
        """執行自動提交"""
        try:
            # 切換到專案目錄並執行提交
            os.chdir(self.repo_path)
            
            # 檢查是否有變更
            result = subprocess.run(
                ["git", "status", "--porcelain"], 
                capture_output=True, 
                text=True
            )
            
            if not result.stdout.strip():
                print("📝 沒有需要提交的變更")
                return
            
            # 執行快速提交腳本
            print("🚀 執行自動提交...")
            subprocess.run(["./quick_commit.sh"], check=True)
            
        except subprocess.CalledProcessError as e:
            print(f"❌ 自動提交失敗: {e}")
        except Exception as e:
            print(f"❌ 監控過程中發生錯誤: {e}")

def start_file_watcher(repo_path):
    """啟動檔案監控"""
    repo_path = Path(repo_path).absolute()
    
    if not repo_path.exists():
        print(f"❌ 目錄不存在: {repo_path}")
        return
    
    print(f"🚀 啟動檔案監控系統")
    print(f"📁 監控目錄: {repo_path}")
    print(f"📝 監控檔案類型: *.py")
    print("⏹️  按 Ctrl+C 停止監控")
    print("-" * 50)
    
    # 建立監控器
    event_handler = AutoCommitHandler(repo_path)
    observer = Observer()
    observer.schedule(event_handler, str(repo_path), recursive=True)
    
    try:
        observer.start()
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("\n⏹️  停止檔案監控")
    
    observer.join()

if __name__ == "__main__":
    repo_path = "/Users/muder13/Documents/GitHub/uber-surge-radar"
    start_file_watcher(repo_path)
