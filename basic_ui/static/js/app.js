(function () {
  const toggle = document.getElementById('drawer-toggle');
  const drawer = document.getElementById('drawer');
  const conversation = document.getElementById('conversation');
  const messages = document.getElementById('messages');

  toggle.addEventListener('click', function () {
    const open = drawer.classList.toggle('open');
    toggle.classList.toggle('active', open);
    toggle.setAttribute('aria-expanded', String(open));
  });

  function scrollToEnd() {
    conversation.scrollTop = conversation.scrollHeight;
  }

  function composerBox() {
    return document.querySelector('#composer textarea');
  }

  function focusComposer() {
    const box = composerBox();
    if (box && !box.matches(':disabled')) box.focus();
  }

  function fit(box) {
    box.style.height = 'auto';
    const border = box.offsetHeight - box.clientHeight;
    const max = parseFloat(getComputedStyle(box).maxHeight);
    box.style.height = Math.min(box.scrollHeight + border, max) + 'px';
  }

  function systemMessage(text, kind) {
    const div = document.createElement('div');
    div.className = 'message message-system message-' + kind;
    div.textContent = text;
    messages.appendChild(div);
  }

  function markUnsent() {
    const pending = document.getElementById('pending-user');
    if (!pending) return;
    pending.removeAttribute('id');
    pending.classList.add('message-unsent');
    const seq = pending.querySelector('.message-seq');
    if (seq) seq.textContent = 'Not sent';
  }

  function fail(text) {
    for (const el of document.querySelectorAll('#pending-reply, #pending-memory')) {
      el.remove();
    }
    markUnsent();
    systemMessage(text, 'error');
    const fieldset = document.querySelector('#composer fieldset');
    if (fieldset) fieldset.disabled = false;
    scrollToEnd();
    focusComposer();
  }

  function formData(el) {
    if (el instanceof HTMLFormElement) return new FormData(el);
    const data = new FormData();
    const fields = el.matches('input, select, textarea')
      ? [el]
      : el.querySelectorAll('input, select, textarea');
    for (const field of fields) {
      if (!field.name) continue;
      if (field.type === 'checkbox' && !field.checked) continue;
      data.append(field.name, field.value);
    }
    return data;
  }

  function setBusy(controls, on) {
    controls.classList.toggle('busy', on);
    for (const field of controls.querySelectorAll('select, input')) {
      if (on && !field.disabled) {
        field.disabled = true;
        field.dataset.busy = 'true';
      } else if (!on && field.dataset.busy) {
        field.disabled = false;
        delete field.dataset.busy;
      }
    }
  }

  function apply(html) {
    const page = document.createElement('template');
    page.innerHTML = html;
    for (const piece of page.content.children) {
      if (!(piece instanceof HTMLTemplateElement) || !piece.dataset.target) continue;
      for (const target of document.querySelectorAll(piece.dataset.target)) {
        const swap = piece.dataset.swap;
        if (swap === 'append') target.append(piece.content.cloneNode(true));
        else if (swap === 'replace') target.replaceWith(piece.content.cloneNode(true));
        else if (swap === 'remove') target.remove();
      }
    }
    const box = composerBox();
    if (box) fit(box);
    scrollToEnd();
    focusComposer();
    for (const el of document.querySelectorAll('[data-post-on="arrive"]')) {
      el.removeAttribute('data-post-on');
      post(el);
    }
  }

  async function post(el) {
    const controls = el.closest('#drawer-controls');
    const body = formData(el);
    if (controls) setBusy(controls, true);
    let response;
    try {
      response = await fetch(el.dataset.post, {
        method: 'POST',
        headers: { 'X-Basic-UI': '1' },
        body: body,
      });
    } catch (error) {
      if (controls) setBusy(controls, false);
      fail("Your agent isn't responding. If its session ended, start it again, " +
           'then reload this page.');
      return;
    }
    if (controls && controls.isConnected) setBusy(controls, false);
    if (response.status === 204) return;
    const type = response.headers.get('Content-Type') || '';
    if (type.startsWith('text/html')) {
      apply(await response.text());
      if (!response.ok) markUnsent();
      return;
    }
    fail('Something went wrong. The terminal shows the details.');
  }

  document.addEventListener('submit', function (e) {
    const form = e.target;
    if (!(form instanceof HTMLFormElement) || !form.dataset.post) return;
    e.preventDefault();
    const box = form.querySelector('textarea');
    if (box && !box.value.trim()) return;
    post(form);
    const fieldset = form.querySelector('fieldset');
    if (fieldset) fieldset.disabled = true;
  });

  document.addEventListener('change', function (e) {
    const field = e.target;
    if (field instanceof Element && field.matches('select[data-post], input[data-post]')) {
      post(field);
    }
  });

  document.addEventListener('click', function (e) {
    const button = e.target instanceof Element && e.target.closest('button[data-post]');
    if (button) post(button);
  });

  document.addEventListener('input', function (e) {
    if (e.target === composerBox()) fit(e.target);
  });

  document.addEventListener('keydown', function (e) {
    const box = composerBox();
    if (e.target !== box || e.key !== 'Enter' || e.shiftKey) return;
    e.preventDefault();
    if (!box.matches(':disabled') && box.value.trim()) box.form.requestSubmit();
  });

  const events = new EventSource('/events');
  events.addEventListener('narration', function (e) {
    const line = document.querySelector('#pending-reply .pending-text');
    if (line) line.textContent = JSON.parse(e.data).text;
  });

  scrollToEnd();
  focusComposer();
})();
