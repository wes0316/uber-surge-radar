#!/bin/bash

# 自動監控與提交腳本
# 當偵測到 Python 檔案變更時，自動執行提交

REPO_DIR="/Users/muder13/Documents/GitHub/uber-surge-radar"
cd "$REPO_DIR"

echo "🚀 啟動自動監控系統"
echo "📁 監控目錄: $REPO_DIR"
echo "📝 監控檔案: *.py"
echo "⏹️  按 Ctrl+C 停止監控"
echo "-" * 50

# 使用 fswatch 監控檔案變更 (如果有的話)
if command -v fswatch &> /dev/null; then
    echo "✅ 使用 fswatch 監控"
    fswatch -o "$REPO_DIR" --event=Updated --exclude=".*" --include=".*\.py$" | while read event; do
        echo "🔍 偵測到檔案變更"
        sleep 2  # 等待檔案寫入完成
        ./quick_commit.sh
    done
else
    # 備用方案：使用迴圈檢查
    echo "📝 使用輪詢檢查 (每 5 秒檢查一次)"
    LAST_HASH=""
    
    while true; do
        # 獲取當前 git 狀態的哈希值
        CURRENT_STATUS=$(git status --porcelain 2>/dev/null || echo "")
        CURRENT_HASH=$(echo "$CURRENT_STATUS" | md5sum | cut -d' ' -f1)
        
        # 如果狀態改變了，執行提交
        if [ "$CURRENT_HASH" != "$LAST_HASH" ] && [ -n "$CURRENT_STATUS" ]; then
            echo "🔍 偵測到檔案變更"
            sleep 2
            ./quick_commit.sh
            LAST_HASH="$CURRENT_HASH"
        fi
        
        sleep 5
    done
fi
