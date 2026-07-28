(function () {
  function copyText(text) {
    const value = String(text || '').trim();
    if (!value || value === '-') {
      window.dispatchEvent(new CustomEvent('welfare-toast', { detail: '복사할 전화번호가 없습니다.' }));
      return;
    }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(value).then(() => {
        window.dispatchEvent(new CustomEvent('welfare-toast', { detail: '전화번호가 복사되었습니다.' }));
      }).catch(() => fallbackCopy(value));
      return;
    }
    fallbackCopy(value);
  }

  function fallbackCopy(value) {
    const input = document.createElement('input');
    input.value = value;
    input.setAttribute('readonly', 'readonly');
    input.style.position = 'fixed';
    input.style.left = '-9999px';
    document.body.appendChild(input);
    input.select();
    try {
      document.execCommand('copy');
      window.dispatchEvent(new CustomEvent('welfare-toast', { detail: '전화번호가 복사되었습니다.' }));
    } catch (error) {
      window.dispatchEvent(new CustomEvent('welfare-toast', { detail: '전화번호 복사에 실패했습니다.' }));
    }
    input.remove();
  }

  document.addEventListener('click', (event) => {
    const button = event.target.closest('[data-copy-phone]');
    if (!button) return;
    copyText(button.dataset.copyPhone || '');
  });
})();
