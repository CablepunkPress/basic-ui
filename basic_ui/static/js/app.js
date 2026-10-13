(function () {
  // Drawer: open and close
  const toggle = document.getElementById('drawer-toggle');
  const drawer = document.getElementById('drawer');
  toggle.addEventListener('click', function () {
    const open = drawer.classList.toggle('open');
    toggle.classList.toggle('active', open);
    toggle.setAttribute('aria-expanded', String(open));
  });

  const conversation = document.getElementById('conversation');

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

  // The box grows with its text, up to the height set in the stylesheet
  function fit(box) {
    box.style.height = 'auto';
    box.style.height = box.scrollHeight + 'px';
  }

  document.addEventListener('input', function (e) {
    if (e.target === composerBox()) fit(e.target);
  });

  // Enter sends; Shift-Enter makes a new line
  document.addEventListener('keydown', function (e) {
    const box = composerBox();
    if (e.target !== box || e.key !== 'Enter' || e.shiftKey) return;
    e.preventDefault();
    if (!box.matches(':disabled') && box.value.trim()) box.form.requestSubmit();
  });

  // After every update: newest message in view, box ready to type in
  document.body.addEventListener('htmx:after:settle', function () {
    scrollToEnd();
    focusComposer();
  });

  scrollToEnd();
  focusComposer();
})();