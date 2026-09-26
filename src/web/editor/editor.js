import { Editor } from '@tiptap/core';
import StarterKit from '@tiptap/starter-kit';
import { Markdown } from '@tiptap/markdown';
import { TaskList, TaskItem } from '@tiptap/extension-list';
import { TableKit } from '@tiptap/extension-table';
import { Placeholder, CharacterCount } from '@tiptap/extensions';

// Bundled locally: no CDN or frontend server required at runtime.
window.createDocumentEditor = function ({onChange, onSelectAI, onSave}) {
  const host = document.getElementById('draft-editor');
  const menu = document.getElementById('slash-menu');
  const bubble = document.getElementById('selection-tools');
  const blockSelect = document.getElementById('block-type');
  let slash = null, menuIndex = 0, version = 0, loading = false;
  const commands = [
    ['본문', '일반 텍스트', chain => chain.setParagraph()],
    ['제목 1', '큰 제목', chain => chain.toggleHeading({level:1})],
    ['제목 2', '중간 제목', chain => chain.toggleHeading({level:2})],
    ['제목 3', '작은 제목', chain => chain.toggleHeading({level:3})],
    ['글머리 목록', '순서 없는 목록', chain => chain.toggleBulletList()],
    ['번호 목록', '순서 있는 목록', chain => chain.toggleOrderedList()],
    ['체크리스트', '할 일과 완료 상태', chain => chain.toggleTaskList()],
    ['인용', '강조할 문장', chain => chain.toggleBlockquote()],
    ['코드', '코드 블록', chain => chain.toggleCodeBlock()],
    ['구분선', '내용 구분', chain => chain.setHorizontalRule()],
    ['표', '3 × 3 표', chain => chain.insertTable({rows:3, cols:3, withHeaderRow:true})],
  ];
  const editor = new Editor({
    element: host,
    extensions: [
      StarterKit.configure({heading:{levels:[1,2,3]}, link:{openOnClick:false, protocols:['https','http','mailto']}}),
      Markdown, TaskList, TaskItem.configure({nested:true}), TableKit.configure({table:{resizable:true}}),
      Placeholder.configure({placeholder:({node}) => node.type.name === 'heading' ? '제목' : '내용을 입력하거나 / 로 블록을 추가하세요'}),
      CharacterCount.configure({limit:50000}),
    ],
    content:'',
    editorProps:{
      attributes:{'aria-label':'기획서 문서 편집기', role:'textbox', 'aria-multiline':'true', spellcheck:'false'},
      handleKeyDown:(_, event) => {
        if (event.isComposing) return false;
        if ((event.ctrlKey || event.metaKey) && event.key === 's') {event.preventDefault(); onSave(); return true;}
        if (slash && !menu.hidden) {
          if (event.key === 'Escape') {closeMenu(); return true;}
          if (['ArrowDown','ArrowUp'].includes(event.key)) {
            menuIndex = (menuIndex + (event.key === 'ArrowDown' ? 1 : -1) + commands.length) % commands.length;
            highlightMenu(); return true;
          }
          if (event.key === 'Enter') {runSlash(menuIndex); return true;}
        }
        return false;
      },
    },
    onUpdate:() => {version++; if (!loading) onChange(); syncUI(); updateSlash();},
    onSelectionUpdate:() => {syncUI(); updateSlash();},
    onBlur:() => {setTimeout(() => { if (!host.contains(document.activeElement)) closeMenu(); }, 180);},
  });

  function closeMenu() { slash = null; menu.hidden = true; }
  function highlightMenu() {
    [...menu.children].forEach((button, index) => {
      button.classList.toggle('selected', index === menuIndex);
      button.setAttribute('aria-selected', String(index === menuIndex));
    });
    menu.children[menuIndex]?.scrollIntoView({block:'nearest'});
  }
  function updateSlash() {
    const {$from, empty} = editor.state.selection;
    if (!empty || !$from.parent.isTextblock || $from.parent.textContent !== '/' || !editor.isFocused) {closeMenu(); return;}
    slash = {from:$from.start(), to:$from.start() + 1};
    const coords = editor.view.coordsAtPos($from.pos);
    menu.hidden = false;
    menu.style.left = `${Math.min(coords.left, window.innerWidth - 275)}px`;
    menu.style.top = `${Math.max(8, Math.min(coords.bottom + 8, window.innerHeight - 365))}px`;
  }
  function runSlash(index) {
    if (!slash) return;
    const range = {...slash}; closeMenu();
    commands[index][2](editor.chain().focus().deleteRange(range)).run();
  }
  commands.forEach(([label, hint], index) => {
    const button = document.createElement('button'); button.type = 'button'; button.role = 'option';
    const title = document.createElement('strong'); title.textContent = label;
    const small = document.createElement('small'); small.textContent = hint;
    button.append(title, small);
    button.onmousedown = event => event.preventDefault(); button.onclick = () => runSlash(index);
    menu.append(button);
  });

  const actions = {
    bold: c => c.toggleBold(), italic: c => c.toggleItalic(), strike:c => c.toggleStrike(),
    bulletList:c => c.toggleBulletList(), orderedList:c => c.toggleOrderedList(), taskList:c => c.toggleTaskList(),
    blockquote:c => c.toggleBlockquote(), codeBlock:c => c.toggleCodeBlock(), horizontalRule:c => c.setHorizontalRule(),
    table:c => c.insertTable({rows:3, cols:3, withHeaderRow:true}),
    addRow:c => c.addRowAfter(), addColumn:c => c.addColumnAfter(), deleteRow:c => c.deleteRow(),
    deleteColumn:c => c.deleteColumn(), deleteTable:c => c.deleteTable(),
    undo:c => c.undo(), redo:c => c.redo(),
  };
  document.querySelectorAll('[data-editor-action]').forEach(button => {
    button.onmousedown = event => event.preventDefault();
    button.onclick = () => actions[button.dataset.editorAction](editor.chain().focus()).run();
  });
  blockSelect.onchange = () => {
    const level = Number(blockSelect.value);
    const chain = editor.chain().focus();
    (level ? chain.setHeading({level}) : chain.setParagraph()).run();
  };
  document.getElementById('link-button').onmousedown = event => event.preventDefault();
  document.getElementById('link-button').onclick = () => {
    const dialog = document.getElementById('link-dialog');
    document.getElementById('link-url').value = editor.getAttributes('link').href || '';
    dialog.showModal();
  };
  document.getElementById('link-form').onsubmit = event => {
    event.preventDefault();
    const input = document.getElementById('link-url'), url = input.value.trim();
    if (url && !/^(https?:\/\/|mailto:)/i.test(url)) {
      input.setCustomValidity('https://, http:// 또는 mailto: 주소를 입력하세요.'); input.reportValidity(); return;
    }
    input.setCustomValidity('');
    const chain = editor.chain().focus().extendMarkRange('link');
    (url ? chain.setLink({href:url}) : chain.unsetLink()).run();
    document.getElementById('link-dialog').close();
  };
  document.getElementById('link-url').oninput = event => event.target.setCustomValidity('');
  document.getElementById('link-cancel').onclick = () => document.getElementById('link-dialog').close();
  document.querySelectorAll('[data-ask-selection]').forEach(button => {
    button.onmousedown = event => event.preventDefault();
    button.onclick = () => {
      const {from,to,empty} = editor.state.selection;
      if (!empty) onSelectAI({from,to,text:editor.state.doc.textBetween(from,to,'\n'), version});
    };
  });
  function syncUI() {
    if (editor.isDestroyed) return;
    document.querySelectorAll('[data-editor-action]').forEach(button => {
      const action = button.dataset.editorAction;
      button.classList.toggle('is-active', editor.isActive(action));
      button.setAttribute('aria-pressed', String(editor.isActive(action)));
      if (action === 'undo' || action === 'redo') button.disabled = !editor.can()[action]();
    });
    blockSelect.value = String(editor.isActive('heading') ? editor.getAttributes('heading').level : 0);
    document.getElementById('table-tools').hidden = !editor.isActive('table');
    const {from,to,empty} = editor.state.selection;
    const hasText = !empty && !!editor.state.doc.textBetween(from,to,'\n').trim();
    document.getElementById('ask-selection').disabled = !hasText;
    bubble.hidden = !hasText || !editor.isFocused;
    if (!bubble.hidden) {
      const rect = editor.view.coordsAtPos(from);
      bubble.style.left = `${Math.max(8, Math.min(rect.left, window.innerWidth - 255))}px`;
      bubble.style.top = `${Math.max(8, rect.top - 44)}px`;
    }
    updateOutline();
  }
  function updateOutline() {
    const outline = document.getElementById('outline'); outline.replaceChildren();
    editor.state.doc.descendants((node,pos) => {
      if (node.type.name !== 'heading') return;
      const li = document.createElement('li'), button = document.createElement('button');
      button.textContent = node.textContent || '제목 없음'; button.className = `outline-level-${node.attrs.level}`;
      button.onclick = () => {editor.chain().focus().setTextSelection(pos+1).scrollIntoView().run();};
      li.append(button); outline.append(li);
    });
    if (!outline.childElementCount) {const li = document.createElement('li'); li.textContent = '제목을 추가하면 목차가 표시됩니다.'; outline.append(li);}
  }
  document.getElementById('draft-pane').addEventListener('scroll', () => {closeMenu(); bubble.hidden = true;});
  window.addEventListener('resize', () => {closeMenu(); bubble.hidden = true;});
  return {
    markdown:() => editor.getMarkdown(),
    json() {
      const json = editor.getJSON();
      if (!json.content?.length) json.content = [{type:'paragraph'}];
      return json;
    },
    html:() => editor.getHTML(),
    text:() => editor.getText(),
    count:() => editor.storage.characterCount.characters(),
    load(markdown, json) {
      loading = true;
      // New instance state also clears undo history between documents.
      const parsed = json || editor.markdown.parse(markdown || '');
      if (!parsed.content?.length) parsed.content = [{type:'paragraph'}];
      const state = editor.state.constructor.create({schema:editor.schema, doc:editor.schema.nodeFromJSON(parsed), plugins:editor.state.plugins});
      editor.view.updateState(state); version++; loading = false; syncUI();
    },
    appendMarkdown(markdown) {editor.chain().focus('end').insertContent('\n\n'+markdown,{contentType:'markdown'}).run();},
    replaceSelection(selection, text) {
      if (selection.version !== version) return false;
      editor.chain().focus().insertContentAt({from:selection.from,to:selection.to}, editor.markdown.parse(text)).run();
      return true;
    },
    hideMenus() {closeMenu(); bubble.hidden = true;},
    refresh:syncUI,
  };
};
