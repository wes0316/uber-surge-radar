#!/bin/bash

# 快速自動提交腳本
# 偵測變更並自動提交

REPO_DIR="/Users/muder13/Documents/GitHub/uber-surge-radar"
cd "$REPO_DIR"

# 檢查是否有變更
if git status --porcelain | grep -q .; then
    echo "🔍 偵測到程式碼變更，正在自動提交..."
    
    # 獲取變更檔案
    CHANGED_FILES=$(git status --porcelain | wc -l)
    echo "📝 發現 $CHANGED_FILES 個檔案變更"
    
    # 添加所有變更
    git add .
    
    # 生成提交訊息
    TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
    COMMIT_MSG="🤖 自動提交: $CHANGED_FILES 個檔案變更 - $TIMESTAMP"
    
    # 提交
    git commit -m "$COMMIT_MSG"
    
    # 推送到遠端
    git push origin main
    
    echo "✅ 自動提交完成並推送到 GitHub"
else
    echo "📝 沒有偵測到變更"
fi
