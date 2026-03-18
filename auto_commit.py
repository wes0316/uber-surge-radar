#!/usr/bin/env python3
"""
自動偵測程式碼變更並提交的腳本
"""

import os
import subprocess
import time
import json
from datetime import datetime
from pathlib import Path

class AutoCommiter:
    def __init__(self, repo_path=".", check_interval=300):
        self.repo_path = Path(repo_path)
        self.check_interval = check_interval
        self.last_commit_hash = self.get_current_commit_hash()
        
    def get_current_commit_hash(self):
        """獲取當前提交的哈希值"""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"], 
                cwd=self.repo_path,
                capture_output=True, 
                text=True
            )
            return result.stdout.strip() if result.returncode == 0 else ""
        except:
            return ""
    
    def get_git_status(self):
        """獲取 Git 狀態"""
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"], 
                cwd=self.repo_path,
                capture_output=True, 
                text=True
            )
            return result.stdout.strip().split('\n') if result.stdout.strip() else []
        except:
            return []
    
    def get_changed_files(self):
        """獲取變更的檔案列表"""
        status = self.get_git_status()
        changed_files = []
        
        for line in status:
            if line.strip():
                status_code = line[:2]
                file_path = line[3:]
                changed_files.append({
                    'status': status_code,
                    'file': file_path
                })
        
        return changed_files
    
    def analyze_changes(self, changed_files):
        """分析變更內容並生成提交訊息"""
        if not changed_files:
            return None
            
        # 分析變更類型
        file_types = {}
        change_types = {'M': 0, 'A': 0, 'D': 0, '??': 0}  # 修改、新增、刪除、未追蹤
        
        for file_info in changed_files:
            status = file_info['status']
            file_path = file_info['file']
            
            # 統計變更類型
            for change_type in change_types:
                if change_type in status:
                    change_types[change_type] += 1
            
            # 統計檔案類型
            ext = Path(file_path).suffix.lower()
            if ext:
                file_types[ext] = file_types.get(ext, 0) + 1
        
        # 生成提交訊息
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 主要變更描述
        descriptions = []
        if change_types['M'] > 0:
            descriptions.append(f"修改 {change_types['M']} 個檔案")
        if change_types['A'] > 0:
            descriptions.append(f"新增 {change_types['A']} 個檔案")
        if change_types['D'] > 0:
            descriptions.append(f"刪除 {change_types['D']} 個檔案")
        
        # 檔案類型統計
        if file_types:
            main_types = sorted(file_types.items(), key=lambda x: x[1], reverse=True)[:3]
            type_desc = ", ".join([f"{ext}({count})" for ext, count in main_types])
            descriptions.append(f"主要檔案類型: {type_desc}")
        
        commit_message = f"🤖 自動提交: {'; '.join(descriptions)} - {timestamp}"
        
        return commit_message
    
    def add_and_commit(self, commit_message):
        """添加變更並提交"""
        try:
            # 添加所有變更
            subprocess.run(["git", "add", "."], cwd=self.repo_path, check=True)
            
            # 提交
            subprocess.run(
                ["git", "commit", "-m", commit_message], 
                cwd=self.repo_path, 
                check=True
            )
            
            print(f"✅ 自動提交成功: {commit_message}")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ 提交失敗: {e}")
            return False
    
    def push_to_remote(self):
        """推送到遠端倉庫"""
        try:
            subprocess.run(
                ["git", "push", "origin", "main"], 
                cwd=self.repo_path, 
                check=True
            )
            print("🚀 已推送到遠端倉庫")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ 推送失敗: {e}")
            return False
    
    def check_and_commit(self):
        """檢查變更並自動提交"""
        changed_files = self.get_changed_files()
        
        if not changed_files:
            print("📝 沒有偵測到變更")
            return False
        
        print(f"🔍 偵測到 {len(changed_files)} 個檔案變更")
        
        # 分析變更並生成提交訊息
        commit_message = self.analyze_changes(changed_files)
        
        if commit_message:
            print(f"📝 生成提交訊息: {commit_message}")
            
            # 提交變更
            if self.add_and_commit(commit_message):
                # 推送到遠端
                self.push_to_remote()
                
                # 更新最後提交哈希
                self.last_commit_hash = self.get_current_commit_hash()
                return True
        
        return False
    
    def start_monitoring(self):
        """開始監控變更"""
        print(f"🚀 開始自動提交監控 (檢查間隔: {self.check_interval} 秒)")
        print(f"📁 監控目錄: {self.repo_path.absolute()}")
        
        while True:
            try:
                self.check_and_commit()
                time.sleep(self.check_interval)
            except KeyboardInterrupt:
                print("\n⏹️  停止自動提交監控")
                break
            except Exception as e:
                print(f"❌ 監控過程中發生錯誤: {e}")
                time.sleep(self.check_interval)

if __name__ == "__main__":
    # 設定參數
    repo_path = "."  # 當前目錄
    check_interval = 300  # 5 分鐘檢查一次
    
    # 建立自動提交器
    auto_commiter = AutoCommiter(repo_path, check_interval)
    
    # 執行一次檢查
    auto_commiter.check_and_commit()
    
    # 開始持續監控 (註解掉這行可以只執行一次檢查)
    # auto_commiter.start_monitoring()
