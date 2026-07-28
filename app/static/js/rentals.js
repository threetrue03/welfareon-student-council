(() => {
  const DEBOUNCE_DELAY = 100;

  function showRentalAlert(message) {
    let modal = document.getElementById('rentalAlertModal');
    if (!modal) {
      modal = document.createElement('div');
      modal.id = 'rentalAlertModal';
      modal.className = 'rental-alert';
      modal.hidden = true;
      modal.innerHTML = `
        <div class="rental-alert-backdrop" data-rental-alert-close></div>
        <div class="rental-alert-card" role="dialog" aria-modal="true" aria-labelledby="rentalAlertTitle">
          <h2 id="rentalAlertTitle">확인</h2>
          <p data-rental-alert-message></p>
          <button type="button" data-rental-alert-close>확인</button>
        </div>
      `;
      document.body.appendChild(modal);
    }
    modal.querySelector('[data-rental-alert-message]').textContent = message;
    modal.hidden = false;
    document.body.classList.add('modal-open');
    modal.querySelectorAll('[data-rental-alert-close]').forEach((button) => {
      button.onclick = () => {
        modal.hidden = true;
        document.body.classList.remove('modal-open');
      };
    });
  }

  function escapeHtml(value) {
    return String(value || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function setFormLoading(form, text, submitter = null) {
    if (window.WelfareONUi?.setFormLoading) return window.WelfareONUi.setFormLoading(form, text, submitter);
    const button = submitter || form?.querySelector('button[type="submit"]');
    if (button) {
      button.disabled = true;
      button.classList.add('is-loading');
      button.textContent = text || '처리 중...';
    }
    return true;
  }

  function setButtonLoading(button, text) {
    if (window.WelfareONUi?.setButtonLoading) return window.WelfareONUi.setButtonLoading(button, text);
    if (button) {
      button.disabled = true;
      button.classList.add('is-loading');
      button.textContent = text || '처리 중...';
    }
  }

  function debounce(fn, delay = DEBOUNCE_DELAY) {
    let timer = null;
    return (...args) => {
      window.clearTimeout(timer);
      timer = window.setTimeout(() => fn(...args), delay);
    };
  }

  function setupStudentAutocomplete() {
    const form = document.querySelector('[data-student-search-form]');
    const input = document.querySelector('[data-student-search-input]');
    const resultList = document.querySelector('[data-student-results]');
    if (!form || !input || !resultList) return;

    const searchUrl = form.dataset.searchUrl;
    let activeController = null;
    let isComposing = false;

    const buildStudentHref = (studentId, query) => {
      const params = new URLSearchParams(window.location.search);
      params.set('student', studentId);
      params.delete('item');
      params.delete('page');
      params.delete('record_page');
      params.delete('phone_ready');
      if (query) params.set('student_q', query);
      else params.delete('student_q');
      return `${window.location.pathname}?${params.toString()}`;
    };

    const renderEmpty = (message) => {
      resultList.hidden = false;
      resultList.innerHTML = `<p class="empty-state">${escapeHtml(message)}</p>`;
    };

    const clearResults = () => {
      resultList.innerHTML = '';
      resultList.hidden = true;
    };

    const renderResults = (students, query) => {
      if (!query) {
        clearResults();
        return;
      }
      if (!students.length) {
        renderEmpty('검색 결과 없음');
        return;
      }
      resultList.hidden = false;
      resultList.innerHTML = '';
      students.forEach((student) => {
        const card = document.createElement('a');
        card.className = 'student-card';
        card.href = buildStudentHref(student.id, query);
        card.innerHTML = `
          <span class="student-id">${escapeHtml(student.student_id)}</span>
          <strong class="student-name">${escapeHtml(student.name)}</strong>
        `;
        resultList.appendChild(card);
      });
    };

    const runSearch = async () => {
      if (isComposing) return;
      const query = input.value.trim();
      if (!query) {
        clearResults();
        return;
      }
      if (activeController) activeController.abort();
      activeController = new AbortController();
      resultList.hidden = false;
      try {
        const url = new URL(searchUrl, window.location.origin);
        url.searchParams.set('q', query);
        const response = await fetch(url, {
          headers: { 'X-Requested-With': 'XMLHttpRequest' },
          signal: activeController.signal,
        });
        if (!response.ok) throw new Error('search failed');
        const data = await response.json();
        renderResults(data.results || [], query);
      } catch (error) {
        if (error.name === 'AbortError') return;
        renderEmpty('검색 중 오류가 발생했습니다.');
      }
    };

    const debouncedSearch = debounce(runSearch);
    input.addEventListener('compositionstart', () => { isComposing = true; });
    input.addEventListener('compositionend', () => { isComposing = false; debouncedSearch(); });
    input.addEventListener('input', () => {
      if (isComposing) return;
      debouncedSearch();
    });
    form.addEventListener('submit', (event) => {
      event.preventDefault();
      runSearch();
    });
  }

  function setupRentalItemPartialSearch() {
    const form = document.querySelector('[data-rental-item-form]');
    if (!form) return;
    const input = form.querySelector('input[type="search"]');
    const category = form.querySelector('select[name="category"]');
    const targetSelector = form.dataset.resultsTarget;
    let isComposing = false;
    let activeController = null;

    const refreshItemArea = async (url) => {
      if (input?.disabled || isComposing) return;
      const target = document.querySelector(targetSelector);
      if (!target) return;
      const panel = target.closest('.item-panel') || target.closest('.panel') || target;
      if (activeController) activeController.abort();
      activeController = new AbortController();
      try {
        panel.classList.add('is-loading');
        panel.setAttribute('aria-busy', 'true');
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
        window.history.replaceState(null, '', url);
        setupSelectedItemPanel();
        bindPaginationLinks();
        document.dispatchEvent(new CustomEvent('rental:item-panel-updated'));
      } catch (error) {
        if (error.name === 'AbortError') return;
        showRentalAlert('검색 중 오류가 발생했습니다.');
      } finally {
        panel.classList.remove('is-loading');
        panel.removeAttribute('aria-busy');
      }
    };

    const buildSearchUrl = () => {
      const params = new URLSearchParams(new FormData(form));
      params.delete('page');
      const query = params.toString();
      return query ? `${window.location.pathname}?${query}` : window.location.pathname;
    };

    const runSearch = () => refreshItemArea(buildSearchUrl());
    const debouncedSearch = debounce(runSearch);

    function bindPaginationLinks() {
      const target = document.querySelector(targetSelector);
      if (!target) return;
      const panel = target.closest('.item-panel') || target.closest('.panel') || target;
      target.querySelectorAll('[data-ajax-page]').forEach((link) => {
        if (link.dataset.ajaxPageReady === '1') return;
        link.dataset.ajaxPageReady = '1';
        link.addEventListener('click', (event) => {
          event.preventDefault();
          refreshItemArea(link.href);
        });
      });
    }

    input?.addEventListener('compositionstart', () => { isComposing = true; });
    input?.addEventListener('compositionend', () => { isComposing = false; debouncedSearch(); });
    input?.addEventListener('input', () => {
      if (isComposing) return;
      debouncedSearch();
    });
    category?.addEventListener('change', runSearch);
    form.addEventListener('submit', (event) => {
      event.preventDefault();
      runSearch();
    });
    bindPaginationLinks();
  }

  function setupSelectedItemPanel() {
    const panel = document.querySelector('[data-selected-item-panel]');
    if (!panel) return;
    const selectItem = (card) => {
      const template = card.querySelector('[data-item-action-template]');
      if (!template) return;
      document.querySelectorAll('[data-item-source]').forEach((source) => {
        source.classList.toggle('selected', source === card);
      });
      panel.innerHTML = '';
      panel.appendChild(template.content.cloneNode(true));
      document.dispatchEvent(new CustomEvent('rental:item-panel-updated'));
    };
    document.querySelectorAll('[data-item-source]').forEach((card) => {
      if (card.dataset.listenerReady === '1') return;
      card.dataset.listenerReady = '1';
      card.addEventListener('click', () => selectItem(card));
      card.addEventListener('keydown', (event) => {
        if (event.key !== 'Enter' && event.key !== ' ') return;
        event.preventDefault();
        selectItem(card);
      });
    });
  }


  function setupPhoneStepLoading() {
    document.querySelectorAll('[data-phone-step-form]').forEach((form) => {
      if (form.dataset.phoneStepLoadingReady === '1') return;
      form.dataset.phoneStepLoadingReady = '1';
      form.addEventListener('submit', (event) => {
        if (form.dataset.formLoadingActive === '1') {
          event.preventDefault();
          return;
        }
        setFormLoading(form, '저장 중...', event.submitter || form.querySelector('button[type="submit"]'));
      });
    });
  }

  function setupRentalCart() {

    const form = document.querySelector('[data-rental-cart-form]');
    const list = document.querySelector('[data-rental-cart-list]');
    const hiddenFields = document.querySelector('[data-cart-hidden-fields]');
    const count = document.querySelector('[data-cart-count]');
    const submitButton = document.querySelector('[data-rental-cart-submit]');
    if (!form || !list || !hiddenFields || !count || !submitButton) return;

    const cart = [];
    const getSelectedUnitIds = () => new Set(cart.filter((item) => item.type === 'equipment').map((item) => item.unitId));

    const syncSelectOptions = () => {
      const selectedUnitIds = getSelectedUnitIds();
      document.querySelectorAll('[data-cart-unit-select]').forEach((select) => {
        let firstAvailableOption = null;
        Array.from(select.options).forEach((option) => {
          const unitStatus = option.dataset.unitStatus || 'disabled';
          const isBaseAvailable = unitStatus === 'available';
          const isAlreadyInCart = selectedUnitIds.has(option.value);
          const shouldDisable = !isBaseAvailable || isAlreadyInCart;
          option.disabled = shouldDisable;
          if (!shouldDisable && !firstAvailableOption) firstAvailableOption = option;
        });
        if (select.selectedOptions[0]?.disabled && firstAvailableOption) select.value = firstAvailableOption.value;
        const hasAvailable = Boolean(firstAvailableOption);
        select.disabled = !hasAvailable;
        const addButton = select.closest('[data-cart-source]')?.querySelector('[data-cart-add]');
        if (addButton) addButton.disabled = !hasAvailable;
      });
    };

    const renderCart = () => {
      count.textContent = `${cart.length}개`;
      hiddenFields.innerHTML = '';
      list.innerHTML = '';
      if (!cart.length) {
        list.innerHTML = '<p class="empty-state cart-empty">아직 담긴 물품이 없습니다.</p>';
        submitButton.disabled = true;
        syncSelectOptions();
        return;
      }

      cart.forEach((item, index) => {
        if (item.type === 'equipment') {
          hiddenFields.insertAdjacentHTML('beforeend', `<input type="hidden" name="equipment_unit_ids" value="${escapeHtml(item.unitId)}">`);
        } else {
          hiddenFields.insertAdjacentHTML('beforeend', `<input type="hidden" name="consumable_item_ids" value="${escapeHtml(item.itemId)}"><input type="hidden" name="consumable_quantities" value="${escapeHtml(item.quantity)}">`);
        }
        const card = document.createElement('div');
        card.className = 'cart-selected-card';
        card.innerHTML = `
          <div>
            <strong>${escapeHtml(item.itemName)}</strong>
            <span>${item.type === 'equipment' ? `${escapeHtml(item.unitNumber)}번` : `${escapeHtml(item.quantity)}개`}</span>
          </div>
          <button type="button" data-cart-remove-index="${index}">삭제</button>
        `;
        list.appendChild(card);
      });
      submitButton.disabled = false;
      syncSelectOptions();
    };

    document.addEventListener('click', (event) => {
      const equipmentButton = event.target.closest('[data-cart-add]');
      if (equipmentButton) {
        const source = equipmentButton.closest('[data-cart-source]');
        const select = source?.querySelector('[data-cart-unit-select]');
        const option = select?.selectedOptions?.[0];
        if (!select || !option || select.disabled || option.disabled || option.dataset.unitStatus !== 'available') {
          showRentalAlert('담을 수 있는 물품 번호가 없습니다.');
          return;
        }
        const unitId = option.value;
        if (cart.some((item) => item.type === 'equipment' && item.unitId === unitId)) {
          showRentalAlert('이미 대여 리스트에 담긴 물품 번호입니다.');
          return;
        }
        cart.push({ type: 'equipment', unitId, itemName: option.dataset.itemName || '물품', unitNumber: option.dataset.unitNumber || '' });
        renderCart();
        return;
      }

      const consumableButton = event.target.closest('[data-consumable-cart-add]');
      if (!consumableButton) return;
      const source = consumableButton.closest('[data-consumable-source]');
      const qtyInput = source?.querySelector('[data-consumable-quantity]');
      const quantity = Number(qtyInput?.value || 0);
      const max = Number(consumableButton.dataset.currentQuantity || 0);
      if (!quantity || quantity < 1) {
        showRentalAlert('지급 수량을 1개 이상 입력해주세요.');
        return;
      }
      const currentInCart = cart
        .filter((item) => item.type === 'consumable' && item.itemId === consumableButton.dataset.itemId)
        .reduce((sum, item) => sum + Number(item.quantity || 0), 0);
      if (currentInCart + quantity > max) {
        showRentalAlert(`현재 수량보다 많이 담을 수 없습니다. 현재 수량: ${max}개`);
        return;
      }
      cart.push({
        type: 'consumable',
        itemId: consumableButton.dataset.itemId,
        itemName: consumableButton.dataset.itemName || '소모품',
        quantity,
      });
      renderCart();
    });

    list.addEventListener('click', (event) => {
      const removeButton = event.target.closest('[data-cart-remove-index]');
      if (!removeButton) return;
      const index = Number(removeButton.dataset.cartRemoveIndex);
      if (Number.isInteger(index) && index >= 0) cart.splice(index, 1);
      renderCart();
    });

    form.addEventListener('submit', (event) => {
      if (!cart.length) {
        event.preventDefault();
        showRentalAlert('대여 리스트에 물품을 먼저 담아주세요.');
        return;
      }
      if (form.dataset.formLoadingActive === '1') {
        event.preventDefault();
        return;
      }
      setFormLoading(form, '처리 중...', submitButton);
    });

    document.addEventListener('rental:item-panel-updated', syncSelectOptions);
    renderCart();
  }


  function setupReturnCart() {
    const form = document.querySelector('[data-return-cart-form]');
    const list = document.querySelector('[data-return-cart-list]');
    const hiddenFields = document.querySelector('[data-return-hidden-fields]');
    const count = document.querySelector('[data-return-cart-count]');
    const submitButton = document.querySelector('[data-return-cart-submit]');
    if (!form || !list || !hiddenFields || !count || !submitButton) return;

    const cart = [];
    const getSelectedRentalIds = () => new Set(cart.map((item) => item.rentalId));

    const syncSelectOptions = () => {
      const selectedRentalIds = getSelectedRentalIds();
      document.querySelectorAll('[data-return-rental-select]').forEach((select) => {
        let firstAvailableOption = null;
        Array.from(select.options).forEach((option) => {
          const isAlreadyInCart = selectedRentalIds.has(option.value);
          option.disabled = isAlreadyInCart;
          if (!isAlreadyInCart && !firstAvailableOption) firstAvailableOption = option;
        });
        if (select.selectedOptions[0]?.disabled && firstAvailableOption) select.value = firstAvailableOption.value;
        const hasAvailable = Boolean(firstAvailableOption);
        select.disabled = !hasAvailable;
        const addButton = select.closest('[data-return-source]')?.querySelector('[data-return-cart-add]');
        if (addButton) addButton.disabled = !hasAvailable;
      });
    };

    const renderCart = () => {
      count.textContent = `${cart.length}개`;
      hiddenFields.innerHTML = '';
      list.innerHTML = '';
      if (!cart.length) {
        list.innerHTML = '<p class="empty-state cart-empty">아직 담긴 물품이 없습니다.</p>';
        submitButton.disabled = true;
        syncSelectOptions();
        return;
      }

      cart.forEach((item, index) => {
        hiddenFields.insertAdjacentHTML('beforeend', `<input type="hidden" name="return_rental_ids" value="${escapeHtml(item.rentalId)}"><input type="hidden" name="return_statuses" value="${escapeHtml(item.status)}">`);
        const card = document.createElement('div');
        card.className = 'cart-selected-card';
        card.innerHTML = `
          <div>
            <strong>${escapeHtml(item.itemName)}</strong>
            <span>${escapeHtml(item.unitNumber)}번 · ${escapeHtml(item.statusLabel)}</span>
          </div>
          <button type="button" data-return-cart-remove-index="${index}">삭제</button>
        `;
        list.appendChild(card);
      });
      submitButton.disabled = false;
      syncSelectOptions();
    };

    document.addEventListener('click', (event) => {
      const addButton = event.target.closest('[data-return-cart-add]');
      if (!addButton) return;
      const source = addButton.closest('[data-return-source]');
      const rentalSelect = source?.querySelector('[data-return-rental-select]');
      const rentalOption = rentalSelect?.selectedOptions?.[0];
      const statusSelect = source?.querySelector('[data-return-status-select]');
      const statusOption = statusSelect?.selectedOptions?.[0];
      if (!rentalSelect || !rentalOption || rentalSelect.disabled || rentalOption.disabled) {
        showRentalAlert('담을 수 있는 반납 물품이 없습니다.');
        return;
      }
      const rentalId = rentalOption.value;
      if (cart.some((item) => item.rentalId === rentalId)) {
        showRentalAlert('이미 반납 리스트에 담긴 물품입니다.');
        return;
      }
      cart.push({
        rentalId,
        itemName: rentalOption.dataset.itemName || '물품',
        unitNumber: rentalOption.dataset.unitNumber || '',
        dueDate: rentalOption.dataset.dueDate || '',
        status: statusOption?.value || 'normal',
        statusLabel: statusOption?.textContent || '정상 반납',
      });
      renderCart();
    });

    list.addEventListener('click', (event) => {
      const removeButton = event.target.closest('[data-return-cart-remove-index]');
      if (!removeButton) return;
      const index = Number(removeButton.dataset.returnCartRemoveIndex);
      if (Number.isInteger(index) && index >= 0) cart.splice(index, 1);
      renderCart();
    });

    form.addEventListener('submit', (event) => {
      if (!cart.length) {
        event.preventDefault();
        showRentalAlert('반납 리스트에 물품을 먼저 담아주세요.');
        return;
      }
      if (form.dataset.formLoadingActive === '1') {
        event.preventDefault();
        return;
      }
      setFormLoading(form, '반납 처리 중...', submitButton);
    });

    document.addEventListener('rental:item-panel-updated', syncSelectOptions);
    renderCart();
  }

  setupStudentAutocomplete();
  setupPhoneStepLoading();
  setupRentalItemPartialSearch();
  setupSelectedItemPanel();
  setupRentalCart();
  setupReturnCart();
})();
