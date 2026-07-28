function setFormLoadingState(form, text, submitter = null) {
  if (window.WelfareONUi?.setFormLoading) return window.WelfareONUi.setFormLoading(form, text, submitter);
  const button = submitter || form?.querySelector('button[type="submit"]');
  if (button) {
    button.disabled = true;
    button.classList.add('is-loading');
    button.textContent = text || '처리 중...';
  }
  return true;
}

function setButtonLoadingState(button, text) {
  if (window.WelfareONUi?.setButtonLoading) return window.WelfareONUi.setButtonLoading(button, text);
  if (button) {
    button.disabled = true;
    button.classList.add('is-loading');
    button.textContent = text || '처리 중...';
  }
}

function ensureConfirmModal() {
  let modal = document.getElementById('uiConfirmModal');
  if (modal) return modal;
  modal = document.createElement('div');
  modal.id = 'uiConfirmModal';
  modal.className = 'item-modal confirm-modal';
  modal.hidden = true;
  modal.innerHTML = `
    <div class="modal-backdrop" data-confirm-cancel></div>
    <div class="modal-card compact-rental-modal" role="dialog" aria-modal="true">
      <div class="modal-head"><h2>확인</h2><button class="modal-close" type="button" data-confirm-cancel aria-label="닫기">×</button></div>
      <p class="confirm-message" data-confirm-message></p>
      <div class="confirm-actions">
        <button type="button" class="confirm-cancel" data-confirm-cancel>취소</button>
        <button type="button" class="confirm-ok" data-confirm-ok>확인</button>
      </div>
    </div>`;
  document.body.appendChild(modal);
  return modal;
}

function showConfirm(message, onConfirm) {
  const modal = ensureConfirmModal();
  const messageElement = modal.querySelector('[data-confirm-message]');
  const okButton = modal.querySelector('[data-confirm-ok]');
  const cancelButtons = modal.querySelectorAll('[data-confirm-cancel]');
  messageElement.textContent = message;
  modal.hidden = false;
  document.body.classList.add('modal-open');
  const close = () => {
    modal.hidden = true;
    document.body.classList.remove('modal-open');
    okButton.onclick = null;
    cancelButtons.forEach((button) => { button.onclick = null; });
  };
  okButton.onclick = () => { close(); if (typeof onConfirm === 'function') onConfirm(); };
  cancelButtons.forEach((button) => { button.onclick = close; });
}

function updateItemTypeFields(form) {
  const selected = form.querySelector('input[name="item_type"]:checked');
  const type = selected ? selected.value : '';
  form.querySelectorAll('.equipment-fields').forEach((el) => { el.hidden = type !== 'equipment'; });
  form.querySelectorAll('.consumable-fields').forEach((el) => { el.hidden = type !== 'consumable'; });
}

function setupItemForms(scope = document) {
  scope.querySelectorAll('form[data-mode]').forEach((form) => {
    if (form.dataset.itemFormReady === '1') return;
    form.dataset.itemFormReady = '1';
    form.querySelectorAll('input[name="item_type"]').forEach((input) => input.addEventListener('change', () => updateItemTypeFields(form)));
    updateItemTypeFields(form);
    form.addEventListener('submit', (event) => {
      if (form.dataset.confirmed === '1') return;
      const selected = form.querySelector('input[name="item_type"]:checked');
      const type = selected ? selected.value : '';
      const mode = form.dataset.mode;
      const oldTotal = Number(form.dataset.oldTotal || 0);
      const totalInput = form.querySelector('[name="total_quantity"]');
      const newTotal = totalInput ? Number(totalInput.value || 0) : 0;
      if (mode === 'update' && type === 'equipment' && newTotal < oldTotal) {
        event.preventDefault();
        showConfirm(`전체 수량을 줄이면 ${newTotal + 1}번부터 ${oldTotal}번까지의 개별 물품 상태가 비활성 처리됩니다. 계속할까요?`, () => {
          form.dataset.confirmed = '1';
          setFormLoadingState(form, '저장 중...');
          form.submit();
        });
        return;
      }
      setFormLoadingState(form, '저장 중...', event.submitter || form.querySelector('button[type="submit"]'));
    });
  });
}

function getCsrfToken() {
  const input = document.querySelector('input[name="csrfmiddlewaretoken"]');
  if (input?.value) return input.value;
  const match = document.cookie.match(/(?:^|; )csrftoken=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : '';
}

function askTargetAdminPassword(message = '해당 관리자 비밀번호를 입력해주세요.') {
  const password = window.prompt(message);
  return password ? password.trim() : '';
}

function fillTargetAdminPassword(form) {
  if (!form?.dataset.adminProtected) return true;
  const hidden = form.querySelector('input[name="target_admin_password"]');
  if (hidden?.value) return true;
  const password = askTargetAdminPassword();
  if (!password) return false;
  if (hidden) hidden.value = password;
  return true;
}

function setupDeleteConfirm(scope = document) {
  scope.querySelectorAll('.inline-delete-form').forEach((form) => {
    if (form.dataset.deleteReady === '1') return;
    form.dataset.deleteReady = '1';
    form.addEventListener('submit', (event) => {
      if (form.dataset.confirmed === '1') return;
      event.preventDefault();
      if (!fillTargetAdminPassword(form)) return;
      showConfirm(form.dataset.confirm || '삭제하시겠습니까?', () => {
        form.dataset.confirmed = '1';
        setFormLoadingState(form, '삭제 중...');
        form.submit();
      });
    });
  });
}

function setupModals(scope = document) {
  const openModal = (modal) => {
    if (!modal) return;
    modal.hidden = false;
    requestAnimationFrame(() => modal.classList.add('is-open'));
    document.body.classList.add('modal-open');
    const firstInput = modal.querySelector('input, select, textarea, button');
    if (firstInput) firstInput.focus({ preventScroll: true });
  };
  const closeModal = (modal) => {
    if (!modal) return;
    modal.classList.remove('is-open');
    document.body.classList.remove('modal-open');
    window.setTimeout(() => { if (!modal.classList.contains('is-open')) modal.hidden = true; }, 160);
  };
  scope.querySelectorAll('[data-modal-open]').forEach((button) => {
    if (button.dataset.modalOpenReady === '1') return;
    button.dataset.modalOpenReady = '1';
    button.addEventListener('click', () => openModal(document.getElementById(button.dataset.modalOpen)));
  });
  scope.querySelectorAll('.item-modal').forEach((modal) => {
    modal.querySelectorAll('[data-modal-close]').forEach((button) => {
      if (button.dataset.modalCloseReady === '1') return;
      button.dataset.modalCloseReady = '1';
      button.addEventListener('click', () => closeModal(modal));
    });
  });
  document.querySelectorAll('.item-modal.is-open').forEach((modal) => { modal.hidden = false; document.body.classList.add('modal-open'); });
}


function setupSimplePostFormLoading(scope = document) {
  scope.querySelectorAll('form.modal-form:not([data-mode]):not([data-worker-edit-form])').forEach((form) => {
    if (form.dataset.simpleLoadingReady === '1') return;
    form.dataset.simpleLoadingReady = '1';
    form.addEventListener('submit', (event) => {
      if (form.dataset.formLoadingActive === '1') {
        event.preventDefault();
        return;
      }
      setFormLoadingState(form, event.submitter?.dataset?.loadingText || null, event.submitter || form.querySelector('button[type="submit"]'));
    });
  });
}

function setupAjaxSearchForms() {
  const debounceDelay = 100;
  document.querySelectorAll('[data-auto-search-form]').forEach((form) => {
    if (form.dataset.ajaxSearchReady === '1') return;
    form.dataset.ajaxSearchReady = '1';
    const input = form.querySelector('input[type="search"]');
    const selects = form.querySelectorAll('select');
    const targetSelector = form.dataset.resultsTarget;
    let timer = null;
    let isComposing = false;
    let activeController = null;

    const refreshTarget = async (url, { replaceUrl = true } = {}) => {
      if (isComposing) return;
      const target = document.querySelector(targetSelector);
      if (!target) return;
      if (activeController) activeController.abort();
      activeController = new AbortController();
      try {
        const response = await fetch(url, {
          headers: { 'X-Requested-With': 'XMLHttpRequest' },
          signal: activeController.signal,
        });
        if (!response.ok) throw new Error('search failed');
        const html = await response.text();
        const doc = new DOMParser().parseFromString(html, 'text/html');
        const nextTarget = doc.querySelector(targetSelector);
        if (!nextTarget) return;
        target.innerHTML = nextTarget.innerHTML;
        if (replaceUrl) history.replaceState(null, '', url);
        setupItemForms(target);
        setupDeleteConfirm(target);
        setupModals(target);
        setupWorkerPasswordTools(target);
        setupSimplePostFormLoading(target);
        bindPaginationLinks();
      } catch (error) {
        if (error.name === 'AbortError') return;
        form.submit();
      }
    };

    const buildSearchUrl = () => {
      const params = new URLSearchParams(new FormData(form));
      params.delete('page');
      const query = params.toString();
      return query ? `${window.location.pathname}?${query}` : window.location.pathname;
    };

    const runSearch = () => refreshTarget(buildSearchUrl());

    const scheduleSearch = () => {
      window.clearTimeout(timer);
      timer = window.setTimeout(runSearch, debounceDelay);
    };

    function bindPaginationLinks() {
      const target = document.querySelector(targetSelector);
      if (!target) return;
      target.querySelectorAll('[data-ajax-page]').forEach((link) => {
        if (link.dataset.ajaxPageReady === '1') return;
        link.dataset.ajaxPageReady = '1';
        link.addEventListener('click', (event) => {
          event.preventDefault();
          window.clearTimeout(timer);
          refreshTarget(link.href);
        });
      });
    }

    input?.addEventListener('compositionstart', () => { isComposing = true; });
    input?.addEventListener('compositionend', () => { isComposing = false; scheduleSearch(); });
    input?.addEventListener('input', () => { if (!isComposing) scheduleSearch(); });
    selects.forEach((select) => select.addEventListener('change', runSearch));
    form.addEventListener('submit', (event) => { event.preventDefault(); window.clearTimeout(timer); runSearch(); });
    bindPaginationLinks();
  });
}

function setImportFormLoading(form) {
  if (!form || form.dataset.importSubmitting === '1') return false;
  form.dataset.importSubmitting = '1';
  form.setAttribute('aria-busy', 'true');

  const uploadButton = form.querySelector('.import-upload-button');
  if (uploadButton) {
    uploadButton.dataset.originalHtml = uploadButton.innerHTML;
    uploadButton.disabled = true;
    uploadButton.classList.add('is-loading');
    uploadButton.setAttribute('aria-busy', 'true');
    uploadButton.setAttribute('aria-label', uploadButton.getAttribute('aria-label') === '백업 다운로드' ? '백업 생성 중' : '가져오는 중');
    uploadButton.setAttribute('title', uploadButton.getAttribute('title') === '백업 다운로드' ? '백업 생성 중' : '가져오는 중');
    uploadButton.innerHTML = '<span class="upload-spinner" aria-hidden="true"></span>';
  } else {
    setFormLoadingState(form, '처리 중...');
  }

  return true;
}

function setupImportUploadForms() {
  document.querySelectorAll('.import-form').forEach((form) => {
    if (form.dataset.importUploadReady === '1') return;
    form.dataset.importUploadReady = '1';

    form.addEventListener('submit', (event) => {
      if (form.dataset.customConfirm && form.dataset.confirmed !== '1') return;
      if (!setImportFormLoading(form)) {
        event.preventDefault();
      }
    });
  });
}

function setupCustomConfirmForms() {
  document.querySelectorAll('form[data-custom-confirm]').forEach((form) => {
    if (form.dataset.customConfirmReady === '1') return;
    form.dataset.customConfirmReady = '1';
    form.addEventListener('submit', (event) => {
      if (form.dataset.confirmed === '1') return;
      event.preventDefault();
      showConfirm(form.dataset.customConfirm || '계속 진행할까요?', () => {
        if (!setImportFormLoading(form)) return;
        form.dataset.confirmed = '1';
        form.submit();
      });
    });
  });
}


function setupWorkerPasswordTools(scope = document) {
  scope.querySelectorAll('[data-worker-password-toggle]').forEach((button) => {
    if (button.dataset.passwordToggleReady === '1') return;
    button.dataset.passwordToggleReady = '1';
    button.addEventListener('click', async () => {
      const field = button.closest('.password-inline-control')?.querySelector('[data-worker-password-field]');
      if (!field) return;
      if (field.type === 'text') {
        field.type = 'password';
        button.textContent = '🙈';
        return;
      }
      if (!field.value) {
        let password = '';
        if (button.dataset.adminPasswordProtected === '1') {
          password = askTargetAdminPassword('해당 관리자 비밀번호를 입력하면 비밀번호를 확인할 수 있습니다.');
          if (!password) return;
        }
        try {
          const body = new URLSearchParams();
          body.set('target_admin_password', password);
          const response = await fetch(button.dataset.revealUrl, {
            method: 'POST',
            headers: {
              'X-CSRFToken': getCsrfToken(),
              'X-Requested-With': 'XMLHttpRequest',
              'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
            },
            body,
          });
          const data = await response.json();
          if (!response.ok || !data.ok) {
            window.alert(data.message || '비밀번호를 확인할 수 없습니다.');
            return;
          }
          if (!data.password) {
            window.alert(data.message || '저장된 표시용 비밀번호가 없습니다.');
            return;
          }
          field.value = data.password;
        } catch (error) {
          window.alert('비밀번호 확인 중 오류가 발생했습니다.');
          return;
        }
      }
      field.type = 'text';
      button.textContent = '👁️';
    });
  });

  scope.querySelectorAll('[data-worker-edit-form]').forEach((form) => {
    if (form.dataset.workerEditReady === '1') return;
    form.dataset.workerEditReady = '1';
    form.addEventListener('submit', (event) => {
      if (form.dataset.confirmed === '1') return;
      event.preventDefault();
      if (!fillTargetAdminPassword(form)) return;
      const passwordInput = form.querySelector('[data-new-password-field]');
      if (passwordInput?.value) {
        showConfirm('정말 비밀번호를 변경하시겠습니까?', () => {
          form.dataset.confirmed = '1';
          setFormLoadingState(form, '저장 중...');
          form.submit();
        });
        return;
      }
      form.dataset.confirmed = '1';
      setFormLoadingState(form, '저장 중...');
      form.submit();
    });
  });
}

document.addEventListener('keydown', (event) => {
  if (event.key !== 'Escape') return;
  document.querySelectorAll('.item-modal.is-open').forEach((modal) => {
    modal.classList.remove('is-open');
    modal.hidden = true;
  });
  document.body.classList.remove('modal-open');
});

setupItemForms();
setupDeleteConfirm();
setupModals();
setupWorkerPasswordTools();
setupSimplePostFormLoading();
setupAjaxSearchForms();
setupImportUploadForms();
setupCustomConfirmForms();
