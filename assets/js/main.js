document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('query-form');
    const queryBtn = document.getElementById('query-btn');
    const modal = document.getElementById('modal');
    const modalMessage = document.getElementById('modal-message');
    const modalClose = document.getElementById('modal-close');

    // 显示弹窗
    function showModal(message) {
        modalMessage.textContent = message;
        modal.style.display = 'block';
    }

    // 关闭弹窗
    modalClose.addEventListener('click', function() {
        modal.style.display = 'none';
    });

    // 表单提交处理
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        
        // 禁用按钮10秒
        queryBtn.disabled = true;
        setTimeout(() => {
            queryBtn.disabled = false;
        }, 10000);

        // 获取表单数据
        const formData = {
            name: document.getElementById('name').value.trim(),
            id: document.getElementById('id').value.trim()
        };

        // 发送查询请求
        fetch('/query', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(formData)
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
        .catch(error => {
            showModal(error.error || '查询过程中发生错误');
        });
    });
});
