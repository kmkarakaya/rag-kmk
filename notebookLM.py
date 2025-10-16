import os
import threading
import traceback
from flask import Flask, request, jsonify, send_file, Response

# Single-file NotebookLM-like MVP using rag_kmk public APIs.
# Binds to 127.0.0.1 only. No external files modified.

app = Flask(__name__, static_folder=None)

# In-memory session state (server-side objects are not JSON-serializable)
_session_collections = {}  # name -> {'obj': collection_obj, 'status': str, 'summary': str}
_selected_collection = {"name": None}

# Import rag_kmk public APIs using the same style as run.py
try:
    from rag_kmk import CONFIG
    from rag_kmk.knowledge_base import document_loader as kb_loader
except Exception:
    kb_loader = None

try:
    import rag_kmk.chat_flow as chat_flow
except Exception:
    chat_flow = None

# Import the vector_db database module to inspect ChromaDBStatus enums
try:
    from rag_kmk.vector_db import database as vdb_database
except Exception:
    vdb_database = None

# summarize_collection might live in knowledge_base or top-level; try common names.
_summarize_fn = None
try:
    from rag_kmk.vector_db import summarize_collection as _sc
    _summarize_fn = _sc
except Exception:
    try:
        from rag_kmk.knowledge_base import summarize_collection as _sc2
        _summarize_fn = _sc2
    except Exception:
        _summarize_fn = None


def _make_error(message, exc=None):
    detail = None
    if exc:
        detail = traceback.format_exc()
    return {"ok": False, "message": message, "trace": detail}


def _discover_persistent_collections():
    """Populate _session_collections with names found in the persistent chromaDB (best-effort).

    This runs at module import time so the UI can show available collections even before
    anyone explicitly "loads" them. Collections are added with obj=None to indicate they
    are known but not opened in memory yet. Selecting a collection will cause the server
    to attempt to open it using kb_loader.load_knowledge_base.
    """
    try:
        # Prefer explicit config from repo CONFIG; fall back to default ./chromaDB
        chroma_cfg = None
        try:
            chroma_cfg = CONFIG.get('vector_db', {}) if isinstance(CONFIG, dict) else None
        except Exception:
            chroma_cfg = None

        resolved = None
        if chroma_cfg and isinstance(chroma_cfg, dict):
            resolved = chroma_cfg.get('chromaDB_path')
        if not isinstance(resolved, str) or not resolved.strip():
            resolved = os.path.join(os.getcwd(), 'chromaDB')
        abs_path = os.path.abspath(resolved)

        if not os.path.isdir(abs_path):
            # Nothing to list
            return

        # Try to build a persistent chromadb client directly and list collections
        client = None
        try:
            import chromadb
            try:
                # modern API
                if hasattr(chromadb, 'PersistentClient'):
                    client = chromadb.PersistentClient(path=abs_path)
                else:
                    try:
                        from chromadb.config import Settings
                        settings = Settings(chroma_db_impl='duckdb+parquet', persist_directory=abs_path)
                        client = chromadb.Client(settings=settings)
                    except Exception:
                        client = None
            except Exception:
                client = None
        except Exception:
            client = None

        names = []
        if client is not None:
            try:
                if vdb_database is not None and hasattr(vdb_database, 'list_collection_names'):
                    names = vdb_database.list_collection_names(client)
                else:
                    # best effort fallback
                    raw = None
                    if hasattr(client, 'list_collections'):
                        raw = client.list_collections()
                    elif hasattr(client, 'collections'):
                        raw = client.collections
                    # normalize similar to vdb_database helper
                    if raw is not None:
                        if isinstance(raw, list):
                            for it in raw:
                                if isinstance(it, str):
                                    names.append(it)
                                else:
                                    names.append(getattr(it, 'name', None) or getattr(it, 'id', None))
                        elif isinstance(raw, dict):
                            for k in raw.keys():
                                names.append(str(k))
                        else:
                            if hasattr(raw, 'name'):
                                names.append(getattr(raw, 'name'))
                            elif hasattr(raw, 'id'):
                                names.append(getattr(raw, 'id'))
            except Exception:
                names = []

        # Add discovered names to session map (do not open them yet)
        for n in names:
            if not n:
                continue
            if n not in _session_collections:
                _session_collections[n] = {"obj": None, "status": "PERSISTENT", "summary": None, "chroma_status": "OK"}
    except Exception:
        # discovery must be best-effort; don't crash import
        print('[notebookLM] collection discovery failed:', traceback.format_exc())

# Discover persistent collections at import time so the UI can show them immediately
try:
    _discover_persistent_collections()
except Exception:
    pass


@app.route("/", methods=["GET"])
def index():
    # Minimal single-file UI
    html = r"""
<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <title>NotebookLM MVP</title>
  <style>
    body { font-family: Arial, sans-serif; margin:0; padding:0; height:100vh; display:flex; flex-direction:column; }
    header { background:#222; color:#fff; padding:10px 16px; }
    .container { display:flex; flex:1; }
    .left { width:320px; border-right:1px solid #ddd; padding:12px; box-sizing:border-box; }
    .right { flex:1; padding:12px; box-sizing:border-box; display:flex; flex-direction:column; }
    .collections { margin-top:12px; max-height:240px; overflow:auto; }
    .col-item { padding:6px; border:1px solid #eee; margin-bottom:6px; cursor:pointer; display:flex; justify-content:space-between; }
    .badge { font-size:12px; padding:2px 6px; border-radius:4px; background:#eee; }
    .chat { flex:1; border:1px solid #eee; padding:8px; margin-bottom:8px; overflow:auto; }
    .controls { display:flex; gap:6px; }
    .log { height:120px; overflow:auto; border:1px solid #eee; padding:6px; background:#fafafa; font-size:13px; }
    .row { margin-bottom:8px; }
    .summary { border:1px solid #eee; padding:8px; margin-bottom:8px; max-height:160px; overflow:auto; }
    .msg-user { color:#004; font-weight:600; }
    .msg-assist { color:#060; }
  </style>
</head>
<body>
  <header><h3 style="margin:0">NotebookLM MVP (local)</h3></header>
  <div class="container">
    <div class="left">
      <div>
        <div class="row"><strong>Create & Ingest</strong></div>
        <div class="row"><input id="create_name" placeholder="collection name" style="width:100%"/></div>
        <div class="row"><input id="create_path" placeholder="folder path (e.g. tests/sample_documents)" style="width:100%"/></div>
        <div class="row"><button onclick="createCollection()">Create & Ingest</button></div>
      </div>
      <hr/>
      <div>
        <div class="row"><strong>Load existing</strong></div>
        <div class="row"><input id="load_name" placeholder="collection name" style="width:100%"/></div>
        <div class="row"><button onclick="loadCollection()">Load</button></div>
      </div>
      <hr/>
      <div>
        <div class="row"><strong>Collections</strong> <button onclick="refreshCollections()">Refresh</button></div>
        <div class="collections" id="collections"></div>
      </div>
    </div>
    <div class="right">
      <div style="display:flex; gap:12px; align-items:flex-start;">
        <div style="flex:1">
          <div class="summary" id="summary">No collection selected.</div>
          <div class="chat" id="chatbox"></div>
          <div style="display:flex; gap:6px;">
            <input id="query" placeholder="Ask a question..." style="flex:1"/>
            <button onclick="sendChat()">Send</button>
          </div>
        </div>
        <div style="width:320px;">
          <div><strong>Logs & Status</strong></div>
          <div class="log" id="log"></div>
          <div style="margin-top:8px;">
            <button onclick="unloadSelected()">Unload Selected</button>
            <button onclick="summarizeSelected()">Refresh Summary</button>
          </div>
        </div>
      </div>
    </div>
  </div>

<script>
let selected = null;

function log(msg) {
  const el = document.getElementById('log');
  const time = new Date().toLocaleTimeString();
  el.innerText = `[${time}] ${msg}\n` + el.innerText;
}

function refreshCollections(){
  fetch('/api/collections').then(r=>r.json()).then(j=>{
    if(!j.ok){ log('Error fetching collections: '+j.message); return; }
    const container = document.getElementById('collections');
    container.innerHTML = '';
    j.collections.forEach(c=>{
      const div = document.createElement('div');
      div.className = 'col-item';
      div.onclick = ()=>selectCollection(c.name);
      div.innerHTML = `<span>${c.name}</span><span class="badge">${c.status}</span>`;
      if(c.name === j.selected) div.style.background = '#eef';
      container.appendChild(div);
    });
    selected = j.selected;
    if(selected) loadSummary(selected);
  }).catch(e=>log('Exception: '+e));
}

function createCollection(){
  const name = document.getElementById('create_name').value.trim();
  const path = document.getElementById('create_path').value.trim();
  if(!name){ alert('Collection name required'); return; }
  if(!path || path.length===0){ alert('Folder path required'); return; }
  log('Creating '+name+' from '+path);
  fetch('/api/create',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({collection_name:name, document_directory_path:path})})
    .then(r=>r.json()).then(j=>{
      if(j.ok){ log('Create success: '+j.message); refreshCollections(); }
      else { log('Create error: '+j.message); alert('Create error: '+j.message); }
    });
}

function loadCollection(){
  const name = document.getElementById('load_name').value.trim();
  if(!name){ alert('Collection name required'); return; }
  fetch('/api/load',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({collection_name:name})})
    .then(r=>r.json()).then(j=>{
      if(j.ok){ log('Load success: '+j.message); refreshCollections(); }
      else { log('Load error: '+j.message); alert('Load error: '+j.message); }
    });
}

function selectCollection(name){
  fetch('/api/select',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({collection_name:name})})
    .then(r=>r.json()).then(j=>{
      if(!j.ok){ log('Select error: '+j.message); return; }
      selected = name;
      refreshCollections();
      loadSummary(name);
    });
}

function loadSummary(name){
  fetch('/api/summarize',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({collection_name:name})})
    .then(r=>r.json()).then(j=>{
      const s = document.getElementById('summary');
      if(j.ok){ s.innerText = j.summary || 'No summary available.'; log('Summary refreshed for '+name); }
      else { s.innerText = 'Summary error: '+j.message; log('Summary error: '+j.message); }
    });
}

function summarizeSelected(){
  if(!selected){ alert('No collection selected'); return; }
  loadSummary(selected);
}

function sendChat(){
  const q = document.getElementById('query').value.trim();
  if(!q){ return; }
  if(!selected){ alert('Select a collection first'); return; }
  appendChat('You', q, 'msg-user');
  document.getElementById('query').value = '';
  fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({collection_name:selected, query:q})})
    .then(r=>r.json()).then(j=>{
      if(j.ok){
        appendChat('Assistant', j.answer || '(no answer)', 'msg-assist');
        log('Chat OK');
      } else {
        appendChat('Assistant', 'Error: '+j.message, 'msg-assist');
        log('Chat error: '+j.message);
      }
    }).catch(e=>{ appendChat('Assistant', 'Exception: '+e, 'msg-assist'); log('Chat exception: '+e); });
}

function appendChat(who, text, cls){
  const cb = document.getElementById('chatbox');
  const p = document.createElement('div');
  p.innerHTML = '<div class="'+cls+'">'+who+':</div><div>'+text.replace(/\n/g,'<br/>')+'</div><hr/>';
  cb.appendChild(p);
  cb.scrollTop = cb.scrollHeight;
}

function unloadSelected(){
  if(!selected){ alert('No collection selected'); return; }
  fetch('/api/unload',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({collection_name:selected})})
    .then(r=>r.json()).then(j=>{
      if(j.ok){ log('Unloaded '+selected); selected=null; refreshCollections(); document.getElementById('summary').innerText='No collection selected.'; }
      else { log('Unload error: '+j.message); alert('Unload error: '+j.message); }
    });
}

// initial load
refreshCollections();
</script>
</body>
</html>
"""
    return Response(html, mimetype="text/html")


@app.route("/api/collections", methods=["GET"])
def api_collections():
    try:
        cols = []
        for name, meta in _session_collections.items():
            cols.append({"name": name, "status": meta.get("status", "UNKNOWN")})
        return jsonify({"ok": True, "collections": cols, "selected": _selected_collection["name"]})
    except Exception as e:
        return jsonify(_make_error("Failed to list collections", e))


@app.route("/api/create", methods=["POST"])
def api_create():
    data = request.get_json() or {}
    name = (data.get("collection_name") or "").strip()
    path = (data.get("document_directory_path") or "").strip()
    if not name:
        return jsonify(_make_error("collection_name is required"))
    if not path:
        return jsonify(_make_error("document_directory_path is required"))
    if not os.path.isdir(path):
        return jsonify(_make_error(f"document_directory_path does not exist: {path}"))
    if name in _session_collections:
        return jsonify(_make_error(f"Collection already in session: {name}"))
    if kb_loader is None or not hasattr(kb_loader, "build_knowledge_base"):
        return jsonify(_make_error("kb_loader.build_knowledge_base not available in rag_kmk"))

    try:
        # build_knowledge_base(collection_name, document_directory_path, add_documents=True)
        res = kb_loader.build_knowledge_base(name, path, add_documents=True)
        # build_knowledge_base may return (collection, status) or just collection
        if isinstance(res, tuple) and len(res) >= 1:
            col = res[0]
            chroma_status = res[1] if len(res) > 1 else None
        else:
            col = res
            chroma_status = None
        # Normalize status and compare against known enums when available
        status_name = None
        try:
            if vdb_database is not None and hasattr(vdb_database, 'ChromaDBStatus') and chroma_status is not None:
                status_name = chroma_status
            else:
                status_name = getattr(chroma_status, 'name', str(chroma_status)) if chroma_status is not None else None
        except Exception:
            status_name = str(chroma_status)

        # If collection already exists, try to open it instead of failing
        already_exists = False
        try:
            if vdb_database is not None and hasattr(vdb_database, 'ChromaDBStatus'):
                already_exists = chroma_status == vdb_database.ChromaDBStatus.ALREADY_EXISTS
            else:
                already_exists = str(status_name) == 'ALREADY_EXISTS'
        except Exception:
            already_exists = False

        if already_exists:
            try:
                loaded = kb_loader.load_knowledge_base(name)
                if isinstance(loaded, tuple) and len(loaded) >= 1:
                    col = loaded[0]
                    chroma_status = loaded[1] if len(loaded) > 1 else chroma_status
                else:
                    col = loaded
                if col is None:
                    return jsonify(_make_error(f"Collection '{name}' already exists but could not be opened. Status: {status_name}"))
            except Exception as e:
                return jsonify(_make_error(f"Collection '{name}' already exists but failed to open: {e}", e))

        # If collection creation returned no collection, treat as error
        if col is None:
            return jsonify(_make_error(f"Failed to create/ingest collection '{name}'; status={status_name}"))

        _session_collections[name] = {"obj": col, "status": "LOADED", "summary": None, "chroma_status": (getattr(status_name, 'name', str(status_name)) if status_name is not None else None)}
        _selected_collection["name"] = name
        return jsonify({"ok": True, "message": f"Collection '{name}' created and ingested.", "status": (getattr(status_name, 'name', str(status_name)) if status_name is not None else None)})
    except Exception as e:
        return jsonify(_make_error(f"Failed to create/ingest collection: {e}", e))


@app.route("/api/load", methods=["POST"])
def api_load():
    data = request.get_json() or {}
    name = (data.get("collection_name") or "").strip()
    if not name:
        return jsonify(_make_error("collection_name is required"))
    if name in _session_collections:
        return jsonify(_make_error(f"Collection already in session: {name}"))
    if kb_loader is None or not hasattr(kb_loader, "load_knowledge_base"):
        return jsonify(_make_error("kb_loader.load_knowledge_base not available in rag_kmk"))
    try:
        res = kb_loader.load_knowledge_base(name)
        if isinstance(res, tuple) and len(res) >= 1:
            col = res[0]
            chroma_status = res[1] if len(res) > 1 else None
        else:
            col = res
            chroma_status = None
        status_name = None
        try:
            if vdb_database is not None and hasattr(vdb_database, 'ChromaDBStatus'):
                status_name = chroma_status
            else:
                status_name = getattr(chroma_status, 'name', str(chroma_status)) if chroma_status is not None else None
        except Exception:
            status_name = str(chroma_status)

        if col is None:
            # Provide specific guidance for missing persistent DB
            try:
                if vdb_database is not None and hasattr(vdb_database, 'ChromaDBStatus') and chroma_status == vdb_database.ChromaDBStatus.MISSING_PERSISTENT:
                    return jsonify(_make_error(f"Persistent chromaDB path missing or collection '{name}' not found (MISSING_PERSISTENT)."))
                if str(status_name) == 'MISSING_PERSISTENT':
                    return jsonify(_make_error(f"Persistent chromaDB path missing or collection '{name}' not found (MISSING_PERSISTENT)."))
            except Exception:
                pass
            return jsonify(_make_error(f"Failed to load collection '{name}'; status={status_name}"))

        _session_collections[name] = {"obj": col, "status": "LOADED", "summary": None, "chroma_status": (getattr(status_name, 'name', str(status_name)) if status_name is not None else None)}
        _selected_collection["name"] = name
        return jsonify({"ok": True, "message": f"Collection '{name}' loaded.", "status": status_name})
    except Exception as e:
        return jsonify(_make_error(f"Failed to load collection: {e}", e))


@app.route("/api/select", methods=["POST"])
def api_select():
    data = request.get_json() or {}
    name = (data.get("collection_name") or "").strip()
    if not name:
        return jsonify(_make_error("collection_name is required"))
    if name not in _session_collections:
        return jsonify(_make_error("Collection not in session"))

    # If the collection was discovered but not yet opened, attempt to load it now
    meta = _session_collections.get(name)
    if meta and meta.get('obj') is None:
        # Attempt to open using kb_loader.load_knowledge_base
        if kb_loader is None or not hasattr(kb_loader, 'load_knowledge_base'):
            return jsonify(_make_error("Collection known but loader unavailable to open it."))
        try:
            loaded = kb_loader.load_knowledge_base(name)
            if isinstance(loaded, tuple) and len(loaded) >= 1:
                col = loaded[0]
                chroma_status = loaded[1] if len(loaded) > 1 else None
            else:
                col = loaded
                chroma_status = None
            if col is None:
                return jsonify(_make_error(f"Failed to open collection '{name}' from persistent store; status={chroma_status}"))
            meta['obj'] = col
            meta['status'] = 'LOADED'
            meta['chroma_status'] = (getattr(chroma_status, 'name', str(chroma_status)) if chroma_status is not None else None)
        except Exception as e:
            return jsonify(_make_error(f"Failed to open collection '{name}': {e}", e))

    _selected_collection["name"] = name
    return jsonify({"ok": True, "message": f"Selected {name}"})


@app.route("/api/summarize", methods=["POST"])
def api_summarize():
    data = request.get_json() or {}
    name = (data.get("collection_name") or "").strip()
    if not name:
        return jsonify(_make_error("collection_name is required"))
    meta = _session_collections.get(name)
    if not meta:
        return jsonify(_make_error("Collection not in session"))
    col_obj = meta.get("obj")
    if _summarize_fn is None:
        return jsonify(_make_error("summarize_collection not available in rag_kmk"))
    try:
        summary = _summarize_fn(col_obj)
        meta["summary"] = summary
        return jsonify({"ok": True, "summary": summary})
    except Exception as e:
        return jsonify(_make_error(f"Failed to summarize collection: {e}", e))


@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.get_json() or {}
    name = (data.get("collection_name") or "").strip()
    query = (data.get("query") or "").strip()
    if not name:
        return jsonify(_make_error("collection_name is required"))
    if not query:
        return jsonify(_make_error("query is required"))
    meta = _session_collections.get(name)
    if not meta:
        return jsonify(_make_error("Collection not in session"))
    col_obj = meta.get("obj")

    if chat_flow is None or not hasattr(chat_flow, "build_chatBot"):
        return jsonify(_make_error("chat_flow.build_chatBot not available in rag_kmk"))

    # Optionally refresh/compute the collection summary as run.py demonstrates summarization
    try:
        if _summarize_fn is not None:
            try:
                meta_summary = _summarize_fn(col_obj)
                meta['summary'] = meta_summary
            except Exception as e:
                # Summarization is optional for chat; log and continue
                print(f"[notebookLM] summarize_collection failed: {e}")
    except Exception:
        pass

    # Build client using repository CONFIG (same style as run.py)
    client = None
    try:
        client = chat_flow.build_chatBot(CONFIG.get('llm', {}))
    except Exception as e:
        return jsonify(_make_error(f"Failed to build LLM client: {e}", e))

    try:
        ans = None

        # Prefer the canonical pipeline from run.py: run_rag_pipeline(client, kb)
        if hasattr(chat_flow, 'run_rag_pipeline'):
            try:
                try:
                    ans = chat_flow.run_rag_pipeline(client, col_obj)
                except TypeError:
                    # if signature accepts flags, prefer non-interactive
                    try:
                        ans = chat_flow.run_rag_pipeline(client, col_obj, non_interactive=True)
                    except Exception:
                        ans = chat_flow.run_rag_pipeline(client, col_obj)
                print('[notebookLM] run_rag_pipeline returned type:', type(ans))
            except Exception as e:
                print('[notebookLM] run_rag_pipeline failed:', e)
                ans = None

        # If pipeline did not return answer, try the single-query helper generateAnswer
        if ans is None and hasattr(chat_flow, 'generateAnswer'):
            try:
                ans = chat_flow.generateAnswer(client, chroma_collection=col_obj, query=query)
                print('[notebookLM] generateAnswer returned type:', type(ans))
            except Exception as e:
                print('[notebookLM] generateAnswer failed:', e)
                ans = None

        # Final fallback: direct LLM prompt API
        if ans is None:
            try:
                from rag_kmk.chat_flow import generate_LLM_answer
                prompt = f"QUESTION: {query}\n"
                ans = generate_LLM_answer(client, prompt)
                print('[notebookLM] generate_LLM_answer returned type:', type(ans))
            except Exception as e:
                print('[notebookLM] generate_LLM_answer failed:', e)
                return jsonify(_make_error("LLM pipeline not available; cannot produce answer."))

        # Unwrap common container return shapes and coerce to string
        try:
            if ans is None:
                ans_str = '(no answer)'
            elif isinstance(ans, str):
                ans_str = ans
            elif isinstance(ans, (list, tuple)) and len(ans) > 0:
                # Sometimes pipelines return (answer, meta)
                first = ans[0]
                ans_str = first if isinstance(first, str) else str(first)
            elif isinstance(ans, dict) and 'answer' in ans:
                a = ans.get('answer')
                ans_str = a if isinstance(a, str) else str(a)
            else:
                ans_str = str(ans)
        except Exception:
            ans_str = '(no answer)'

        # server-side log
        print(f"[notebookLM] Chat answer (len={len(ans_str) if ans_str else 0}): {ans_str[:200]}")
        return jsonify({"ok": True, "answer": ans_str})
    except Exception as e:
        return jsonify(_make_error(f"Error during chat: {e}", e))
    finally:
        try:
            if client and hasattr(client, 'close'):
                client.close()
        except Exception:
            pass
    


@app.route("/api/unload", methods=["POST"])
def api_unload():
    data = request.get_json() or {}
    name = (data.get("collection_name") or "").strip()
    if not name:
        return jsonify(_make_error("collection_name is required"))
    if name in _session_collections:
        try:
            obj = _session_collections[name].get("obj")
            if hasattr(obj, "close"):
                try:
                    obj.close()
                except Exception:
                    pass
            del _session_collections[name]
            if _selected_collection["name"] == name:
                _selected_collection["name"] = None
            return jsonify({"ok": True, "message": f"Unloaded {name}"})
        except Exception as e:
            return jsonify(_make_error(f"Failed to unload collection: {e}", e))
    return jsonify(_make_error("Collection not in session"))

def _run_server(host="127.0.0.1", port=5005):
    # Ensure only localhost binding
    app.run(host=host, port=port, debug=False, threaded=True)

if __name__ == "__main__":
    import argparse
    import webbrowser
    parser = argparse.ArgumentParser(description="NotebookLM MVP (single-file)")
    parser.add_argument("--port", type=int, default=5005, help="Port to bind (127.0.0.1 only)")
    parser.add_argument("--open", action="store_true", help="Open default browser after server starts")
    args = parser.parse_args()

    host = "127.0.0.1"
    port = args.port

    if args.open:
        # Start server in a background thread and open the browser
        server_thread = threading.Thread(target=_run_server, kwargs={"host": host, "port": port}, daemon=True)
        server_thread.start()
        url = f"http://{host}:{port}"
        try:
            # Try to open the default browser
            webbrowser.open(url)
            print(f"Opened browser to {url}")
        except Exception:
            print(f"Server running at {url} (failed to auto-open browser)")
        # Keep main thread alive while server is running
        try:
            server_thread.join()
        except KeyboardInterrupt:
            print("Shutting down...")
    else:
        print(f"Starting NotebookLM MVP on http://{host}:{port}")
        _run_server(host=host, port=port)
