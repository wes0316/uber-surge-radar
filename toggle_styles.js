console.log('toggle_styles.js 開始載入');

function applyToggleStyles() {
    console.log('開始應用開關樣式');
    
    // 等待 DOM 完全載入
    setTimeout(() => {
        const toggles = document.querySelectorAll('[data-testid="stToggle"]');
        console.log('找到開關數量:', toggles.length);
        
        if (toggles.length === 0) {
            console.log('沒有找到開關，等待...');
            setTimeout(applyToggleStyles, 1000);
            return;
        }
        
        toggles.forEach((toggle, index) => {
            console.log(`處理開關 ${index}`);
            const input = toggle.querySelector('input');
            const label = toggle.querySelector('label');
            
            if (input && label) {
                console.log(`開關 ${index} 狀態:`, input.checked);
                
                // 移除所有可能的樣式
                label.removeAttribute('style');
                
                // 根據狀態設定樣式
                if (input.checked) {
                    // ON 狀態 - 藍色底座 + 綠色滑塊
                    label.style.backgroundColor = '#00D4FF';
                    label.style.border = '3px solid #00D4FF';
                    label.style.boxShadow = '0 0 30px rgba(0, 212, 255, 1)';
                    
                    // 創建或更新滑塊偽元素
                    let thumb = label.querySelector('::after') || label.appendChild(document.createElement('div'));
                    thumb.style.position = 'absolute';
                    thumb.style.top = '4px';
                    thumb.style.left = 'calc(100% - 48px)';
                    thumb.style.width = '44px';
                    thumb.style.height = '44px';
                    thumb.style.backgroundColor = '#00FF88';
                    thumb.style.border = '2px solid #00CC66';
                    thumb.style.borderRadius = '50%';
                    
                    console.log(`開關 ${index} 設定為 ON 狀態`);
                } else {
                    // OFF 狀態 - 紅色底座 + 紅色滑塊
                    label.style.backgroundColor = '#2D1B1B';
                    label.style.border = '3px solid #8B4513';
                    label.style.boxShadow = 'none';
                    
                    // 創建或更新滑塊偽元素
                    let thumb = label.querySelector('::after') || label.appendChild(document.createElement('div'));
                    thumb.style.position = 'absolute';
                    thumb.style.top = '4px';
                    thumb.style.left = '4px';
                    thumb.style.width = '44px';
                    thumb.style.height = '44px';
                    thumb.style.backgroundColor = '#FF4444';
                    thumb.style.border = '2px solid #CC0000';
                    thumb.style.borderRadius = '50%';
                    
                    console.log(`開關 ${index} 設定為 OFF 狀態`);
                }
            } else {
                console.log(`開關 ${index} 結構不符合預期`);
            }
        });
    }, 500);
}

// 立即執行
applyToggleStyles();

// 監聽 DOM 變化
const observer = new MutationObserver(() => {
    console.log('DOM 變化，重新應用樣式');
    applyToggleStyles();
});

observer.observe(document.body, { childList: true, subtree: true });

// 監聽開關狀態變化
document.addEventListener('change', (e) => {
    if (e.target && e.target.closest('[data-testid="stToggle"]')) {
        console.log('開關狀態變化，重新應用樣式');
        setTimeout(applyToggleStyles, 100);
    }
});

console.log('toggle_styles.js 載入完成');
