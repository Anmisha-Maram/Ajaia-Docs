'use strict';
const $app = document.getElementById('app');
const $toast = document.getElementById('toast');
let me = null;
let config = { supportedUploads: ['.txt', '.md', '.docx'], maxUploadMb: 2 };
let cleanupEditor = null;

// ---------- helpers ----------
function h(tag, props = {}, ...children) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(props)) {
    if (k === 'class') el.className = v;
    else if (k.startsWith('on')) el.addEventListener(k.slice(2), v);
    else if (v !== false && v != null) el.setAttribute(k, v === true ? '' : v);
  }
  for (const c of children.flat()) if (c != null) el.append(c.nodeType ? c : document.createTextNode(c));
  return el;
}

let toastTimer;
function toast(msg, isError = false) {
  $toast.textContent = msg;
  $toast.className = 'show' + (isError ? ' error' : '');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => ($toast.className = ''), 3500);
}

// FastAPI errors look like {detail: "text"} or, for validation, {detail: [{msg: ...}]}.
function errorText(data, status) {
  if (typeof data.detail === 'string') return data.detail;
  if (Array.isArray(data.detail) && data.detail.length) return data.detail.map((d) => d.msg).join('; ');
  return `Request failed (${status})`;
}

async function api(path, { method = 'GET', body, form, keepalive } = {}) {
  const res = await fetch('/api' + path, {
    method, keepalive,
    headers: body ? { 'content-type': 'application/json' } : undefined,
    body: form ?? (body ? JSON.stringify(body) : undefined),
  });
  let data = {};
  try { data = await res.json(); } catch { /* empty body */ }
  if (!res.ok) {
    if (res.status === 401 && me) { me = null; render(); }
    const err = new Error(errorText(data, res.status));
    err.status = res.status;
    throw err;
  }
  return data;
}

const fmtDate = (s) => new Date(s).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' });

// ---------- views ----------
function loginView() {
  const err = h('div', { class: 'error', role: 'alert' });
  const email = h('input', { type: 'email', placeholder: 'Email', required: true, autocomplete: 'username', 'aria-label': 'Email' });
  const pw = h('input', { type: 'password', placeholder: 'Password', required: true, autocomplete: 'current-password', 'aria-label': 'Password' });
  const submit = async (e) => {
    e?.preventDefault();
    err.textContent = '';
    try {
      me = await api('/login', { method: 'POST', body: { email: email.value, password: pw.value } });
      location.hash = '#/';
      render();
    } catch (ex) { err.textContent = ex.message; }
  };
  const demo = (e) => h('button', { type: 'button', onclick: () => { email.value = e; pw.value = 'ajaia-demo'; submit(); } }, e.split('@')[0]);
  return h('div', { class: 'login' },
    h('h1', {}, 'Ajaia Docs'),
    h('div', { class: 'muted' }, 'Lightweight collaborative documents'),
    h('form', { onsubmit: submit }, email, pw, err, h('button', { class: 'primary', type: 'submit' }, 'Sign in')),
    h('div', { class: 'demo-users' }, 'Demo accounts (password ', h('code', {}, 'ajaia-demo'), '): ',
      demo('alice@ajaia.test'), demo('bob@ajaia.test'), demo('carol@ajaia.test')));
}

function topbar() {
  return h('div', { class: 'topbar' },
    h('span', { class: 'brand', onclick: () => (location.hash = '#/') }, 'Ajaia Docs'),
    h('span', { class: 'spacer' }),
    h('span', { class: 'muted' }, `${me.name} · ${me.email}`),
    h('button', { onclick: async () => { await api('/logout', { method: 'POST' }); me = null; render(); } }, 'Sign out'));
}

async function dashboardView() {
  const list = h('div', {}, h('div', { class: 'muted' }, 'Loading…'));
  const fileInput = h('input', { type: 'file', accept: config.supportedUploads.join(','), hidden: true });
  fileInput.addEventListener('change', async () => {
    const file = fileInput.files[0];
    fileInput.value = '';
    if (!file) return;
    const form = new FormData();
    form.append('file', file);
    try {
      const { id } = await api('/import', { method: 'POST', form });
      toast('Imported as a new document');
      location.hash = `#/doc/${id}`;
    } catch (ex) { toast(ex.message, true); }
  });

  const newDoc = async () => {
    try { const { id } = await api('/docs', { method: 'POST', body: {} }); location.hash = `#/doc/${id}`; }
    catch (ex) { toast(ex.message, true); }
  };

  const row = (d) => h('li', { tabindex: 0, onclick: () => (location.hash = `#/doc/${d.id}`),
      onkeydown: (e) => e.key === 'Enter' && (location.hash = `#/doc/${d.id}`) },
    h('span', { class: 'doc-title' }, d.title),
    d.role === 'owner'
      ? h('span', { class: 'badge' }, 'Owned by you')
      : h('span', { class: 'badge shared' }, `Shared by ${d.owner_name}`),
    d.role === 'viewer' ? h('span', { class: 'badge viewer' }, 'View only') : null,
    h('span', { class: 'muted' }, fmtDate(d.updated_at)));

  const section = (title, docs, emptyMsg) => h('div', {},
    h('h2', { class: 'section-title' }, title),
    docs.length ? h('ul', { class: 'doc-list' }, docs.map(row)) : h('div', { class: 'empty' }, emptyMsg));

  const el = h('div', {}, topbar(), h('div', { class: 'container' },
    h('div', { class: 'actions' },
      h('button', { class: 'primary', onclick: newDoc }, '+ New document'),
      h('button', { onclick: () => fileInput.click() }, 'Upload file'), fileInput),
    h('p', { class: 'muted hint' }, `Upload supports ${config.supportedUploads.join(', ')} (max ${config.maxUploadMb} MB). The file becomes a new editable document.`),
    list));
  try {
    const { owned, shared } = await api('/docs');
    list.replaceChildren(
      section('My documents', owned, 'No documents yet. Create one or upload a file.'),
      section('Shared with me', shared, 'Nothing has been shared with you yet.'));
  } catch (ex) { list.replaceChildren(h('div', { class: 'error' }, ex.message)); }
  return el;
}

async function editorView(id) {
  let doc;
  try { doc = await api(`/docs/${id}`); }
  catch (ex) {
    return h('div', {}, topbar(), h('div', { class: 'container' },
      h('div', { class: 'empty' }, ex.status === 404 ? 'This document does not exist or is not shared with you.' : ex.message),
      h('p', {}, h('button', { onclick: () => (location.hash = '#/') }, '← Back to documents'))));
  }
  const canEdit = doc.role !== 'viewer';
  let version = doc.version;
  let dirty = false, saving = false, timer = null, conflict = false;

  const state = h('span', { class: 'save-state', 'aria-live': 'polite' }, canEdit ? 'Saved' : '');
  const setState = (t, err = false) => { state.textContent = t; state.className = 'save-state' + (err ? ' err' : ''); };

  const titleInput = h('input', { class: 'title-input', type: 'text', value: doc.title, maxlength: 120, 'aria-label': 'Document title', disabled: !canEdit });
  let savedTitle = doc.title;

  const toolbar = h('div', { id: 'toolbar' },
    h('span', { class: 'ql-formats' },
      h('select', { class: 'ql-header' }, h('option', { value: '1' }, 'Heading 1'), h('option', { value: '2' }, 'Heading 2'), h('option', { value: '3' }, 'Heading 3'), h('option', { selected: true }, 'Normal'))),
    h('span', { class: 'ql-formats' },
      h('button', { class: 'ql-bold', title: 'Bold' }), h('button', { class: 'ql-italic', title: 'Italic' }), h('button', { class: 'ql-underline', title: 'Underline' })),
    h('span', { class: 'ql-formats' },
      h('button', { class: 'ql-list', value: 'ordered', title: 'Numbered list' }), h('button', { class: 'ql-list', value: 'bullet', title: 'Bulleted list' })),
    h('span', { class: 'ql-formats' }, h('button', { class: 'ql-clean', title: 'Clear formatting' })));
  const box = h('div', { id: 'editor-box' });

  let quill;

  async function save() {
    if (!canEdit || saving || conflict || !quill) return;
    clearTimeout(timer);
    const titleChanged = titleInput.value.trim() !== savedTitle;
    if (!dirty && !titleChanged) return;
    if (titleChanged && !titleInput.value.trim()) { toast('Title cannot be empty.', true); titleInput.value = savedTitle; if (!dirty) return; }
    saving = true; setState('Saving…');
    const body = { base_version: version };
    if (dirty) body.html = quill.getSemanticHTML();
    if (titleInput.value.trim() !== savedTitle) body.title = titleInput.value.trim();
    const wasDirty = dirty;
    dirty = false;
    try {
      const r = await api(`/docs/${id}`, { method: 'PUT', body });
      version = r.version; savedTitle = r.title; titleInput.value = r.title;
      setState('Saved');
    } catch (ex) {
      dirty = wasDirty || dirty;
      if (ex.status === 409) { conflict = true; setState('Conflict', true); toast(ex.message, true); }
      else { setState('Not saved', true); toast(ex.message, true); }
    } finally {
      saving = false;
      if (dirty && !conflict) timer = setTimeout(save, 1500);
    }
  }
  const schedule = () => { dirty = true; setState('Unsaved changes'); clearTimeout(timer); timer = setTimeout(save, 1200); };

  const shareBtn = doc.role === 'owner' ? h('button', { onclick: () => openShareDialog(id, doc.title) }, 'Share') : null;
  const delBtn = doc.role === 'owner' ? h('button', { class: 'danger', onclick: async () => {
    if (!confirm(`Delete "${titleInput.value}"? This cannot be undone.`)) return;
    try { dirty = false; clearTimeout(timer); await api(`/docs/${id}`, { method: 'DELETE' }); location.hash = '#/'; }
    catch (ex) { toast(ex.message, true); }
  } }, 'Delete') : null;

  const el = h('div', {}, topbar(), h('div', { class: 'editor-wrap' },
    h('div', { class: 'title-row' },
      h('button', { onclick: async () => { await save(); location.hash = '#/'; } }, '←'),
      titleInput, state, shareBtn, delBtn),
    h('div', { class: 'muted', style: 'margin-bottom:10px' },
      doc.role === 'owner' ? 'You own this document' : `Owned by ${doc.owner_name} · you can ${doc.role === 'editor' ? 'edit' : 'only view'}`),
    !canEdit ? h('div', { class: 'readonly-banner' }, 'View only — ask the owner for edit access.') : null,
    toolbar, box));

  // Quill is created in mount(), after the elements are attached to the page.
  el.mount = () => {
    quill = new Quill(box, { theme: 'snow', readOnly: !canEdit, modules: { toolbar }, placeholder: canEdit ? 'Start writing…' : '' });
    quill.setContents(quill.clipboard.convert({ html: doc.html }), 'silent');
    if (!canEdit) toolbar.style.display = 'none';
    quill.on('text-change', (_d, _o, source) => { if (source === 'user') schedule(); });
  };

  titleInput.addEventListener('keydown', (e) => e.key === 'Enter' && titleInput.blur());
  titleInput.addEventListener('blur', save);
  const onKey = (e) => { if ((e.ctrlKey || e.metaKey) && e.key === 's') { e.preventDefault(); save(); } };
  const onUnload = (e) => { if (dirty) { e.preventDefault(); e.returnValue = ''; } };
  document.addEventListener('keydown', onKey);
  window.addEventListener('beforeunload', onUnload);
  cleanupEditor = () => {
    document.removeEventListener('keydown', onKey);
    window.removeEventListener('beforeunload', onUnload);
    if (dirty && !conflict && quill) { // best-effort flush when navigating away
      api(`/docs/${id}`, { method: 'PUT', keepalive: true, body: { html: quill.getSemanticHTML(), base_version: version } }).catch(() => {});
    }
    clearTimeout(timer);
  };
  return el;
}

async function openShareDialog(id, title) {
  const dlg = h('dialog');
  const err = h('div', { class: 'error', role: 'alert' });
  const listEl = h('ul', { class: 'share-list' });
  const email = h('input', { type: 'email', placeholder: 'Teammate email (e.g. bob@ajaia.test)', 'aria-label': 'Email to share with' });
  const role = h('select', { 'aria-label': 'Permission' }, h('option', { value: 'editor' }, 'Can edit'), h('option', { value: 'viewer' }, 'Can view'));

  async function refresh() {
    try {
      const { shares } = await api(`/docs/${id}/shares`);
      listEl.replaceChildren(...(shares.length ? shares.map((s) => h('li', {},
        h('span', { class: 'who' }, `${s.name} `, h('span', { class: 'muted' }, s.email)),
        h('span', { class: 'badge' }, s.role === 'editor' ? 'Can edit' : 'Can view'),
        h('button', { class: 'danger', onclick: async () => {
          try { await api(`/docs/${id}/shares/${s.user_id}`, { method: 'DELETE' }); refresh(); } catch (ex) { err.textContent = ex.message; }
        } }, 'Remove'))) : [h('li', { class: 'muted' }, 'Not shared with anyone yet.')]));
    } catch (ex) { err.textContent = ex.message; }
  }
  const add = async (e) => {
    e.preventDefault(); err.textContent = '';
    try { await api(`/docs/${id}/shares`, { method: 'POST', body: { email: email.value, role: role.value } }); email.value = ''; refresh(); }
    catch (ex) { err.textContent = ex.message; }
  };
  dlg.append(h('h2', {}, `Share "${title}"`),
    h('form', { class: 'share-form', onsubmit: add }, email, role, h('button', { class: 'primary', type: 'submit' }, 'Share')),
    err, listEl,
    h('div', { class: 'dialog-actions' }, h('button', { onclick: () => dlg.close() }, 'Done')));
  dlg.addEventListener('close', () => dlg.remove());
  document.body.append(dlg);
  dlg.showModal();
  refresh();
}

// ---------- routing ----------
async function render() {
  if (cleanupEditor) { cleanupEditor(); cleanupEditor = null; }
  if (!me) { $app.replaceChildren(loginView()); return; }
  const m = location.hash.match(/^#\/doc\/(\d+)$/);
  const view = m ? await editorView(Number(m[1])) : await dashboardView();
  $app.replaceChildren(view);
  view.mount?.();
}

window.addEventListener('hashchange', render);
(async function init() {
  try { config = await api('/config'); } catch { /* defaults */ }
  try { me = await api('/me'); } catch { me = null; }
  render();
})();