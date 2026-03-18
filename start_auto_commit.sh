#!/bin/bash

# 自動提交系統啟動器
# 一鍵啟動檔案監控與自動提交

echo "🤖 Uber 運輸需求預測 - 自動提交系統"
echo "=" * 50
echo ""
echo "📋 選擇啟動模式："
echo "1. 🔄 Python 監控模式 (推薦) - 偵測 .py 檔案變更"
echo "2. ⚡ 快速提交模式 - 手動執行一次提交"
echo "3. 🚪 離開"
echo ""
read -p "請選擇模式 (1-3): " choice

case $choice in
    1)
        echo "🚀 啟動 Python 檔案監控模式..."
        echo "💡 提示：當您修改並儲存 .py 檔案時，系統會自動提交"
        echo "⏹️  按 Ctrl+C 可隨時停止監控"
        echo ""
        sleep 2
        
        # 啟動 Python 監控
        if [ -f "watch_and_commit.py" ]; then
            python3 watch_and_commit.py
        else
            echo "❌ 找不到 watch_and_commit.py"
            echo "🔄 使用備用監控模式..."
            ./auto_monitor.sh
        fi
        ;;
    2)
        echo "⚡ 執行快速提交..."
        ./quick_commit.sh
        ;;
    3)
        echo "👋 再見！"
        exit 0
        ;;
    *)
        echo "❌ 無效選擇"
        exit 1
        ;;
esac
