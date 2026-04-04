#!/usr/bin/env node
/**
 * Artifact Browser — lightweight HTTP server for browsing/uploading/viewing .artifacts/
 * Uses only Node.js built-in modules (http, fs, path, url, crypto).
 * Port: process.env.ARTIFACT_BROWSER_PORT || 28080
 */

'use strict';

const http = require('http');
const fs   = require('fs');
const path = require('path');
const { URL } = require('url');

const PORT           = parseInt(process.env.ARTIFACT_BROWSER_PORT || '28080', 10);
const ARTIFACTS_ROOT = path.resolve(__dirname, '..', '.artifacts');

// ── Security helper ──────────────────────────────────────────────────────────

/**
 * Resolve a user-supplied relative path against ARTIFACTS_ROOT and throw if
 * the result escapes the root (path traversal guard).
 */
function resolveSafe(rel) {
  if (!rel) throw Object.assign(new Error('Missing path'), { status: 400 });
  const resolved = path.resolve(ARTIFACTS_ROOT, rel.replace(/^\/+/, ''));
  if (!resolved.startsWith(ARTIFACTS_ROOT + path.sep) && resolved !== ARTIFACTS_ROOT) {
    throw Object.assign(new Error('Forbidden'), { status: 403 });
  }
  return resolved;
}

// ── Tree builder ─────────────────────────────────────────────────────────────

function buildTree(dir, relBase) {
  const entries = fs.readdirSync(dir, { withFileTypes: true })
    .sort((a, b) => {
      // Directories first, then files
      if (a.isDirectory() && !b.isDirectory()) return -1;
      if (!a.isDirectory() && b.isDirectory()) return 1;
      return a.name.localeCompare(b.name);
    });

  return entries.map(entry => {
    const relPath = relBase ? `${relBase}/${entry.name}` : entry.name;
    if (entry.isDirectory()) {
      return {
        name: entry.name,
        path: relPath,
        type: 'dir',
        children: buildTree(path.join(dir, entry.name), relPath),
      };
    }
    return { name: entry.name, path: relPath, type: 'file' };
  });
}

// ── Multipart parser ─────────────────────────────────────────────────────────

/**
 * Parse multipart/form-data from a raw Buffer.
 * Returns an array of { filename, data } objects (only file parts).
 * Limit: 50 MB total body.
 */
function parseMultipart(body, contentType) {
  const boundaryMatch = contentType.match(/boundary=(?:"([^"]+)"|([^\s;]+))/i);
  if (!boundaryMatch) throw Object.assign(new Error('No boundary'), { status: 400 });
  const boundary = Buffer.from('--' + (boundaryMatch[1] || boundaryMatch[2]));
  const CRLF = Buffer.from('\r\n');
  const files = [];

  let pos = 0;

  function indexOf(buf, needle, start) {
    for (let i = start; i <= buf.length - needle.length; i++) {
      let match = true;
      for (let j = 0; j < needle.length; j++) {
        if (buf[i + j] !== needle[j]) { match = false; break; }
      }
      if (match) return i;
    }
    return -1;
  }

  while (pos < body.length) {
    // Find boundary
    const boundaryPos = indexOf(body, boundary, pos);
    if (boundaryPos === -1) break;
    pos = boundaryPos + boundary.length;

    // Check for final boundary (--)
    if (body[pos] === 0x2d && body[pos + 1] === 0x2d) break;

    // Skip CRLF after boundary
    if (body[pos] === 0x0d && body[pos + 1] === 0x0a) pos += 2;

    // Read headers
    const headerEnd = indexOf(body, Buffer.from('\r\n\r\n'), pos);
    if (headerEnd === -1) break;
    const headerStr = body.slice(pos, headerEnd).toString('utf8');
    pos = headerEnd + 4;

    // Parse Content-Disposition
    const dispMatch = headerStr.match(/Content-Disposition:[^\r\n]*filename="([^"]+)"/i);
    if (!dispMatch) {
      // Not a file part — skip to next boundary
      const nextBoundary = indexOf(body, boundary, pos);
      if (nextBoundary === -1) break;
      pos = nextBoundary;
      continue;
    }
    const filename = path.basename(dispMatch[1]); // strip any path from filename

    // Find next boundary to get part body
    const nextBoundary = indexOf(body, Buffer.from('\r\n' + '--' + (boundaryMatch[1] || boundaryMatch[2])), pos);
    if (nextBoundary === -1) break;
    const data = body.slice(pos, nextBoundary);
    files.push({ filename, data });
    pos = nextBoundary;
  }

  return files;
}

// ── Inline HTML ──────────────────────────────────────────────────────────────

const HTML = `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Artifact Browser</title>
<style>
  *{box-sizing:border-box;margin:0;padding:0}
  body{font-family:system-ui,sans-serif;display:flex;height:100vh;overflow:hidden;background:#f5f5f5}
  #sidebar{width:280px;min-width:200px;max-width:400px;background:#1e1e2e;color:#cdd6f4;overflow-y:auto;padding:12px;resize:horizontal;border-right:2px solid #313244}
  #sidebar h2{font-size:.8rem;text-transform:uppercase;letter-spacing:.1em;color:#6c7086;padding:4px 0 8px;border-bottom:1px solid #313244;margin-bottom:8px}
  #main{flex:1;display:flex;flex-direction:column;overflow:hidden}
  #toolbar{background:#313244;color:#cdd6f4;padding:6px 12px;font-size:.8rem;display:flex;align-items:center;gap:8px}
  #content{flex:1;overflow:auto;padding:16px;background:#fff}
  #content pre{background:#1e1e2e;color:#cdd6f4;padding:16px;border-radius:6px;overflow:auto;font-size:.8rem;line-height:1.5;white-space:pre-wrap;word-break:break-all}
  #content img{max-width:100%;border-radius:4px}
  #content iframe{width:100%;height:calc(100vh - 120px);border:none}
  .tree-node{margin-left:0}
  .tree-node .node-row{display:flex;align-items:center;gap:4px;padding:2px 4px;border-radius:4px;cursor:pointer;font-size:.82rem;white-space:nowrap;overflow:hidden}
  .tree-node .node-row:hover{background:#313244}
  .tree-node .node-row.selected{background:#45475a}
  .chevron{display:inline-block;width:14px;text-align:center;transition:transform .15s;flex-shrink:0;font-size:.7rem;color:#6c7086}
  .chevron.open{transform:rotate(90deg)}
  .icon{flex-shrink:0}
  .label{overflow:hidden;text-overflow:ellipsis;flex:1}
  .children{margin-left:16px;border-left:1px solid #313244}
  .upload-btn{background:none;border:1px solid #45475a;color:#89b4fa;border-radius:3px;padding:1px 5px;font-size:.7rem;cursor:pointer;flex-shrink:0}
  .upload-btn:hover{background:#45475a}
  #status{padding:4px 8px;font-size:.75rem;color:#a6e3a1}
  #status.err{color:#f38ba8}
  .empty{color:#6c7086;font-style:italic;font-size:.85rem;padding:20px}
  a.dl{color:#89b4fa;text-decoration:none}
  a.dl:hover{text-decoration:underline}
</style>
</head>
<body>
<div id="sidebar">
  <h2>Artifacts</h2>
  <div id="tree">Loading…</div>
</div>
<div id="main">
  <div id="toolbar">
    <span id="current-path" style="flex:1;opacity:.6">Select a file</span>
    <span id="status"></span>
  </div>
  <div id="content"><div class="empty">Select a file from the tree to view it.</div></div>
</div>
<input type="file" id="file-input" multiple style="display:none">
<script>
let uploadTarget = null;
let selectedPath = null;

async function loadTree() {
  const res = await fetch('/api/tree');
  const tree = await res.json();
  document.getElementById('tree').innerHTML = '';
  renderNodes(tree, document.getElementById('tree'));
}

function renderNodes(nodes, container) {
  nodes.forEach(node => {
    const div = document.createElement('div');
    div.className = 'tree-node';
    const row = document.createElement('div');
    row.className = 'node-row';

    if (node.type === 'dir') {
      const chev = document.createElement('span');
      chev.className = 'chevron open';
      chev.textContent = '▶';
      const icon = document.createElement('span');
      icon.className = 'icon';
      icon.textContent = '📁';
      const label = document.createElement('span');
      label.className = 'label';
      label.textContent = node.name;
      const uploadBtn = document.createElement('button');
      uploadBtn.className = 'upload-btn';
      uploadBtn.textContent = '↑';
      uploadBtn.title = 'Upload to ' + node.path;
      uploadBtn.onclick = e => { e.stopPropagation(); triggerUpload(node.path); };
      row.appendChild(chev);
      row.appendChild(icon);
      row.appendChild(label);
      row.appendChild(uploadBtn);

      const children = document.createElement('div');
      children.className = 'children';
      if (node.children && node.children.length) {
        renderNodes(node.children, children);
      }
      div.appendChild(row);
      div.appendChild(children);

      row.onclick = () => {
        const open = chev.classList.toggle('open');
        children.style.display = open ? '' : 'none';
      };
    } else {
      const chev = document.createElement('span');
      chev.className = 'chevron';
      chev.textContent = '';
      const icon = document.createElement('span');
      icon.className = 'icon';
      icon.textContent = fileIcon(node.name);
      const label = document.createElement('span');
      label.className = 'label';
      label.textContent = node.name;
      row.appendChild(chev);
      row.appendChild(icon);
      row.appendChild(label);
      div.appendChild(row);

      row.onclick = () => {
        document.querySelectorAll('.node-row.selected').forEach(r => r.classList.remove('selected'));
        row.classList.add('selected');
        openFile(node.path);
      };
    }
    container.appendChild(div);
  });
}

function fileIcon(name) {
  const ext = name.split('.').pop().toLowerCase();
  if (['png','jpg','jpeg','gif','svg','webp'].includes(ext)) return '🖼';
  if (ext === 'pdf') return '📄';
  if (['md','txt','yaml','yml','json','sh','js','ts','html','css'].includes(ext)) return '📝';
  return '📎';
}

async function openFile(relPath) {
  selectedPath = relPath;
  document.getElementById('current-path').textContent = relPath;
  const content = document.getElementById('content');
  content.innerHTML = '<div class="empty">Loading…</div>';

  const ext = relPath.split('.').pop().toLowerCase();
  const url = '/api/file?path=' + encodeURIComponent(relPath);

  if (['png','jpg','jpeg','gif','svg','webp'].includes(ext)) {
    content.innerHTML = '<img src="' + url + '" alt="' + relPath + '">';
  } else if (ext === 'pdf') {
    content.innerHTML = '<iframe src="' + url + '"></iframe>';
  } else {
    // Try to fetch as text
    try {
      const res = await fetch(url);
      if (!res.ok) throw new Error(await res.text());
      const text = await res.text();
      const pre = document.createElement('pre');
      pre.textContent = text;
      content.innerHTML = '';
      content.appendChild(pre);
    } catch(e) {
      content.innerHTML = '<div class="empty">Cannot display file. <a class="dl" href="' + url + '?download=1">Download</a></div>';
    }
  }
}

function triggerUpload(dirPath) {
  uploadTarget = dirPath;
  const input = document.getElementById('file-input');
  input.value = '';
  input.click();
}

document.getElementById('file-input').onchange = async function() {
  const files = Array.from(this.files);
  if (!files.length) return;
  const status = document.getElementById('status');
  status.className = '';
  status.textContent = 'Uploading…';

  const fd = new FormData();
  files.forEach(f => fd.append('file', f, f.name));

  try {
    const res = await fetch('/api/upload?dir=' + encodeURIComponent(uploadTarget), {
      method: 'POST',
      body: fd,
    });
    if (!res.ok) throw new Error(await res.text());
    const json = await res.json();
    status.textContent = 'Uploaded ' + json.uploaded.join(', ');
    await loadTree();
  } catch(e) {
    status.className = 'err';
    status.textContent = 'Upload failed: ' + e.message;
  }
};

loadTree();
</script>
</body>
</html>`;

// ── Request handlers ─────────────────────────────────────────────────────────

function sendJSON(res, status, obj) {
  const body = JSON.stringify(obj);
  res.writeHead(status, { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(body) });
  res.end(body);
}

function sendError(res, err) {
  const status = err.status || 500;
  res.writeHead(status, { 'Content-Type': 'text/plain' });
  res.end(err.message || 'Internal Server Error');
}

function handleGetTree(req, res) {
  try {
    const tree = buildTree(ARTIFACTS_ROOT, '');
    sendJSON(res, 200, tree);
  } catch (err) {
    sendError(res, err);
  }
}

function handleGetFile(req, res, params) {
  try {
    const rel = params.get('path');
    const absPath = resolveSafe(rel);
    if (!fs.existsSync(absPath) || fs.statSync(absPath).isDirectory()) {
      throw Object.assign(new Error('Not Found'), { status: 404 });
    }

    const download = params.get('download') === '1';
    const ext = path.extname(absPath).toLowerCase().slice(1);
    const mimeMap = {
      md: 'text/plain', txt: 'text/plain', yaml: 'text/plain', yml: 'text/plain',
      json: 'application/json', js: 'text/javascript', ts: 'text/plain',
      html: 'text/html', css: 'text/css', sh: 'text/plain',
      png: 'image/png', jpg: 'image/jpeg', jpeg: 'image/jpeg',
      gif: 'image/gif', svg: 'image/svg+xml', webp: 'image/webp',
      pdf: 'application/pdf',
    };
    const mime = mimeMap[ext] || 'application/octet-stream';
    const stat = fs.statSync(absPath);
    const headers = {
      'Content-Type': mime,
      'Content-Length': stat.size,
      'Cache-Control': 'no-cache',
    };
    if (download) {
      headers['Content-Disposition'] = `attachment; filename="${path.basename(absPath)}"`;
    } else {
      headers['Content-Disposition'] = `inline; filename="${path.basename(absPath)}"`;
    }
    res.writeHead(200, headers);
    fs.createReadStream(absPath).pipe(res);
  } catch (err) {
    sendError(res, err);
  }
}

function handleUpload(req, res, params) {
  const LIMIT = 50 * 1024 * 1024; // 50 MB
  const chunks = [];
  let totalSize = 0;

  req.on('data', chunk => {
    totalSize += chunk.length;
    if (totalSize > LIMIT) {
      req.destroy();
      return;
    }
    chunks.push(chunk);
  });

  req.on('end', () => {
    try {
      if (totalSize > LIMIT) {
        throw Object.assign(new Error('Payload too large (max 50 MB)'), { status: 413 });
      }
      const dir = params.get('dir') || '';
      const absDir = resolveSafe(dir);

      if (!fs.existsSync(absDir)) {
        fs.mkdirSync(absDir, { recursive: true });
      } else if (!fs.statSync(absDir).isDirectory()) {
        throw Object.assign(new Error('Target is not a directory'), { status: 400 });
      }

      const contentType = req.headers['content-type'] || '';
      const body = Buffer.concat(chunks);
      const files = parseMultipart(body, contentType);

      if (!files.length) {
        throw Object.assign(new Error('No files found in upload'), { status: 400 });
      }

      const uploaded = [];
      for (const { filename, data } of files) {
        const dest = path.join(absDir, filename);
        // One more safety check on the final dest path
        if (!dest.startsWith(ARTIFACTS_ROOT + path.sep)) {
          throw Object.assign(new Error('Forbidden'), { status: 403 });
        }
        fs.writeFileSync(dest, data);
        uploaded.push(filename);
      }

      sendJSON(res, 200, { uploaded });
    } catch (err) {
      sendError(res, err);
    }
  });

  req.on('error', err => sendError(res, err));
}

function handleDeleteFile(req, res, params) {
  try {
    const rel = params.get('path');
    const absPath = resolveSafe(rel);
    if (!fs.existsSync(absPath) || fs.statSync(absPath).isDirectory()) {
      throw Object.assign(new Error('Not Found'), { status: 404 });
    }
    fs.unlinkSync(absPath);
    sendJSON(res, 200, { deleted: rel });
  } catch (err) {
    sendError(res, err);
  }
}

// ── Main router ──────────────────────────────────────────────────────────────

const server = http.createServer((req, res) => {
  // Parse URL
  let parsedUrl;
  try {
    parsedUrl = new URL(req.url, `http://localhost:${PORT}`);
  } catch {
    res.writeHead(400); res.end('Bad Request'); return;
  }

  const pathname = parsedUrl.pathname;
  const params   = parsedUrl.searchParams;
  const method   = req.method.toUpperCase();

  // CORS for local dev (optional but harmless)
  res.setHeader('X-Content-Type-Options', 'nosniff');

  if (method === 'GET' && pathname === '/') {
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    res.end(HTML);
    return;
  }

  if (method === 'GET' && pathname === '/api/tree') {
    handleGetTree(req, res);
    return;
  }

  if (method === 'GET' && pathname === '/api/file') {
    handleGetFile(req, res, params);
    return;
  }

  if (method === 'POST' && pathname === '/api/upload') {
    handleUpload(req, res, params);
    return;
  }

  if (method === 'DELETE' && pathname === '/api/file') {
    handleDeleteFile(req, res, params);
    return;
  }

  res.writeHead(404, { 'Content-Type': 'text/plain' });
  res.end('Not Found');
});

server.listen(PORT, '127.0.0.1', () => {
  console.log(`Artifact browser running at http://localhost:${PORT}`);
});

server.on('error', err => {
  if (err.code === 'EADDRINUSE') {
    console.error(`Error: port ${PORT} is already in use. Set ARTIFACT_BROWSER_PORT to a different port.`);
  } else {
    console.error('Server error:', err.message);
  }
  process.exit(1);
});
