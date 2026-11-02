const $ = id => document.getElementById(id);
let sessionId = localStorage.getItem('div-session');
let draftRevision = 0, conflict = false, listOffset = 0, switching = false;
let timer, questionsKey = '', busy = false;
let draftSession = null, draftDirty = false, draftSaving = false, view = 'edit', latestData = null;
let saveTimer, savePromise, selectedPassage = null, revisionText = '', revising = false, submitting = false;
const emptyDocument = $('document').innerHTML;
const editor = window.createDocumentEditor({onChange:draftChanged, onSelectAI:selectForAI, onSave:() => saveDraft().catch(showError)});
function draftKey(id = sessionId) { return `div-draft-${id}`; }
function cachedDraft() {return JSON.stringify({version:3, base_revision:draftRevision, dirty:draftDirty, markdown:editor.markdown(), document:editor.json()});}
function decodeDraft(value, fallback = '') {
  if (value == null) return {markdown:fallback};
  try {const data = JSON.parse(value); if(data.version === 2 || data.version === 3) return data;} catch {}
  return {markdown:value};
}
function draftChanged() {
  draftDirty = true;
  try {localStorage.setItem(draftKey(), cachedDraft());} catch {showError('브라우저 임시 저장 공간이 부족합니다. 문서를 다운로드해 주세요.');}
  $('draft-status').textContent = '브라우저 임시 보관 · 서버 저장 전';
  $('draft-count').textContent = `${editor.count().toLocaleString()} / 50,000자`;
  clearTimeout(saveTimer); if (!conflict) saveTimer = setTimeout(() => saveDraft().catch(showError), 1200);
}
function setView(next) {
  view = next;
  $('draft-pane').hidden = view !== 'edit'; $('document').hidden = view === 'edit';
  $('editor-toolbar').hidden = view !== 'edit';
  $('table-tools').hidden = true;
  $('result-actions').hidden = view !== 'result' || !latestData?.markdown;
  editor.hideMenus();
  for (const name of ['edit', 'preview', 'result']) {
    $(`${name}-tab`).classList.toggle('selected', view === name);
    $(`${name}-tab`).setAttribute('aria-pressed', String(view === name));
  }
  $('document').classList.toggle('tiptap', view === 'preview');
  $('document').innerHTML = (view === 'preview' ? editor.html() : latestData?.html) || emptyDocument;
  if (view === 'edit') editor.refresh();
}
async function saveDraft() {
  clearTimeout(saveTimer);
  if (savePromise) {await savePromise; if (!draftDirty) return;}
  if (!sessionId) return;
  if (conflict) throw new Error('충돌을 해결하거나 사본으로 저장하세요.');
  draftSaving = true; $('save-draft').disabled = true;
  const markdown = editor.markdown(), document = editor.json(), saved = JSON.stringify(document);
  savePromise = (async () => {try {
    const data = await api(`/api/sessions/${sessionId}/draft`, {method:'PUT', body:JSON.stringify({markdown, document, base_revision:draftRevision})});
    latestData = {...latestData, ...data};
    draftRevision = data.draft_revision;
    draftDirty = JSON.stringify(editor.json()) !== saved;
    $('draft-status').textContent = draftDirty ? '새 변경사항 · 저장 대기' : '모든 변경사항 저장됨';
    localStorage.setItem(draftKey(), cachedDraft());
  } catch(error) { if (error.status === 409) setConflict(true); $('draft-status').textContent = '저장 실패 · 브라우저에 임시 보관됨'; throw error; }
  finally { draftSaving = false; $('save-draft').disabled = false; savePromise = null; }
  })();
  return savePromise;
}
$('edit-tab').onclick = () => setView('edit');
$('result-tab').onclick = () => setView('result');
$('preview-tab').onclick = () => setView('preview');
$('append-result').onclick = () => {if(latestData?.markdown) {setView('edit'); editor.appendMarkdown(latestData.markdown);} };
$('save-draft').onclick = () => saveDraft().catch(showError);
$('download-draft').onclick = () => {
  const url = URL.createObjectURL(new Blob([editor.markdown()], {type:'text/markdown;charset=utf-8'}));
  const link = document.createElement('a'); link.href = url; link.download = 'vibe-draft.md'; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
};
function selectForAI(selection) {
  if (revising) return;
  selectedPassage = selection; revisionText = '';
  $('selected-text').textContent = selection.text;
  $('selection-panel').hidden = false; $('revision-result').hidden = true;
  $('revision-status').textContent = '선택한 문장만 수정합니다. 결과를 확인한 뒤 반영하세요.';
  $('revise-instruction').value = '자연스럽고 명확한 문장으로 다듬어 주세요.';
  $('revise-instruction').focus(); editor.hideMenus();
}
$('close-selection').onclick = () => {if(!revising) {$('selection-panel').hidden = true; selectedPassage = null;} };
$('discard-revision').onclick = () => {$('revision-result').hidden = true; revisionText = ''; $('revision-status').textContent = '수정안을 버렸습니다. 원문은 유지됩니다.';};
document.querySelectorAll('[data-revise]').forEach(button => button.onclick = () => {$('revise-instruction').value = button.dataset.revise;});
$('revise-form').onsubmit = async event => {
  event.preventDefault(); if(revising || !selectedPassage) return;
  revising = true; $('request-revision').disabled = true; $('close-selection').disabled = true;
  $('revision-result').hidden = true; $('revision-status').textContent = '수정안을 작성하고 있습니다… 문서는 계속 편집할 수 있습니다.';
  try {
    const data = await api(`/api/sessions/${sessionId}/revise`, {method:'POST', body:JSON.stringify({selection:selectedPassage.text, instruction:$('revise-instruction').value, context:editor.text().slice(0,12000)})});
    revisionText = data.text; $('revision-preview').innerHTML = data.html;
    $('revision-result').hidden = false; $('revision-status').textContent = '수정안을 확인하세요. 반영 전에는 문서가 바뀌지 않습니다.';
  } catch(error) {$('revision-status').textContent = error.message;}
  finally {revising = false; $('request-revision').disabled = false; $('close-selection').disabled = false;}
};
$('apply-revision').onclick = () => {
  if (!selectedPassage || !revisionText) return;
  if (!editor.replaceSelection(selectedPassage, revisionText)) {
    $('revision-status').textContent = '수정안을 만드는 동안 문서가 바뀌었습니다. 적용할 문장을 다시 선택해 요청하세요.'; return;
  }
  $('revision-result').hidden = true; $('revision-status').textContent = '문서에 반영했습니다. Ctrl+Z로 되돌릴 수 있습니다.';
  selectedPassage = null; setView('edit');
};
async function api(path, options = {}) {
  const response = await fetch(path, {...options, headers: {'Content-Type': 'application/json'}});
  if (!response.ok) {
    let data; try { data = await response.json(); } catch { data = {}; }
    const error = new Error(typeof data.detail === 'string' ? data.detail : `요청 실패 (${response.status})`);
    error.status = response.status; throw error;
  }
  return response.json();
}
function showError(error) { $('error').hidden = false; $('error').textContent = error.message || error; }
function render(data) {
  latestData = data;
  if (draftSession !== data.id) {
    draftSession = data.id;
    const local = localStorage.getItem(draftKey(data.id));
    const restored = decodeDraft(local, data.draft || '');
    draftRevision = data.draft_revision;
    const useLocal = local != null && restored.dirty !== false;
    editor.load(useLocal ? restored.markdown : data.draft, useLocal ? restored.document : data.draft_document);
    draftDirty = useLocal && (restored.markdown !== data.draft || JSON.stringify(restored.document) !== JSON.stringify(data.draft_document));
    setConflict(draftDirty && restored.base_revision !== draftRevision);
    $('draft-status').textContent = conflict ? '다른 버전의 초안입니다. 복구 방법을 선택하세요.' : draftDirty ? '브라우저 초안 복구됨 · 서버 저장 전' : '모든 변경사항 저장됨';
    $('draft-count').textContent = `${editor.count().toLocaleString()} / 50,000자`;
    if (draftDirty && !conflict) {clearTimeout(saveTimer); saveTimer = setTimeout(() => saveDraft().catch(showError),1200);}
    view = 'edit';
  }
  busy = data.status === 'running';
  $('save-draft').disabled = draftSaving;
  $('include-draft').disabled = busy;
  $('status').textContent = busy ? '● 기획 작업 중' : data.status === 'error' ? '오류 확인 필요' : '● 입력 대기';
  $('send').disabled = busy; $('prompt').disabled = busy; $('new').disabled = busy;
  $('stage').textContent = ({idea_structuring:'아이디어 정리',planning:'기획서 작성',research:'자료 조사'})[data.stage] || '어시스턴트';
  $('error').hidden = !data.error; if (data.error) showError(data.error);
  const messages = $('messages'); const atBottom = messages.scrollHeight - messages.scrollTop - messages.clientHeight < 70;
  messages.replaceChildren();
  for (const message of data.messages) {
    const item = document.createElement('div'); item.className = `message ${message.role}`;
    const name = document.createElement('small'); name.textContent = message.role === 'human' ? '나' : 'DIV ASSISTANT';
    item.append(name, document.createTextNode(typeof message.content === 'string' ? message.content : JSON.stringify(message.content))); messages.append(item);
  }
  if (busy) { const item = document.createElement('div'); item.className = 'message'; item.textContent = '생각을 정리하고 있습니다… 로컬 모델은 시간이 걸릴 수 있어요.'; messages.append(item); }
  if (atBottom) messages.scrollTop = messages.scrollHeight;
  setView(view);
  $('download').hidden = !data.markdown; $('download').href = `/api/sessions/${sessionId}/download`;
  $('evidence').replaceChildren();
  for (const section of data.sections || []) for (const evidence of section.evidence || []) {
    const p = document.createElement('p'); p.textContent = typeof evidence === 'string' ? evidence : JSON.stringify(evidence); $('evidence').append(p);
  }
  if (!$('evidence').childElementCount) $('evidence').textContent = '문서 작성 중 수집한 근거가 여기에 표시됩니다.';
  const questions = Array.isArray(data.questions) ? data.questions : [];
  $('questions').hidden = !questions.length; $('chat').hidden = !!questions.length;
  if (JSON.stringify(questions) !== questionsKey) {
    questionsKey = JSON.stringify(questions); $('questions').replaceChildren();
    questions.forEach((q, i) => {
      const label = document.createElement('label'); label.textContent = q.question;
      const select = document.createElement('select'); select.name = String(q.current_section); select.dataset.question = q.question;
      for (const option of q.options || []) { const opt = document.createElement('option'); opt.textContent = option.label; opt.value = option.value; select.append(opt); }
      const extra = document.createElement('textarea'); extra.placeholder = q.guide_text || '직접 입력'; extra.id = `answer-${i}`;
      const toggle = () => { extra.hidden = select.value !== '사용자 입력' && select.options.length > 0; extra.required = !extra.hidden; };
      select.addEventListener('change', toggle); toggle(); label.append(select, extra); $('questions').append(label);
    });
    const button = document.createElement('button'); button.className = 'primary'; button.textContent = '답변 제출'; $('questions').append(button);
  }
  $('questions').querySelectorAll('button,select,textarea').forEach(el => el.disabled = busy);
}
async function poll() {
  clearTimeout(timer);
  const requestedId = sessionId;
  try { const data = await api(`/api/sessions/${requestedId}`); if (requestedId !== sessionId || switching) return; render(data); if (data.status === 'running') timer = setTimeout(poll, 1800); }
  catch (error) { showError(error); if (error.status !== 404) timer = setTimeout(poll, 4000); else {busy = false; $('new').disabled = false;} }
}
async function submit(payload) {
  if (submitting || busy) return;
  submitting = true;
  $('send').disabled = true;
  try {
    if (draftDirty) await saveDraft();
    payload.include_draft = !payload.answers && $('include-draft').checked;
    await api(`/api/sessions/${sessionId}/messages`, {method:'POST', body:JSON.stringify(payload)}); $('prompt').value = ''; await poll();
  }
  catch (error) { showError(error); $('send').disabled = busy; }
  finally {submitting = false;}
}
$('chat').addEventListener('submit', event => {event.preventDefault(); if (!busy) submit({text:$('prompt').value});});
$('prompt').addEventListener('keydown', event => { if(event.key === 'Enter' && !event.shiftKey && !event.isComposing) {event.preventDefault(); $('chat').requestSubmit();} });
$('questions').addEventListener('submit', event => {
  event.preventDefault(); if (busy) return;
  const answers = {};
  $('questions').querySelectorAll('select').forEach((select,i) => {answers[select.name] = {question:select.dataset.question, selected_option:select.selectedOptions[0]?.textContent || '직접 입력', value:$(`answer-${i}`).hidden ? select.value : $(`answer-${i}`).value};});
  submit({answers});
});
async function newSession(recoveredDraft) {
  if (switching || revising || submitting) {showError('AI 요청이 끝나면 새 문서를 시작할 수 있습니다.'); return;}
  if (savePromise) await savePromise;
  if (draftDirty && draftSession === sessionId) await saveDraft();
  clearTimeout(timer); const data = await api('/api/sessions', {method:'POST'});
  sessionId = data.id; localStorage.setItem('div-session',sessionId);
  $('selection-panel').hidden = true; selectedPassage = null; draftSession = null;
  editor.load('', null);
  if (typeof recoveredDraft === 'string') localStorage.setItem(draftKey(), recoveredDraft);
  render(data);
  await loadDocuments(true);
}
$('new').onclick = () => newSession().catch(showError);
async function checkHealth() { $('health').textContent = '연결 확인 중…'; try { const data = await api('/api/health'); $('health').textContent = data.message; } catch(error) { $('health').textContent = error.message; } }
$('check').onclick = checkHealth;
async function init() {
  const config = await api('/api/config'); $('model').textContent = `${config.provider} / ${config.model}`;
  checkHealth();
  await loadDocuments(true);
  if (sessionId) {try {const data = await api(`/api/sessions/${sessionId}`); render(data); if(data.status === 'running') poll(); return;} catch(error) {if(error.status !== 404) throw error;}}
  await newSession(sessionId ? localStorage.getItem(draftKey()) : undefined);
}
function setConflict(value) {
  conflict = value; $('draft-conflict').hidden = !value;
  if (value) clearTimeout(saveTimer);
}
async function openSession(id) {
  if (switching || revising || submitting) throw new Error('AI 요청이 끝난 뒤 문서를 전환하세요.');
  if (savePromise) await savePromise;
  if (draftDirty) await saveDraft();
  const data = await api(`/api/sessions/${id}`);
  clearTimeout(timer); sessionId = id; draftSession = null; questionsKey = '';
  selectedPassage = null; $('selection-panel').hidden = true;
  localStorage.setItem('div-session', id); render(data);
  if (data.status === 'running') poll();
}
async function loadDocuments(reset = false) {
  if (reset) {listOffset = 0; $('document-list').replaceChildren();}
  const rows = await api(`/api/sessions?limit=20&offset=${listOffset}`);
  for (const row of rows) {
    const button = document.createElement('button'); button.textContent = row.title;
    button.onclick = () => openSession(row.id).catch(showError); $('document-list').append(button);
  }
  listOffset += rows.length; $('more-documents').hidden = rows.length < 20;
}
$('more-documents').onclick = () => loadDocuments().catch(showError);
$('refresh-documents').onclick = () => loadDocuments(true).catch(showError);
$('reload-draft').onclick = async () => {
  if (switching || revising || submitting) return;
  switching = true;
  try {
    const data = await api(`/api/sessions/${sessionId}`);
    localStorage.setItem(`div-recovery-${sessionId}-${Date.now()}`, cachedDraft());
    localStorage.removeItem(draftKey()); draftSession = null; render(data);
  } catch(error) {showError(error);} finally {switching = false;}
};
$('copy-draft').onclick = async () => {
  if (switching || revising || submitting) return;
  switching = true;
  const sourceId = sessionId, sourceCache = localStorage.getItem(draftKey());
  const copiedDocument = JSON.stringify(editor.json());
  try {
  const data = await api(`/api/sessions/${sessionId}/copy`, {method:'POST', body:JSON.stringify({markdown:editor.markdown(), document:editor.json(), base_revision:draftRevision})});
  clearTimeout(timer); clearTimeout(saveTimer);
  const changed = JSON.stringify(editor.json()) !== copiedDocument;
  if (changed) localStorage.setItem(draftKey(data.id), JSON.stringify({version:3, base_revision:data.draft_revision, dirty:true, markdown:editor.markdown(), document:editor.json()}));
  if (localStorage.getItem(draftKey(sourceId)) === sourceCache || localStorage.getItem(draftKey(sourceId)) === cachedDraft()) localStorage.removeItem(draftKey(sourceId));
  sessionId = data.id; localStorage.setItem('div-session', sessionId); draftSession = null; render(data);
  await loadDocuments(true);
} catch(error) {showError(error);} finally {switching = false;} };
init().catch(showError);
