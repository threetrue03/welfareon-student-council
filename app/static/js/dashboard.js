(() => {
  const dueDataElement = document.getElementById('due-items-data');
  const borrowedDataElement = document.getElementById('borrowed-items-data');
  const modal = document.getElementById('dueModal');
  const modalTitle = document.getElementById('dueModalTitle');
  const modalBody = document.getElementById('dueModalBody');
  const closeButton = document.getElementById('dueModalClose');
  if (!dueDataElement || !borrowedDataElement || !modal || !modalTitle || !modalBody || !closeButton) return;

  const dueItems = JSON.parse(dueDataElement.textContent || '[]');
  const borrowedItems = JSON.parse(borrowedDataElement.textContent || '[]');
  const groupByDate = (items) => items.reduce((acc, item) => {
    if (!acc[item.date]) acc[item.date] = [];
    acc[item.date].push(item);
    return acc;
  }, {});
  const dueByDate = groupByDate(dueItems);
  const borrowedByDate = groupByDate(borrowedItems);

  const formatDate = (dateString) => {
    const [year, month, day] = dateString.split('-').map(Number);
    return `${year}년 ${month}월 ${day}일`;
  };
  const escapeHtml = (value) => String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');

  const renderRows = (items, emptyText) => {
    if (!items.length) return `<p class="empty-state">${escapeHtml(emptyText)}</p>`;
    return `
      <div class="date-detail-table-wrap">
        <table class="date-detail-table">
          <thead>
            <tr>
              <th>대여 일시</th>
              <th>학생</th>
              <th>물품</th>
              <th>반납 예정일</th>
              <th>근무자</th>
              <th>메모</th>
            </tr>
          </thead>
          <tbody>
            ${items.map((item) => `
              <tr>
                <td>${escapeHtml(item.borrowed_at)}</td>
                <td>${escapeHtml(item.student)}</td>
                <td>${escapeHtml(item.item)}</td>
                <td>${escapeHtml(item.due_date)}</td>
                <td>${escapeHtml(item.worker)}</td>
                <td>${escapeHtml(item.memo)}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>`;
  };

  const openModal = (dateString) => {
    modalTitle.textContent = `${formatDate(dateString)} 상세`;
    modalBody.innerHTML = `
      <section class="date-detail-section">
        <h3>해당 날짜 대여 기록</h3>
        ${renderRows(borrowedByDate[dateString] || [], '이 날짜에 대여한 기록이 없습니다.')}
      </section>
      <section class="date-detail-section">
        <h3>해당 날짜 반납 예정</h3>
        ${renderRows(dueByDate[dateString] || [], '이 날짜에 반납 예정인 물품이 없습니다.')}
      </section>`;
    modal.classList.add('open');
    modal.setAttribute('aria-hidden', 'false');
    closeButton.focus();
  };

  const closeModal = () => {
    modal.classList.remove('open');
    modal.setAttribute('aria-hidden', 'true');
  };
  document.querySelectorAll('.calendar-day').forEach((button) => button.addEventListener('click', () => openModal(button.dataset.date)));
  closeButton.addEventListener('click', closeModal);
  modal.addEventListener('click', (event) => { if (event.target === modal) closeModal(); });
  document.addEventListener('keydown', (event) => { if (event.key === 'Escape' && modal.classList.contains('open')) closeModal(); });
})();


(() => {
  const form = document.getElementById('googleSheetForm');
  if (!form) return;

  const submitButtons = Array.from(form.querySelectorAll('button[type="submit"]'));
  let isSubmitting = false;

  const setLoading = (submitter) => {
    const action = submitter?.value || submitter?.dataset.loadingAction || 'save';

    if (action && submitter?.name === 'action') {
      const hiddenAction = document.createElement('input');
      hiddenAction.type = 'hidden';
      hiddenAction.name = 'action';
      hiddenAction.value = action;
      hiddenAction.dataset.generatedAction = 'true';
      form.appendChild(hiddenAction);
    }

    const title = submitter?.dataset?.loadingTitle || (action === 'sync' ? '오늘 데이터 동기화 중' : action === 'test' ? '연결 테스트 중' : '저장 중...');

    form.classList.add('is-loading');
    submitButtons.forEach((button) => {
      button.disabled = true;
      button.setAttribute('aria-disabled', 'true');
    });
    if (window.WelfareONUi?.setButtonLoading && submitter) {
      window.WelfareONUi.setButtonLoading(submitter, title);
    } else if (submitter) {
      submitter.classList.add('button-loading');
      submitter.dataset.originalText = submitter.textContent;
      submitter.innerHTML = `<span class="button-spinner" aria-hidden="true"></span>${title}`;
    }
  };

  form.addEventListener('submit', (event) => {
    if (isSubmitting) {
      event.preventDefault();
      return;
    }
    isSubmitting = true;
    setLoading(event.submitter);
  });
})();
