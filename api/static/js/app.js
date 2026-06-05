/* ── AI 剧本创作工具 — Web UI 主应用 ────── */
const API = '/api/v1';
var _taskPollTimer = null;
var _lastTaskStates = {};  // 记录上次任务状态，用于检测完成

/* ── 页面导航 ────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.topbar-nav a').forEach(tab => {
    tab.addEventListener('click', (e) => {
      e.preventDefault();
      document.querySelectorAll('.topbar-nav a').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      const page = tab.dataset.page;
      document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
      var el = document.getElementById('page-' + page);
      if (el) el.classList.add('active');
      if (page === 'tasks') { loadTasks(); startTaskPolling(); }
      else { stopTaskPolling(); }
      if (page === 'styles') loadStyles();
    });
  });

  document.getElementById('btn-add-chapter').addEventListener('click', addChapter);
  document.getElementById('btn-demo').addEventListener('click', loadDemo);
  document.getElementById('btn-submit').addEventListener('click', submitConvert);
  setupFileUpload();

  document.getElementById('btn-refresh-tasks').addEventListener('click', loadTasks);
  document.getElementById('task-status-filter').addEventListener('change', loadTasks);

  document.querySelector('.modal-close').addEventListener('click', () => {
    document.getElementById('task-detail').classList.add('hidden');
  });
  document.getElementById('task-detail').addEventListener('click', function(e) {
    if (e.target === this) this.classList.add('hidden');
  });

  // 阅读器控制
  document.getElementById('reader-btn-prev').addEventListener('click', readerPrev);
  document.getElementById('reader-btn-next').addEventListener('click', readerNext);
  document.getElementById('reader-btn-close').addEventListener('click', closeReader);
});

/* ── Toast ───────────────────────────────── */
function toast(msg, type) {
  type = type || 'success';
  var el = document.createElement('div');
  el.className = 'toast ' + type;
  el.textContent = msg;
  document.body.appendChild(el);
  setTimeout(function() { el.remove(); }, 3000);
}

/* ── 章节管理 ────────────────────────────── */
function addChapter() {
  var container = document.getElementById('chapters-container');
  var idx = container.children.length;
  var div = document.createElement('div');
  div.className = 'chapter-block';
  div.dataset.idx = idx;
  div.innerHTML = '<button class="btn-remove-chapter" onclick="this.parentElement.remove()">&times;</button>' +
    '<input class="chapter-title" placeholder="第' + (idx+1) + '章 章节标题">' +
    '<textarea class="chapter-content" rows="5" placeholder="粘贴或输入章节正文..."></textarea>';
  container.appendChild(div);
}

function loadDemo() {
  var texts = [t('demo.text1'), t('demo.text2'), t('demo.text3')];
  var titles = [t('demo.title1'), t('demo.title2'), t('demo.title3')];
  var container = document.getElementById('chapters-container');
  container.innerHTML = '';
  for (var i = 0; i < 3; i++) {
    var div = document.createElement('div');
    div.className = 'chapter-block';
    div.dataset.idx = i;
    div.innerHTML = '<input class="chapter-title" value="第' + (i+1) + '章 ' + titles[i] + '">' +
      '<textarea class="chapter-content" rows="5">' + texts[i] + '</textarea>';
    container.appendChild(div);
  }
  toast(t('demo.loaded'));
}

/* ── 文件上传（支持 .txt/.docx/.pdf）─────── */
function setupFileUpload() {
  var zone = document.getElementById('file-upload-zone');
  var input = document.getElementById('file-input');
  zone.addEventListener('click', function() { input.click(); });
  zone.addEventListener('dragover', function(e) { e.preventDefault(); zone.classList.add('drag-over'); });
  zone.addEventListener('dragleave', function() { zone.classList.remove('drag-over'); });
  zone.addEventListener('drop', function(e) {
    e.preventDefault();
    zone.classList.remove('drag-over');
    handleDropFiles(e.dataTransfer.files);
  });
  input.addEventListener('change', function(e) { handleDropFiles(e.target.files); });
}

var _selectedFiles = [];

function handleDropFiles(files) {
  var validExt = ['.txt', '.docx', '.pdf'];
  var fileArray = Array.from(files).filter(function(f) {
    var ext = '.' + f.name.split('.').pop().toLowerCase();
    return validExt.indexOf(ext) !== -1;
  });

  if (fileArray.length < 3) {
    toast('请选择至少 3 个文件（支持 .txt / .docx / .pdf）', 'error');
    return;
  }

  // 按文件名中的数字排序
  fileArray.sort(function(a, b) {
    var na = parseInt((a.name.match(/\d+/) || ['0'])[0]);
    var nb = parseInt((b.name.match(/\d+/) || ['0'])[0]);
    return na - nb;
  });

  _selectedFiles = fileArray;

  var list = document.getElementById('file-list');
  list.innerHTML = '';
  fileArray.forEach(function(f, i) {
    var ext = f.name.split('.').pop().toLowerCase();
    var chip = document.createElement('span');
    chip.className = 'file-chip';
    var icon = ext === 'pdf' ? '&#128196;' : ext === 'docx' ? '&#128221;' : '&#128220;';
    chip.innerHTML = icon + ' ' + f.name + ' (' + (f.size / 1024).toFixed(1) + ' KB)';
    list.appendChild(chip);
  });
  toast('已选择 ' + fileArray.length + ' 个文件 — 点击"开始创作"将自动上传并解析');
}

/* ── 提交转换 ────────────────────────────── */
async function submitConvert() {
  var hasTextChapters = false;
  var chapters = [];
  document.querySelectorAll('#chapters-container .chapter-block').forEach(function(card) {
    var title = (card.querySelector('.chapter-title') || {}).value || '';
    var content = (card.querySelector('.chapter-content') || {}).value || '';
    title = title.trim();
    content = content.trim();
    if (title || content) { chapters.push({ title: title || '未命名', content: content }); hasTextChapters = true; }
  });

  var hasFiles = _selectedFiles.length >= 3;

  if (!hasTextChapters && !hasFiles) {
    toast('请提供至少 3 个章节（输入文本或上传文件）', 'error');
    return;
  }

  var btn = document.getElementById('btn-submit');
  btn.disabled = true;
  btn.textContent = '提交中...';

  var statusBox = document.getElementById('convert-status');
  statusBox.className = 'status-msg loading show';
  statusBox.textContent = '正在提交任务...';

  var cfgMode = document.getElementById('cfg-mode').value;
  var cfgStyle = document.getElementById('cfg-style').value;
  var cfgLang = document.getElementById('cfg-lang').value;
  var cfgReview = document.getElementById('cfg-review').checked;

  try {
    var resp;
    if (hasFiles) {
      // 文件上传模式
      var formData = new FormData();
      _selectedFiles.forEach(function(f) { formData.append('files', f); });
      formData.append('title', document.getElementById('cfg-title').value.trim());
      formData.append('author', document.getElementById('cfg-author').value.trim());
      formData.append('mode', cfgMode);
      formData.append('style', cfgStyle);
      formData.append('language', cfgLang);
      formData.append('enable_review', cfgReview);
      resp = await fetch(API + '/convert/upload', { method: 'POST', body: formData });
    } else {
      // 文本输入模式
      var body = {
        chapters: chapters,
        title: document.getElementById('cfg-title').value.trim(),
        author: document.getElementById('cfg-author').value.trim(),
        config: { mode: cfgMode, style: cfgStyle === 'auto' ? null : cfgStyle, language: cfgLang, enable_review: cfgReview }
      };
      resp = await fetch(API + '/convert', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });
    }
    if (!resp.ok) {
      var err = await resp.json();
      throw new Error(err.message || '提交失败');
    }
    var data = await resp.json();
    _selectedFiles = [];
    document.getElementById('file-list').innerHTML = '';
    statusBox.className = 'status-msg success show';
    statusBox.innerHTML = '已提交，3 秒后跳转到「我的作品」查看进度...<br><code>' + data.task_id + '</code>';
    toast(t('notify.taskSubmitted'));
    // 自动跳转到任务页看进度
    setTimeout(function() {
      var tasksTab = document.querySelector('[data-page=tasks]');
      if (tasksTab) tasksTab.click();
      loadTasks();
    }, 2000);
  } catch (e) {
    statusBox.className = 'status-msg error show';
    statusBox.textContent = '错误: ' + e.message;
    toast(e.message, 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = t('convert.submit');
  }
}

/* ── 任务列表（表格化+自动轮询）─────────── */
async function loadTasks() {
  var status = document.getElementById('task-status-filter').value;
  var url = API + '/tasks/' + (status ? '?status=' + status : '');
  var tbody = document.getElementById('task-tbody');
  var emptyDiv = document.getElementById('task-empty');

  try {
    var resp = await fetch(url);
    var data = await resp.json();

    if (!data.items || data.items.length === 0) {
      tbody.innerHTML = '';
      emptyDiv.style.display = 'block';
      _lastTaskStates = {};
      return;
    }
    emptyDiv.style.display = 'none';

    var hasProcessing = false;
    var nowStates = {};

    tbody.innerHTML = data.items.map(function(task) {
      nowStates[task.task_id] = task.status;
      if (task.status === 'processing') hasProcessing = true;

      var pct = task.progress.total_chapters > 0
        ? Math.round(task.progress.processed_chapters / task.progress.total_chapters * 100) : 0;
      
      // 检测任务从 processing 变为 completed
      var prevStatus = _lastTaskStates[task.task_id];
      if (prevStatus === 'processing' && task.status === 'completed') {
        setTimeout(function() {
          notifyTaskComplete(task.task_id);
        }, 100);
      }
      if (prevStatus === 'processing' && task.status === 'failed') {
        setTimeout(function() {
          toast(t('notify.taskFailed') + ': ' + (task.error_message || task.task_id.slice(0, 10)), 'error');
        }, 100);
      }

      var statusClass = task.status;
      if (task.status === 'completed') statusClass = 'completed';
      else if (task.status === 'failed') statusClass = 'failed';
      else if (task.status === 'processing') statusClass = 'processing';

      return '<tr class="task-row ' + statusClass + '" onclick="openTaskDetail(\'' + task.task_id + '\')">' +
        '<td><span class="dot ' + task.status + '"></span><span class="task-label">' + escHtml(task.task_id.slice(0, 10)) + '...</span></td>' +
        '<td style="color:var(--color-muted)">' + (task.progress.current_step || '-') + '</td>' +
        '<td class="task-progress-mini">' +
          '<span style="font-size:11px;color:var(--color-subtle)">' + task.progress.processed_chapters + '/' + task.progress.total_chapters + ' 章</span>' +
          '<div class="progress-bar-bg"><div class="progress-bar-fill" style="width:' + pct + '%"></div></div>' +
        '</td>' +
        '<td style="font-size:11px;color:var(--color-subtle)">' + (task.created_at || '').slice(0, 16) + '</td>' +
        '<td>' +
          (task.script_available ? '<button class="btn btn-ghost btn-xs" onclick="event.stopPropagation();openReader(\'' + task.task_id + '\')">' + t('detail.viewOnline') + '</button>' : '') +
          '<button class="btn btn-ghost btn-xs" onclick="event.stopPropagation();downloadScript(\'' + task.task_id + '\')" ' + (task.script_available ? '' : 'disabled') + '>' + t('detail.download') + '</button>' +
          '<button class="btn btn-ghost btn-xs" style="color:var(--color-error)" onclick="event.stopPropagation();deleteTask(\'' + task.task_id + '\')">' + t('detail.delete') + '</button>' +
        '</td>' +
      '</tr>';
    }).join('');

    _lastTaskStates = nowStates;

    // 有处理中任务时自动轮询
    if (hasProcessing && !_taskPollTimer) {
      startTaskPolling();
    } else if (!hasProcessing && _taskPollTimer) {
      stopTaskPolling();
    }
  } catch (e) {
    console.error(e);
  }
}

function startTaskPolling() {
  if (_taskPollTimer) return;
  _taskPollTimer = setInterval(function() {
    var tasksPage = document.getElementById('page-tasks');
    if (tasksPage && tasksPage.classList.contains('active')) {
      loadTasks();
    } else {
      stopTaskPolling();
    }
  }, 3000);
}

function stopTaskPolling() {
  if (_taskPollTimer) {
    clearInterval(_taskPollTimer);
    _taskPollTimer = null;
  }
}

function notifyTaskComplete(taskId) {
  var shortId = taskId.slice(0, 10);
  toast(t('notify.taskComplete') + ' 「' + shortId + '...」', 'success');
  // 浏览器通知
  if ('Notification' in window && Notification.permission === 'granted') {
    new Notification(t('app.title'), { body: t('notify.taskComplete') + ' 「' + shortId + '...」' });
  } else if ('Notification' in window && Notification.permission === 'default') {
    Notification.requestPermission();
  }
}

/* ── 任务详情 ────────────────────────────── */
async function openTaskDetail(id) {
  try {
    var taskResp = await fetch(API + '/tasks/' + id);
    var scriptResp = await fetch(API + '/tasks/' + id + '/script').catch(function() { return { ok: false }; });
    var task = await taskResp.json();
    var scriptText = '';
    if (scriptResp.ok) scriptText = await scriptResp.text();

    var reviewHtml = '';
    try {
      var reviewResp = await fetch(API + '/tasks/' + id + '/review');
      if (reviewResp.ok) {
        var rev = await reviewResp.json();
        reviewHtml = buildReviewHtml(rev);
      }
    } catch (_) {}

    var detail = document.getElementById('detail-body');
    detail.innerHTML =
      '<div class="info-row"><div class="info-label">任务 ID</div><div class="info-value">' + task.task_id + '</div></div>' +
      '<div class="info-row"><div class="info-label">状态</div><div class="info-value"><span class="dot ' + task.status + '"></span>' + t('status.' + task.status) + '</div></div>' +
      '<div class="info-row"><div class="info-label">进度</div><div class="info-value">' + (task.progress.current_step || '-') + ' (' + task.progress.processed_chapters + '/' + task.progress.total_chapters + ' 章, ' + task.progress.total_scenes + ' 场景)</div></div>' +
      (task.error_message ? '<div class="info-row"><div class="info-label">错误</div><div class="info-value" style="color:var(--color-error)">' + escHtml(task.error_message) + '</div></div>' : '') +
      reviewHtml +
      (scriptText ? '<div class="info-row"><div class="info-label">剧本预览</div><div class="script-preview">' + escHtml(scriptText.slice(0, 800)) + '...</div></div>' : '') +
      '<div style="display:flex;gap:8px;margin-top:16px;flex-wrap:wrap">' +
        '<button class="btn btn-outline btn-sm" onclick="openReader(\'' + id + '\')">' + t('detail.viewOnline') + '</button>' +
        (task.script_available ?
          '<button class="btn btn-primary btn-sm" onclick="downloadScript(\'' + id + '\')">' + t('detail.download') + '</button>' +
          '<button class="btn btn-outline btn-sm" onclick="validateScript(\'' + id + '\')">' + t('detail.validate') + '</button>' +
          '<button class="btn btn-outline btn-sm" onclick="polishDialogues(\'' + id + '\')">' + t('detail.polish') + '</button>' +
          '<button class="btn btn-outline btn-sm" onclick="getReview(\'' + id + '\')">' + t('detail.review') + '</button>'
        : '') +
        '<button class="btn btn-outline btn-sm" onclick="document.getElementById(\'task-detail\').classList.add(\'hidden\')">' + t('detail.close') + '</button>' +
      '</div>';

    document.getElementById('detail-title').textContent = '任务详情 — ' + id.slice(0, 10) + '...';
    document.getElementById('task-detail').classList.remove('hidden');
  } catch (e) {
    toast(t('toast.error') + ': ' + e.message, 'error');
  }
}

function buildReviewHtml(rev) {
  var colors = ['#2563eb','#059669','#d97706','#dc2626','#7c3aed','#0891b2'];
  return '<div style="margin-top:14px;padding:16px;background:#fafaf9;border-radius:var(--radius-sm);border:1px solid var(--color-border)">' +
    '<div class="info-label" style="margin-bottom:10px">' + t('detail.review') + '</div>' +
    '<div class="review-head">' +
      '<div class="score-ring">' + rev.total_score + '</div>' +
      '<div><span class="grade-badge">' + rev.grade + '</span><br><span style="font-size:12px;color:var(--color-muted)">AI 痕迹: ' + (rev.ai_trace_level || '?') + '</span></div>' +
    '</div>' +
    (rev.dimensions || []).map(function(d, i) {
      return '<div class="dim-row"><div class="dim-header"><span>' + d.name + ' (' + d.score + '/10)</span><span style="color:var(--color-subtle);font-size:11px">' + (d.priority || '') + '</span></div>' +
        '<div class="dim-bar-bg"><div class="dim-bar-fill" style="width:' + (d.score * 10) + '%;background:' + colors[i % 6] + '"></div></div>' +
        '<div class="dim-comment">' + (d.comment || '') + '</div></div>';
    }).join('') +
    (rev.top_strengths && rev.top_strengths.length ? '<ul class="strengths">' + rev.top_strengths.map(function(s) { return '<li>' + escHtml(s) + '</li>'; }).join('') + '</ul>' : '') +
    (rev.top_issues && rev.top_issues.length ? '<ul class="issues">' + rev.top_issues.map(function(s) { return '<li>' + escHtml(s) + '</li>'; }).join('') + '</ul>' : '') +
  '</div>';
}

/* ── 操作函数 ────────────────────────────── */
function downloadScript(id) {
  window.open(API + '/tasks/' + id + '/script', '_blank');
}

async function validateScript(id) {
  try {
    var resp = await fetch(API + '/tasks/' + id + '/validate', { method: 'POST' });
    var data = await resp.json();
    toast((data.valid ? '校验通过' : '校验未通过') + ': ' + data.error_count + ' 错误, ' + data.warning_count + ' 警告', data.valid ? 'success' : 'error');
  } catch (_) { toast(t('toast.error'), 'error'); }
}

async function polishDialogues(id) {
  try {
    var resp = await fetch(API + '/tasks/' + id + '/polish', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' });
    var data = await resp.json();
    toast(data.message || '润色完成', 'success');
  } catch (_) { toast(t('toast.error'), 'error'); }
}

async function getReview(id) {
  try {
    var resp = await fetch(API + '/tasks/' + id + '/review');
    var data = await resp.json();
    toast('评分: ' + data.total_score + '/60 · 等级: ' + data.grade, 'success');
  } catch (_) { toast('审核报告不可用', 'error'); }
}

async function deleteTask(id) {
  if (!confirm('确认删除此任务？关联的剧本也将被删除。')) return;
  try {
    await fetch(API + '/tasks/' + id, { method: 'DELETE' });
    toast(t('toast.deleted'));
    loadTasks();
  } catch (_) { toast(t('toast.error'), 'error'); }
}

/* ── 风格指南 ────────────────────────────── */
async function loadStyles() {
  try {
    var resp = await fetch(API + '/tasks/styles');
    var data = await resp.json();
    document.getElementById('style-grid').innerHTML = data.styles.map(function(s) {
      var label = t('style.label.' + s.value) || s.label;
      var desc = t('style.desc.' + s.value) || s.description;
      var acts = s.act_titles.map(function(a, i) {
        var actLabel = t('style.act.' + s.value + '.' + i) || a;
        return '<span class="act-tag">' + actLabel + '</span>';
      }).join('');
      return '<div class="style-card"><h4>' + label + '</h4><p>' + desc + '</p>' +
        '<div class="act-tags">' + acts + '</div></div>';
    }).join('');
  } catch (e) { console.error(e); }
}

/* ── 工具函数 ────────────────────────────── */
function escHtml(s) {
  var div = document.createElement('div');
  div.textContent = s;
  return div.innerHTML;
}

/* ══════════════════════════════════════════════════
   剧本在线阅读器 — 书本翻页
   ══════════════════════════════════════════════════ */

var _readerData = null;   // 剧本 YAML 数据
var _readerPages = [];    // 分页后的 HTML 内容
var _readerCurrent = 0;   // 当前双页索引（每双页=2面）
var _readerTotalSpreads = 0;
var _flipBusy = false;    // 翻页动画进行中
var _touchStartX = 0, _touchMoved = false;

async function openReader(taskId) {
  try {
    var resp = await fetch(API + '/tasks/' + taskId + '/script');
    if (!resp.ok) throw new Error('Fetch failed');
    var yamlText = await resp.text();

    _readerData = parseSimpleYaml(yamlText);
    if (!_readerData) { toast('无法解析剧本', 'error'); return; }

    _readerPages = buildReaderPages(_readerData);
    if (_readerPages.length === 0) { toast('剧本无内容', 'error'); return; }

    _readerCurrent = 0;
    _readerTotalSpreads = Math.ceil(_readerPages.length / 2);

    var title = (_readerData.meta || _readerData['元信息'] || {}).script_title ||
                (_readerData.meta || _readerData['元信息'] || {}).title || taskId.slice(0, 10);
    document.getElementById('reader-title').textContent = '剧本阅读 — ' + title;

    renderReaderSpread();
    document.getElementById('script-reader').classList.remove('hidden');
    document.body.style.overflow = 'hidden';

    document.addEventListener('keydown', _readerKeyHandler);
    _initTouchDrag();
  } catch (e) {
    toast(t('toast.error') + ': ' + e.message, 'error');
  }
}

function closeReader() {
  document.getElementById('script-reader').classList.add('hidden');
  document.body.style.overflow = '';
  document.removeEventListener('keydown', _readerKeyHandler);
  _cleanupTouchDrag();
  _readerData = null;
  _readerPages = [];
  _flipBusy = false;
}

function _readerKeyHandler(e) {
  if (e.key === 'ArrowRight' || e.key === 'ArrowDown') { e.preventDefault(); readerNext(); }
  else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') { e.preventDefault(); readerPrev(); }
  else if (e.key === 'Escape') { closeReader(); }
}

/* ── 翻页（transitionend 驱动 + 折叠阴影） ── */
function readerNext() {
  if (_flipBusy || _readerCurrent >= _readerTotalSpreads - 1) return;
  _flipBusy = true;

  var page = document.getElementById('reader-right');
  var leftPage = document.getElementById('reader-left');

  // 左页接收右页翻转投射的阴影
  leftPage.classList.add('shadow-receiving');

  var onEnd = function() {
    page.removeEventListener('transitionend', onEnd);
    _readerCurrent++;
    renderReaderSpread();
    page.classList.remove('flip-anim', 'flipping');
    leftPage.classList.remove('shadow-receiving');
    // 新渲染后清除可能的残留
    document.getElementById('reader-left').classList.remove('shadow-receiving');
    _flipBusy = false;
  };
  page.addEventListener('transitionend', onEnd);
  page.classList.add('flip-anim', 'flipping');
}

function readerPrev() {
  if (_flipBusy || _readerCurrent <= 0) return;
  _flipBusy = true;

  var page = document.getElementById('reader-left');
  var rightPage = document.getElementById('reader-right');

  // 右页接收左页翻转投射的阴影
  rightPage.classList.add('shadow-receiving');

  var onEnd = function() {
    page.removeEventListener('transitionend', onEnd);
    _readerCurrent--;
    renderReaderSpread();
    page.classList.remove('flip-anim', 'flipping');
    rightPage.classList.remove('shadow-receiving');
    // 新渲染后清除可能的残留
    document.getElementById('reader-right').classList.remove('shadow-receiving');
    _flipBusy = false;
  };
  page.addEventListener('transitionend', onEnd);
  page.classList.add('flip-anim', 'flipping');
}

/* ── 触摸 / 鼠标拖拽翻页 ── */
function _initTouchDrag() {
  var stage = document.querySelector('.reader-stage');
  if (!stage) return;
  stage.addEventListener('touchstart', _onTouchStart, {passive: true});
  stage.addEventListener('touchmove', _onTouchMove, {passive: true});
  stage.addEventListener('touchend', _onTouchEnd);
  stage.addEventListener('mousedown', _onMouseDown);
  stage.addEventListener('mouseup', _onMouseUp);
  document.addEventListener('mousemove', _onMouseMove);
}

function _cleanupTouchDrag() {
  var stage = document.querySelector('.reader-stage');
  if (!stage) return;
  stage.removeEventListener('touchstart', _onTouchStart);
  stage.removeEventListener('touchmove', _onTouchMove);
  stage.removeEventListener('touchend', _onTouchEnd);
  stage.removeEventListener('mousedown', _onMouseDown);
  stage.removeEventListener('mouseup', _onMouseUp);
  document.removeEventListener('mousemove', _onMouseMove);
  _resetDragPreview();
}

var _dragTarget = null, _dragStartX = 0, _dragMaxAngle = 0;

function _resetDragPreview() {
  if (_dragTarget) {
    _dragTarget.classList.remove('drag-preview', 'flip-anim');
    _dragTarget.style.removeProperty('--drag-angle');
    _dragTarget = null;
  }
}

function _onTouchStart(e) {
  _touchStartX = e.touches[0].clientX;
  _touchMoved = false;
}

function _onTouchMove(e) {
  if (_flipBusy) return;
  var dx = _touchStartX - e.touches[0].clientX;
  if (Math.abs(dx) > 8) _touchMoved = true;
  // 实时拖拽反馈
  _applyDragPreview(dx);
}

function _onTouchEnd(e) {
  _resetDragPreview();
  if (!_touchMoved || _flipBusy) return;
  var dx = _touchStartX - e.changedTouches[0].clientX;
  if (Math.abs(dx) > 50) {
    if (dx > 0) readerNext();
    else readerPrev();
  }
}

function _onMouseDown(e) {
  if (_flipBusy) return;
  _dragStartX = e.clientX;
}

var _mouseDragActive = false;
function _onMouseMove(e) {
  if (_flipBusy || e.buttons !== 1) return;
  if (!_mouseDragActive && Math.abs(e.clientX - _dragStartX) > 5) _mouseDragActive = true;
  if (_mouseDragActive) {
    _applyDragPreview(_dragStartX - e.clientX);
  }
}

function _onMouseUp(e) {
  var wasDrag = _mouseDragActive;
  _mouseDragActive = false;
  _resetDragPreview();
  if (!wasDrag || _flipBusy) return;
  var dx = _dragStartX - e.clientX;
  if (Math.abs(dx) > 50) {
    if (dx > 0) readerNext();
    else readerPrev();
  }
}

/* 拖拽实时预览 — 页面角度随手指移动 */
function _applyDragPreview(dx) {
  var maxAngle = Math.min(Math.abs(dx) / 1.5, 90); // 最大 90°
  var angle = dx > 0 ? -maxAngle : maxAngle; // 右拖→右翻（负角），左拖→左翻（正角）

  var page;
  if (dx > 0 && _readerCurrent < _readerTotalSpreads - 1) {
    page = document.getElementById('reader-right');
  } else if (dx < 0 && _readerCurrent > 0) {
    page = document.getElementById('reader-left');
  }

  if (page && page !== _dragTarget) {
    _resetDragPreview();
    _dragTarget = page;
    page.classList.add('drag-preview', 'flip-anim');
  }
  if (page) {
    page.style.setProperty('--drag-angle', angle);
  }
}

function renderReaderSpread() {
  var leftIdx = _readerCurrent * 2;
  var rightIdx = leftIdx + 1;

  var leftEl = document.getElementById('reader-left');
  var rightEl = document.getElementById('reader-right');
  var leftContent = document.getElementById('reader-left-content');
  var rightContent = document.getElementById('reader-right-content');

  leftContent.innerHTML = leftIdx < _readerPages.length ? _readerPages[leftIdx] : '';
  rightContent.innerHTML = rightIdx < _readerPages.length ? _readerPages[rightIdx] : '';

  document.getElementById('reader-page-num').textContent =
    (_readerCurrent + 1) + ' / ' + _readerTotalSpreads;

  document.getElementById('reader-btn-prev').disabled = (_readerCurrent <= 0);
  document.getElementById('reader-btn-next').disabled = (_readerCurrent >= _readerTotalSpreads - 1);

  // 点击右页向前翻，左页向后翻
  rightEl.onclick = function() { readerNext(); };
  leftEl.onclick = function() { readerPrev(); };
}

/* ── 分页引擎 ──────────────────────────────── */
function buildReaderPages(data) {
  var meta = data.meta || data['元信息'] || {};
  var characters = data.characters || data['角色列表'] || [];
  var scenes = data.scenes || data['场景列表'] || [];
  var acts = data.acts || data['分幕结构'] || [];

  if (!scenes.length) return [];

  var pages = [];

  // 封面页
  var coverHtml = '<div style="display:flex;flex-direction:column;justify-content:center;min-height:420px">' +
    '<div class="reader-scene-num">改编剧本</div>' +
    '<h1 style="font-family:var(--font-serif);font-size:28px;font-weight:700;color:var(--ink);margin:16px 0 8px">' +
      escHtml(meta.script_title || meta['剧本标题'] || meta.title || '未命名') +
    '</h1>' +
    '<p style="color:var(--ink-muted);font-size:14px;margin-bottom:4px">原著: ' +
      escHtml(meta.original_novel || meta['原著名称'] || '') + '</p>' +
    '<p style="color:var(--ink-muted);font-size:14px;margin-bottom:4px">作者: ' +
      escHtml(meta.original_author || meta['原著作者'] || '') + '</p>' +
    '<p style="color:var(--ink-muted);font-size:14px;margin-bottom:4px">类型: ' +
      escHtml((meta.genre || meta['类型标签'] || []).join('、')) + '</p>' +
    '<p style="color:var(--ink-muted);font-size:14px">共 ' + scenes.length + ' 个场景</p>' +
    '<div style="margin-top:40px;padding-top:20px;border-top:1px solid #e8e2d8">' +
      '<p style="color:var(--ink-soft);font-size:13px;line-height:1.8;font-style:italic">' +
        escHtml(meta.synopsis || meta['故事梗概'] || '') +
      '</p></div>' +
  '</div>';
  pages.push(coverHtml);

  // 角色页
  if (characters.length > 0) {
    var charHtml = '<div class="reader-scene-num">角色表</div>' +
      '<h2 style="font-family:var(--font-serif);font-size:20px;font-weight:600;color:var(--ink);margin:10px 0 18px">主要角色</h2>';
    for (var ci = 0; ci < characters.length; ci++) {
      var c = characters[ci];
      charHtml += '<div style="margin-bottom:16px;padding-bottom:14px;border-bottom:1px solid #f0ebe2">' +
        '<span style="font-weight:700;color:var(--ink)">' + escHtml(c.name || c['姓名'] || c.character_id || '') + '</span>' +
        '<span style="font-size:11px;color:var(--ink-muted);margin-left:8px">' +
          escHtml(c.role_type || c['角色类型'] || '') + '</span>' +
        '<p style="font-size:13px;color:var(--ink-soft);margin-top:4px;line-height:1.7">' +
          escHtml((c.personality_traits || c['性格特征'] || []).join('、')) + '</p>' +
        '<p style="font-size:12px;color:var(--ink-faint);margin-top:2px">' +
          (c.background || c['背景故事'] || c.motivation || c['核心动机'] || '') + '</p>' +
      '</div>';
    }
    pages.push(charHtml);
  }

  // 分幕标题页（每个 act 一个标题页）
  for (var ai = 0; ai < acts.length; ai++) {
    var a = acts[ai];
    var ah = '<div style="display:flex;flex-direction:column;justify-content:center;min-height:420px;text-align:center">' +
      '<div class="reader-scene-num" style="text-align:center">第' + (a.act_number || a['幕序号'] || (ai + 1)) + '幕</div>' +
      '<h2 style="font-family:var(--font-serif);font-size:32px;font-weight:700;color:var(--ink);margin:16px 0 8px">' +
        escHtml(a.title || a['幕标题'] || '') + '</h2>' +
      '<p style="color:var(--ink-muted);font-size:14px;line-height:1.7;max-width:320px;margin:0 auto">' +
        escHtml(a.description || a['描述'] || a.narrative_function || a['叙事功能'] || '') + '</p>' +
    '</div>';
    pages.push(ah);
  }

  // 场景页（每个场景一页）
  for (var si = 0; si < scenes.length; si++) {
    var scene = scenes[si];
    var heading = scene.scene_heading || scene['场景标题'] || {};
    var loc = heading.location || heading['地点'] || '';
    var time = heading.time || heading['时间'] || '';
    var ie = heading.interior_exterior || heading['内外景'] || '';

    var shtml = '<div class="reader-scene-num">场景 ' + (scene.scene_id || scene['场景编号'] || (si + 1)) + '</div>' +
      '<div class="reader-scene-heading">' + escHtml(ie) + ' · ' + escHtml(loc) + ' · ' + escHtml(time) + '</div>';

    shtml += '<div class="reader-scene-summary">' + escHtml(scene.summary || scene['场景概要'] || '') + '</div>';

    var beats = scene.beats || scene['节拍'] || [];
    for (var bi = 0; bi < beats.length; bi++) {
      var beat = beats[bi];
      var bt = beat.beat_type || beat['节拍类型'] || '';
      if (bt === 'dialogue' || bt === 'monologue' || bt === 'voiceover') {
        var charId = beat.character_id || beat['说话角色'] || '';
        var charName = _findCharName(charId, characters);
        shtml += '<div class="reader-beat dialogue">';
        if (beat.parenthetical || beat['动作指示']) {
          shtml += '<div class="beat-parenthetical">(' + escHtml(beat.parenthetical || beat['动作指示']) + ')</div>';
        }
        shtml += '<div class="beat-char">' + escHtml(charName || charId) + '</div>';
        shtml += '<div class="beat-text">' + escHtml(beat.content || beat['内容'] || '') + '</div>';
        if (beat.subtext || beat['潜台词']) {
          shtml += '<div class="beat-subtext">' + escHtml(beat.subtext || beat['潜台词']) + '</div>';
        }
        shtml += '</div>';
      } else {
        shtml += '<div class="reader-beat"><div class="beat-action">' +
          escHtml(beat.content || beat['内容'] || '') + '</div></div>';
      }
    }
    pages.push(shtml);
  }

  // 结束页
  var endHtml = '<div style="display:flex;flex-direction:column;justify-content:center;align-items:center;min-height:420px;text-align:center">' +
    '<div style="font-size:48px;color:var(--ink-faint);margin-bottom:20px">&#9998;</div>' +
    '<h2 style="font-family:var(--font-serif);font-size:24px;font-weight:600;color:var(--ink)">— 剧本完 —</h2>' +
    '<p style="color:var(--ink-muted);font-size:14px;margin-top:12px">共 ' + scenes.length + ' 个场景</p>' +
    '<p style="color:var(--ink-faint);font-size:12px;margin-top:20px">AI 剧本创作工具 生成</p>' +
  '</div>';
  pages.push(endHtml);

  return pages;
}

function _findCharName(charId, characters) {
  for (var i = 0; i < characters.length; i++) {
    var c = characters[i];
    if ((c.character_id || c['角色ID']) === charId) return c.name || c['姓名'];
  }
  return null;
}

/* ── 简易 YAML 解析器（无需外部库）────────────── */
function parseSimpleYaml(text) {
  var lines = text.split('\n');
  var root = {};
  var stack = [{ obj: root, indent: -1, key: '' }];
  var multilineKey = '';
  var multilineBuf = '';
  var inMultiline = false;

  for (var i = 0; i < lines.length; i++) {
    var line = lines[i];
    var trimmed = line.replace(/\r$/, '');

    if (inMultiline) {
      var mEndMatch = trimmed.match(/^(\s*)(\S)/);
      if (mEndMatch && mEndMatch[1].length <= stack[stack.length - 1].indent && mEndMatch[2] !== '-') {
        _setNested(stack[stack.length - 1].obj, multilineKey, multilineBuf, stack);
        multilineBuf = ''; multilineKey = ''; inMultiline = false;
      } else {
        var mline = trimmed.replace(/^\s+/, '');
        if (mline && !mline.startsWith('#')) multilineBuf += (multilineBuf ? '\n' : '') + mline;
        continue;
      }
    }

    if (!trimmed || trimmed.startsWith('#')) continue;

    var indent = line.search(/\S/);
    var content = trimmed;

    // 修改：处理数组项时，如果栈顶是数组的键（不是数组项），即使缩进相同也不弹出
    var isArrayItem = content.startsWith('- ');
    while (stack.length > 1) {
      var top = stack[stack.length - 1];
      // 如果是数组项，且栈顶是数组的键（不是数组项），即使缩进相同也保留
      if (isArrayItem && !top._isArrItem && top.indent === indent) {
        break;
      }
      if (top.indent >= indent) {
        stack.pop();
      } else {
        break;
      }
    }
    var parent = stack[stack.length - 1];

    if (isArrayItem) {
      var arrVal = content.slice(2);
      var arrKey = _findArrayKey(stack);
      
      var arr = null;
      
      // 查找目标对象
      var targetObj = null;
      for (var si = 0; si < stack.length; si++) {
        if (stack[si].key === arrKey) {
          targetObj = stack[si].obj;
          break;
        }
      }
      if (!targetObj) targetObj = parent.obj;
      
      // 检查当前对象是否就是目标数组
      if (targetObj === parent.obj && parent['key'] === arrKey) {
        // 当前对象应该是数组，需要转换
        if (!Array.isArray(parent.obj)) {
          // 需要重新设置父级中的这个键为数组
          for (var pi = stack.length - 2; pi >= 0; pi--) {
            if (stack[pi].obj[parent.key] === parent.obj) {
              stack[pi].obj[parent.key] = [];
              arr = stack[pi].obj[parent.key];
              break;
            }
          }
          if (!arr) {
            arr = [];
          }
        } else {
          arr = parent.obj;
        }
      } else {
        // 目标对象的属性是数组
        if (!targetObj[arrKey]) targetObj[arrKey] = [];
        else if (!Array.isArray(targetObj[arrKey])) targetObj[arrKey] = [];
        arr = targetObj[arrKey];
      }

      var obj = {};
      if (arrVal.includes(':')) {
        var colonIdx = arrVal.indexOf(':');
        var k2 = arrVal.slice(0, colonIdx).trim();
        var v2 = arrVal.slice(colonIdx + 1).trim();
        obj[k2] = v2 ? _parseScalar(v2) : '';
      } else {
        obj = arrVal ? _parseScalar(arrVal) : '';
      }
      arr.push(obj);

      if (typeof obj === 'object' && obj !== null && !Array.isArray(obj)) {
        stack.push({ obj: obj, indent: indent, key: '', _isArrItem: true });
      }

    } else if (content.includes(':')) {
      var ci = content.indexOf(':');
      var key = content.slice(0, ci).trim();
      var val = content.slice(ci + 1).trim();

      if (!val && key.startsWith('- ')) { key = key.slice(2); val = ''; }

      if (val === '|' || val === '>' || val === '|-' || val === '>-') {
        multilineKey = key; multilineBuf = ''; inMultiline = true;
        continue;
      }

      if (val === '' || val === '{}' || val === '[]') parent.obj[key] = {};
      else parent.obj[key] = _parseScalar(val);

      var nextLine = '';
      for (var j = i + 1; j < lines.length; j++) {
        var nl = lines[j].replace(/\r$/, '');
        if (nl.trim() && !nl.trim().startsWith('#')) { nextLine = nl; break; }
      }
      if (nextLine) {
        var nextIndent = nextLine.search(/\S/);
        // 关键修复：无论下一行缩进是否更大，只要下一行是数组项，就需要将当前键推入栈
        if (nextLine.trim().startsWith('- ')) {
          // 将空对象改为空数组
          parent.obj[key] = [];
          stack.push({ obj: parent.obj[key], indent: indent, key: key });
        } else if (nextIndent > indent) {
          if (typeof parent.obj[key] !== 'object' || Array.isArray(parent.obj[key])) parent.obj[key] = {};
          stack.push({ obj: parent.obj[key], indent: indent, key: key });
        }
      }
    }
  }

  if (inMultiline && multilineKey) _setNested(stack[stack.length - 1].obj, multilineKey, multilineBuf, stack);

  return root;
}

function _findArrayKey(stack) {
  for (var i = stack.length - 1; i >= 0; i--) {
    if (stack[i].key && !stack[i]._isArrItem) return stack[i].key;
  }
  return 'items';
}

function _setNested(obj, key, val, stack) {
  obj[key] = val;
}

function _parseScalar(v) {
  if (v === 'true') return true;
  if (v === 'false') return false;
  if (v === 'null' || v === '~') return null;
  if (/^-?\d+$/.test(v)) return parseInt(v);
  if (/^-?\d+\.\d+$/.test(v)) return parseFloat(v);
  v = v.replace(/^["']|["']$/g, '');
  return v;
}
