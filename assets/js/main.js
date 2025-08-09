document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('query-form');
    const queryBtn = document.getElementById('query-btn');
    const modal = document.getElementById('modal');
    const modalMessage = document.getElementById('modal-message');
    const modalClose = document.getElementById('modal-close');
    const nameInput = document.getElementById('name');
    const idInput = document.getElementById('id');
    const nameDotBtn = document.getElementById('name-dot-btn');
    const idXBtn = document.getElementById('id-x-btn');
    const spinner = document.createElement('div');
    spinner.className = 'spinner';
    form.appendChild(spinner);

    // 添加按钮点击事件
    nameDotBtn.addEventListener('click', function() {
        console.log('Name dot button clicked');
        nameInput.value += '·';
        nameInput.focus();
    });

    idXBtn.addEventListener('click', function() {
        console.log('ID X button clicked');
        idInput.value += 'X';
        idInput.focus();
    });

    // 调试信息
    console.log('Buttons initialized:', {
        nameDotBtn: nameDotBtn,
        idXBtn: idXBtn
    });

    // 显示弹窗
    function showModal(message) {
        modalMessage.textContent = message;
        modal.style.display = 'block';
    }

    // 显示/隐藏加载动画
    function toggleLoading(show) {
        spinner.style.display = show ? 'block' : 'none';
        queryBtn.style.display = show ? 'none' : 'block';
    }

    // 关闭弹窗
    modalClose.addEventListener('click', function() {
        modal.style.display = 'none';
    });

    // 表单提交处理
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        
        // 保存原始按钮文本
        const originalText = queryBtn.textContent;
        queryBtn.disabled = true;
        
        // 更新按钮文本显示倒计时
        let seconds = 10;
        const updateButtonText = () => {
            queryBtn.textContent = `${seconds}秒后可再次${originalText}`;
            seconds--;
            if (seconds < 0) {
                clearInterval(countdownInterval);
                queryBtn.disabled = false;
                queryBtn.textContent = originalText;
            }
        };

        updateButtonText();
        const countdownInterval = setInterval(updateButtonText, 1000);

        // 获取表单数据
        const formData = {
            name: document.getElementById('name').value.trim(),
            id: document.getElementById('id').value.trim()
        };

        toggleLoading(true);
        
        // 发送查询请求
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 10000);
        
        fetch('/query', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(formData),
            signal: controller.signal
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => { throw err; });
            }
            return response.json();
        })
        .then(data => {
            showModal(data.message);
            // 如果有文件URL，自动触发下载
            if (data.file_url) {
                window.location.href = data.file_url;
            }
        })
        .finally(() => {
            toggleLoading(false);
            clearTimeout(timeoutId);
            // 确保倒计时在请求完成后继续运行
        })
        .catch(error => {
            showModal(error.error || '查询过程中发生错误');
        });
    });
});
