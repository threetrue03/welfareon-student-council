(function () {

  const THEME_STORAGE_KEY = 'welfareThemeMode';

  function normalizeButtonLoadingText(button, fallback = '처리 중...') {
    const explicit = button?.dataset?.loadingText;
    if (explicit) return explicit;
    const text = (button?.textContent || '').trim();
    if (text.includes('다음')) return '저장 중...';
    if (text.includes('반납 처리')) return '반납 처리 중...';
    if (text === '처리' || text.includes('처리')) return '처리 중...';
    if (text.includes('저장')) return '저장 중...';
    if (text.includes('추가')) return '추가 중...';
    if (text.includes('삭제')) return '삭제 중...';
    if (text.includes('변경')) return '변경 중...';
    if (text.includes('확인')) return '확인 중...';
    if (text.includes('백업')) return '백업 생성 중...';
    if (text.includes('업로드')) return '업로드 중...';
    if (text.includes('가져오기')) return '가져오는 중...';
    return fallback;
  }

  function setButtonLoading(button, loadingText = null) {
    if (!button || button.dataset.loadingActive === '1') return;
    button.dataset.loadingActive = '1';
    button.dataset.originalHtml = button.innerHTML;
    if (button.offsetWidth) button.style.minWidth = `${Math.ceil(button.offsetWidth)}px`;
    button.disabled = true;
    button.classList.add('is-loading', 'button-loading');
    button.setAttribute('aria-busy', 'true');
    button.innerHTML = `<span class="button-spinner" aria-hidden="true"></span><span>${loadingText || normalizeButtonLoadingText(button)}</span>`;
  }

  function resetButtonLoading(button) {
    if (!button || button.dataset.loadingActive !== '1') return;
    button.innerHTML = button.dataset.originalHtml || button.textContent || '';
    button.disabled = false;
    button.classList.remove('is-loading', 'button-loading');
    button.removeAttribute('aria-busy');
    button.style.minWidth = '';
    delete button.dataset.loadingActive;
    delete button.dataset.originalHtml;
  }

  function setFormLoading(form, loadingText = null, submitter = null) {
    if (!form || form.dataset.formLoadingActive === '1') return false;
    form.dataset.formLoadingActive = '1';
    form.setAttribute('aria-busy', 'true');
    const button = submitter || form.querySelector('button[type="submit"], input[type="submit"]');
    if (button && button.tagName === 'BUTTON') {
      setButtonLoading(button, loadingText || normalizeButtonLoadingText(button));
    } else if (button) {
      button.disabled = true;
      button.classList.add('is-loading');
    }
    form.querySelectorAll('button[type="submit"]').forEach((other) => {
      if (other !== button) other.disabled = true;
    });
    return true;
  }

  window.WelfareONUi = Object.assign(window.WelfareONUi || {}, {
    setButtonLoading,
    resetButtonLoading,
    setFormLoading,
    showToastMessage,
  });


  function showToastMessage(message) {
    let stack = document.querySelector('[data-message-stack]');
    if (!stack) {
      stack = document.createElement('div');
      stack.className = 'message-stack';
      stack.setAttribute('data-message-stack', '');
      document.querySelector('.page-shell')?.prepend(stack);
    }
    const toast = document.createElement('div');
    toast.className = 'message message-info';
    toast.textContent = message;
    stack.appendChild(toast);
    window.setTimeout(() => toast.classList.add('is-hiding'), 1000);
    window.setTimeout(() => {
      toast.remove();
      if (stack.children.length === 0) stack.remove();
    }, 1240);
  }

  function clearToastMessages() {
    const stack = document.querySelector('[data-message-stack]');
    if (!stack) return;

    const messages = stack.querySelectorAll('.message');
    messages.forEach((message, index) => {
      const hideDelay = 1000 + index * 80;

      window.setTimeout(() => {
        message.classList.add('is-hiding');
      }, hideDelay);

      window.setTimeout(() => {
        message.remove();

        if (stack.children.length === 0) {
          stack.remove();
        }
      }, hideDelay + 240);
    });
  }

  function initSidebarToggle() {
    const layout = document.querySelector('.app-layout');
    const sidebar = document.querySelector('[data-sidebar]');
    const toggle = document.querySelector('[data-sidebar-toggle]');

    if (!layout || !sidebar || !toggle) return;

    const storageKey = 'welfareSidebarCollapsed';
    const root = document.documentElement;
    const toggleIcon = toggle.querySelector('span');

    const setToggleIcon = (collapsed) => {
      if (toggleIcon) {
        toggleIcon.textContent = collapsed ? '›' : '‹';
      }
    };

    const applyState = (collapsed, options = {}) => {
      const { instant = false, expanding = false } = options;

      if (instant) {
        layout.classList.add('sidebar-no-transition');
      }

      layout.classList.toggle('sidebar-collapsed', collapsed);
      sidebar.classList.toggle('is-collapsed', collapsed);
      toggle.setAttribute('aria-expanded', String(!collapsed));
      setToggleIcon(collapsed);

      if (expanding) {
        sidebar.classList.add('is-expanding');
        window.setTimeout(() => sidebar.classList.remove('is-expanding'), 120);
      } else {
        sidebar.classList.remove('is-expanding');
      }

      if (instant) {
        window.requestAnimationFrame(() => {
          layout.classList.remove('sidebar-no-transition');
        });
      }
    };

    const isCollapsed = window.localStorage.getItem(storageKey) === '1';
    applyState(isCollapsed, { instant: true });
    root.classList.remove('sidebar-collapsed-preload');

    toggle.addEventListener('click', () => {
      const nextCollapsed = !layout.classList.contains('sidebar-collapsed');
      window.localStorage.setItem(storageKey, nextCollapsed ? '1' : '0');
      applyState(nextCollapsed, { expanding: !nextCollapsed });
    });
  }




  function initDraggableModals() {
    const selector = '.modal-card, .rental-alert-card';
    let topZIndex = 1500;

    const isInteractiveTarget = (target) => {
      return Boolean(target.closest('button, a, input, textarea, select, label, [contenteditable="true"], [data-modal-close], [data-confirm-cancel], [data-rental-alert-close]'));
    };

    const clamp = (value, min, max) => {
      if (min > max) return value;
      return Math.min(Math.max(value, min), max);
    };

    const getHandle = (card) => {
      return card.querySelector(':scope > .modal-head')
        || card.querySelector(':scope > .modal-header')
        || card.querySelector(':scope > h2')
        || card;
    };

    const prepareCard = (card) => {
      if (!card || card.dataset.draggableReady === '1') return;
      card.dataset.draggableReady = '1';
      card.dataset.dragX = card.dataset.dragX || '0';
      card.dataset.dragY = card.dataset.dragY || '0';
      card.classList.add('draggable-modal-card');

      const handle = getHandle(card);
      handle.classList.add('draggable-modal-handle');

      handle.addEventListener('pointerdown', (event) => {
        if (event.button !== undefined && event.button !== 0) return;
        if (isInteractiveTarget(event.target)) return;

        const startX = event.clientX;
        const startY = event.clientY;
        const startOffsetX = Number.parseFloat(card.dataset.dragX || '0') || 0;
        const startOffsetY = Number.parseFloat(card.dataset.dragY || '0') || 0;
        const startRect = card.getBoundingClientRect();
        const margin = 12;

        card.classList.add('is-dragging');
        card.style.zIndex = String(++topZIndex);
        handle.setPointerCapture?.(event.pointerId);
        event.preventDefault();

        const move = (moveEvent) => {
          const deltaX = moveEvent.clientX - startX;
          const deltaY = moveEvent.clientY - startY;

          const minX = startOffsetX + margin - startRect.left;
          const maxX = startOffsetX + window.innerWidth - margin - startRect.right;
          const minY = startOffsetY + margin - startRect.top;
          const maxY = startOffsetY + window.innerHeight - margin - startRect.bottom;

          const nextX = clamp(startOffsetX + deltaX, minX, maxX);
          const nextY = clamp(startOffsetY + deltaY, minY, maxY);

          card.dataset.dragX = String(nextX);
          card.dataset.dragY = String(nextY);
          card.style.transform = `translate(${nextX}px, ${nextY}px)`;
        };

        const end = () => {
          card.classList.remove('is-dragging');
          document.removeEventListener('pointermove', move);
          document.removeEventListener('pointerup', end);
          document.removeEventListener('pointercancel', end);
        };

        document.addEventListener('pointermove', move);
        document.addEventListener('pointerup', end, { once: true });
        document.addEventListener('pointercancel', end, { once: true });
      });
    };

    const prepareAll = (root = document) => {
      root.querySelectorAll?.(selector).forEach(prepareCard);
      if (root.matches?.(selector)) prepareCard(root);
    };

    prepareAll(document);

    const observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        mutation.addedNodes.forEach((node) => {
          if (!(node instanceof Element)) return;
          prepareAll(node);
        });
      });
    });

    observer.observe(document.body, { childList: true, subtree: true });
  }

  function initZoomLock() {
    window.addEventListener('wheel', (event) => {
      if (!event.ctrlKey) return;
      event.preventDefault();
    }, { passive: false });

    document.addEventListener('keydown', (event) => {
      if (!event.ctrlKey && !event.metaKey) return;
      const key = String(event.key || '').toLowerCase();
      if (['+', '-', '=', '0'].includes(key)) {
        event.preventDefault();
      }
    });

    document.addEventListener('gesturestart', (event) => {
      event.preventDefault();
    });
  }


  function applyTheme(theme) {
    const normalized = theme === 'dark' ? 'dark' : 'light';
    document.documentElement.classList.toggle('theme-dark', normalized === 'dark');
    document.documentElement.style.colorScheme = normalized === 'dark' ? 'dark' : 'light';
    document.body?.classList.toggle('theme-dark', normalized === 'dark');
    document.querySelectorAll('[data-theme-toggle]').forEach((toggle) => {
      toggle.checked = normalized === 'dark';
      toggle.setAttribute('aria-checked', String(normalized === 'dark'));
    });
  }

  function initThemeMode() {
    let saved = 'light';
    try {
      saved = window.localStorage.getItem(THEME_STORAGE_KEY) === 'dark' ? 'dark' : 'light';
    } catch (error) {
      saved = 'light';
    }
    applyTheme(saved);
    document.querySelectorAll('[data-theme-toggle]').forEach((toggle) => {
      if (toggle.dataset.themeReady === '1') return;
      toggle.dataset.themeReady = '1';
      toggle.addEventListener('change', () => {
        const nextTheme = toggle.checked ? 'dark' : 'light';
        try { window.localStorage.setItem(THEME_STORAGE_KEY, nextTheme); } catch (error) {}
        applyTheme(nextTheme);
        showToastMessage(nextTheme === 'dark' ? '어두움 모드로 변경했습니다.' : '밝음 모드로 변경했습니다.');
      });
    });
  }

  function initUserMenu() {
    const toggle = document.querySelector('[data-user-menu-toggle]');
    const menu = document.querySelector('[data-user-menu]');
    if (!toggle || !menu) return;

    const closeMenu = () => {
      menu.hidden = true;
      toggle.classList.remove('active');
    };

    toggle.addEventListener('click', (event) => {
      event.stopPropagation();
      menu.hidden = !menu.hidden;
      toggle.classList.toggle('active', !menu.hidden);
    });

    document.addEventListener('click', (event) => {
      if (menu.hidden) return;
      if (menu.contains(event.target) || toggle.contains(event.target)) return;
      closeMenu();
    });

    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape') closeMenu();
    });
  }



  function hasHangul(value) {
    return /[가-힣ㄱ-ㅎㅏ-ㅣ]/.test(value || '');
  }

  function bindPasswordHangulBlock(root = document) {
    root.querySelectorAll?.('input[type="password"]').forEach((input) => {
      if (input.dataset.passwordHangulBlock === '1') return;
      input.dataset.passwordHangulBlock = '1';
      input.setAttribute('inputmode', 'latin');
      input.addEventListener('beforeinput', (event) => {
        if (hasHangul(event.data)) {
          event.preventDefault();
          showToastMessage('비밀번호는 영문, 숫자, 특수문자만 입력할 수 있습니다.');
        }
      });
      input.addEventListener('input', () => {
        const cleaned = Array.from(input.value).filter((ch) => /^[!-~]$/.test(ch) && !hasHangul(ch)).join('');
        if (input.value !== cleaned) {
          input.value = cleaned;
          showToastMessage('비밀번호는 영문, 숫자, 특수문자만 입력할 수 있습니다.');
        }
      });
    });
  }

  function initLoginLoading() {
    const form = document.querySelector('[data-login-form]');
    if (!form) return;
    const button = form.querySelector('[data-login-button]');
    form.addEventListener('submit', () => {
      if (button) {
        setButtonLoading(button, '로그인 중...');
      }
    });
  }

  function initEndShiftLoading() {
    document.querySelectorAll('[data-end-shift-form]').forEach((form) => {
      if (form.dataset.endShiftReady === '1') return;
      form.dataset.endShiftReady = '1';
      form.addEventListener('submit', () => {
        const button = form.querySelector('[data-end-shift-button]');
        if (button) {
          setButtonLoading(button, '근무 종료 중...');
        }
        showToastMessage('근무 종료 처리 중입니다.');
      });
    });
  }

  function initInternalNavigationLock() {
    window.open = function () { return null; };

    document.addEventListener('keydown', (event) => {
      if (event.shiftKey && event.key === 'Enter') {
        event.preventDefault();
        event.stopPropagation();
      }
    }, true);

    const cleanTargets = (root = document) => {
      root.querySelectorAll?.('a[target], form[target]').forEach((element) => {
        element.removeAttribute('target');
      });
    };

    document.addEventListener('click', (event) => {
      const anchor = event.target?.closest?.('a');
      if (!anchor) return;
      const href = anchor.getAttribute('href') || '';
      if (/^https?:\/\//i.test(href) && !href.includes('127.0.0.1') && !href.includes('localhost')) {
        event.preventDefault();
        event.stopPropagation();
      }
    }, true);

    cleanTargets(document);
    new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        mutation.addedNodes.forEach((node) => {
          if (node instanceof Element) cleanTargets(node);
        });
      });
    }).observe(document.documentElement, { childList: true, subtree: true });
  }


  function initPasswordChangeModal() {
    const modal = document.querySelector('[data-password-modal]');
    const openButton = document.querySelector('[data-password-modal-open]');
    if (!modal || !openButton) return;

    const form = modal.querySelector('[data-password-change-form]');
    const closeButtons = modal.querySelectorAll('[data-password-modal-close]');
    const firstInput = () => modal.querySelector('input[name="current_password"]');

    const closeUserMenu = () => {
      document.querySelectorAll('[data-user-menu]').forEach((menu) => { menu.hidden = true; });
      document.querySelectorAll('[data-user-menu-toggle]').forEach((toggle) => toggle.classList.remove('active'));
    };

    const closeOtherModals = () => {
      document.querySelectorAll('.modal-backdrop.open').forEach((backdrop) => {
        backdrop.classList.remove('open');
        backdrop.setAttribute('aria-hidden', 'true');
      });
      document.querySelectorAll('.item-modal.is-open, .item-modal:not([hidden])').forEach((itemModal) => {
        itemModal.classList.remove('is-open');
        itemModal.hidden = true;
        itemModal.setAttribute('aria-hidden', 'true');
      });
      document.body.classList.remove('modal-open');
    };

    const open = () => {
      closeOtherModals();
      closeUserMenu();
      modal.hidden = false;
      modal.setAttribute('aria-hidden', 'false');
      document.body.classList.add('password-modal-open');
      bindPasswordHangulBlock(modal);
      window.setTimeout(() => firstInput()?.focus(), 0);
    };

    const close = () => {
      modal.hidden = true;
      modal.setAttribute('aria-hidden', 'true');
      document.body.classList.remove('password-modal-open');
      form?.reset();
      const submit = form?.querySelector('button[type="submit"]');
      if (submit) {
        resetButtonLoading(submit);
      }
    };

    openButton.addEventListener('click', (event) => {
      event.preventDefault();
      event.stopPropagation();
      open();
    });

    closeButtons.forEach((button) => button.addEventListener('click', close));

    modal.addEventListener('click', (event) => {
      if (event.target === modal) close();
    });

    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape' && !modal.hidden) close();
    });

    form?.addEventListener('submit', (event) => {
      const p1 = form.querySelector('input[name="new_password1"]')?.value || '';
      const p2 = form.querySelector('input[name="new_password2"]')?.value || '';
      if (p1 !== p2) {
        event.preventDefault();
        showToastMessage('새 비밀번호 확인이 일치하지 않습니다.');
        return;
      }
      const submit = form.querySelector('button[type="submit"]');
      if (submit) {
        setButtonLoading(submit, '변경 중...');
      }
    });
  }


  function initGenericFormLoading() {
    document.querySelectorAll('form[method="post"], form[method="POST"]').forEach((form) => {
      if (form.dataset.genericLoadingReady === '1') return;
      if (form.matches('[data-login-form], [data-end-shift-form], [data-password-change-form], [data-loading-form]')) return;
      if (form.matches('[data-rental-cart-form], [data-return-cart-form], [data-phone-step-form]')) return;
      if (form.matches('[data-custom-confirm], .import-form, .inline-delete-form, [data-worker-edit-form], form[data-mode]')) return;
      form.dataset.genericLoadingReady = '1';
      form.addEventListener('submit', (event) => {
        if (form.dataset.skipGenericLoading === '1') return;
        if (form.dataset.formLoadingActive === '1') {
          event.preventDefault();
          return;
        }
        setFormLoading(form, event.submitter?.dataset?.loadingText || null, event.submitter || null);
      });
    });
  }

  function init() {
    clearToastMessages();
    initZoomLock();
    initDraggableModals();
    initSidebarToggle();
    initThemeMode();
    initUserMenu();
    initLoginLoading();
    initEndShiftLoading();
    initPasswordChangeModal();
    initGenericFormLoading();
    bindPasswordHangulBlock(document);
    initInternalNavigationLock();
  }

  window.addEventListener('welfare-toast', (event) => showToastMessage(event.detail || '알림'));

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
