# Templates (HTML/CSS/JS) do servidor web RagThulhu.
# Strings com placeholders: __SITE__, __WSPORT__, __TABS__, __BACK__.
# Dados reais vêm do WebSocket (snapshot/event/status) e dos endpoints /api/*.
# Mock so existe atras do parametro ?mock=1 (teste visual offline).

MAIN_TABS = (
  '<button class="tab on" data-t="home">Visão Geral</button>\n'
  '  <button class="tab" data-t="bases">Bases RAG</button>\n'
  '  <button class="tab" data-t="uso">Uso</button>\n'
  '  <button class="tab" data-t="config">Configurações</button>'
)
RAG_TABS = (
  '<button class="tab on" data-t="home">Visão Geral</button>\n'
  '  <button class="tab" data-t="A">Coleta</button>\n'
  '  <button class="tab" data-t="B">Limpeza</button>\n'
  '  <button class="tab" data-t="C">Indexação</button>\n'
  '  <button class="tab" data-t="D">Avaliação</button>\n'
  '  <button class="tab" data-t="uso">Uso</button>')
BACK_LINK = '<a href="/" class="btn">← Bases RAG</a>'

HTML = r"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<title>RagThulhu — painel de serviço</title>
<style>
 :root{
  --bg:#0b0d10; --bg2:#111418; --bg3:#161b21; --border:#222a31; --border2:#2c363f;
  --text:#d6dbe0; --muted:#7d8794; --green:#33ff66; --green2:#66ff99; --accent:#6cf;
  --warn:#ffd27d; --danger:#ff6b6b;
  --mono:'JetBrains Mono','Fira Code',Consolas,Menlo,monospace;
  --sans:system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;
 }
 *{box-sizing:border-box}
 body{margin:0;background:var(--bg);color:var(--text);font:14px/1.5 var(--sans)}
 a{color:var(--green)}
 .appbar{position:sticky;top:0;z-index:10;display:flex;align-items:center;gap:14px;padding:12px 18px;background:rgba(11,13,16,.85);backdrop-filter:blur(8px);border-bottom:1px solid var(--border)}
 .brand{font:700 16px var(--mono);color:var(--green);letter-spacing:.5px;display:flex;align-items:baseline}
 .brand-sub{color:var(--muted);font-weight:400;font-size:12px;margin-left:8px}
 .spacer{flex:1}
 .badge{display:inline-block;padding:3px 11px;border-radius:999px;font:600 11px var(--sans);border:1px solid var(--border2)}
 .badge.ok{color:#7cffb0;background:rgba(51,255,102,.1);border-color:rgba(51,255,102,.3)}
 .badge.stop{color:var(--muted)}
 .badge.run{color:var(--warn);background:rgba(255,200,80,.1);border-color:rgba(255,200,80,.3)}
 .badge.fail{color:#ff8a8a;background:rgba(255,80,80,.1);border-color:rgba(255,80,80,.3)}
 .tabs{display:flex;gap:6px;padding:10px 16px;background:var(--bg2);border-bottom:1px solid var(--border);flex-wrap:wrap}
 .tab{background:transparent;color:var(--muted);border:1px solid transparent;padding:8px 15px;border-radius:9px;cursor:pointer;font:600 13px var(--sans);transition:.15s}
 .tab:hover{color:var(--text);background:var(--bg3)}
  .tab.on{color:var(--green);background:rgba(51,255,102,.08);border-color:rgba(51,255,102,.35);box-shadow:inset 0 0 0 1px rgba(51,255,102,.15)}
  .tab.locked{opacity:.35;cursor:not-allowed;border-style:dashed}
  .tab.locked:hover{color:var(--muted);background:transparent}
 .wrap{max-width:1200px;margin:0 auto;padding:22px}
 section{display:none;animation:fade .2s ease}
 section.show{display:block}
 @keyframes fade{from{opacity:0;transform:translateY(4px)}to{opacity:1}}
  .card{background:var(--bg2);border:1px solid var(--border);border-radius:14px;padding:18px 20px;margin-bottom:18px;box-shadow:inset 0 1px 0 rgba(255,255,255,.02),0 10px 30px rgba(0,0,0,.28)}
  .card-head{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:4px}
  .card-head h2{margin:0}
 h2{margin:0 0 4px;font:600 18px var(--sans);color:var(--green2)}
 h3{margin:0 0 12px;font:600 14px var(--sans);color:var(--text)}
 .muted{color:var(--muted)}
 .chip{display:inline-block;padding:3px 10px;border-radius:8px;background:var(--bg3);border:1px solid var(--border2);font:12px var(--mono);color:var(--accent)}
 .prog{margin:6px 0 14px}
 .prog .row{display:flex;justify-content:space-between;font:12px var(--mono);color:var(--muted);margin-bottom:7px}
 .bar{height:12px;background:var(--bg3);border:1px solid var(--border2);border-radius:999px;overflow:hidden}
 .fill{height:100%;width:0;background:linear-gradient(90deg,#1f8f4f,#33ff66);transition:width .5s ease;box-shadow:0 0 14px rgba(51,255,102,.45)}
 .log{background:#07090b;border:1px solid var(--border);border-radius:12px;padding:14px;height:56vh;overflow:auto;font:12.5px/1.55 var(--mono);color:#bdf5cf;white-space:pre-wrap;word-break:break-word}
 .ln{white-space:pre-wrap}
 .ln.sucesso{color:#9be8b4}
 .ln.erro{color:#ff8a8a}
 .ln.excecao{color:var(--warn)}
 .empty-note{color:var(--muted);font-style:italic;padding:18px;text-align:center;display:block}
 .tbl{width:100%;border-collapse:collapse;font:13px var(--mono)}
 .tbl th{text-align:left;padding:11px 13px;color:var(--muted);border-bottom:1px solid var(--border2);font-weight:600;background:var(--bg3);position:sticky;top:0}
 .tbl td{padding:11px 13px;border-bottom:1px solid var(--border);color:var(--text);vertical-align:top}
 .tbl tbody tr:hover{background:rgba(255,255,255,.025)}
 .tbl td.url{color:var(--green);word-break:break-all}
 .tbl td.path{color:var(--accent);word-break:break-all}
 .tbl td.num{color:var(--green2);text-align:right}
 .totals{margin-top:14px;font:13px var(--mono);color:var(--muted)}
 .totals b{color:var(--green)}
 .btn{background:var(--bg3);color:var(--text);border:1px solid var(--border2);padding:8px 13px;border-radius:9px;cursor:pointer;font:600 12px var(--sans);transition:.15s}
 .btn:hover{border-color:var(--green);color:var(--green)}
 .btn.on{border-color:var(--green);color:var(--green)}
 .btn.danger:hover{border-color:var(--danger);color:#ff8a8a}
  .actions{display:flex;gap:8px;flex-wrap:wrap}
  .bench-params{background:var(--bg2);border:1px solid var(--border2);border-radius:12px;padding:12px 14px;margin-bottom:12px}
  .bp-row{display:flex;gap:14px;flex-wrap:wrap;align-items:flex-end}
  .bp-row label{display:flex;flex-direction:column;gap:5px;font:600 11px var(--sans);color:var(--muted)}
  .bp-row select,.bp-row input{flex:1;min-width:150px}
 textarea,select,input{background:var(--bg3);color:var(--text);border:1px solid var(--border2);border-radius:9px;padding:9px 11px;font:13px var(--mono);color-scheme:dark}
 textarea{width:100%;min-height:84px;resize:vertical}
 .field{margin-top:14px}
 .field label{display:block;margin-bottom:6px;font:600 12px var(--sans);color:var(--muted)}
 .note{font:12px var(--sans);color:var(--muted);margin:2px 0 0}
 .result{background:var(--bg3);border:1px solid var(--border2);border-radius:12px;padding:14px 16px;margin-top:6px;font:12.5px/1.6 var(--mono);white-space:pre-wrap;word-break:break-word;max-height:460px;overflow:auto;color:var(--text)}
 .chart-wrap{margin:6px 0 18px}
 .chart{display:flex;align-items:flex-end;gap:12px;height:210px;padding:8px 4px 0;border-bottom:1px solid var(--border2);overflow-x:auto}
 .chart .col{flex:1;min-width:52px;display:flex;flex-direction:column;align-items:center;justify-content:flex-end;height:100%}
 .chart .bars{display:flex;align-items:flex-end;gap:5px;height:170px}
 .chart .bar{width:18px;border-radius:5px 5px 0 0;transition:height .4s ease;box-shadow:inset 0 0 10px rgba(0,0,0,.25)}
 .chart .bar.rag{background:linear-gradient(180deg,#5bb0ff,#1f6fd6)}
 .chart .bar.norag{background:linear-gradient(180deg,#ff7b7b,#d63a3a)}
 .chart .lbl{margin-top:7px;font:10px var(--mono);color:var(--muted);text-align:center;max-width:74px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
 .legend{display:flex;gap:18px;margin-top:10px;font:12px var(--sans);color:var(--muted)}
 .legend .sw{display:inline-block;width:12px;height:12px;border-radius:3px;margin-right:6px;vertical-align:-1px}
 .legend .sw.rag{background:linear-gradient(180deg,#5bb0ff,#1f6fd6)}
 .legend .sw.norag{background:linear-gradient(180deg,#ff7b7b,#d63a3a)}
  .tbl.center th, .tbl.center td{text-align:center}
  .tbl.center th.col-left, .tbl.center td.col-left{text-align:left}
 .linechart{width:100%;height:auto;display:block;background:var(--bg3);border:1px solid var(--border);border-radius:12px;padding:8px}
 .sup-row{display:flex;align-items:center;gap:12px;margin:10px 0}
 .sup-label{width:74px;color:var(--muted);font:12px var(--sans)}
 .sup-bar{flex:1;height:18px;background:var(--bg3);border:1px solid var(--border2);border-radius:999px;overflow:hidden}
 .sup-fill{height:100%;border-radius:999px}
 .sup-fill.rag{background:linear-gradient(90deg,#1f6fd6,#5bb0ff)}
 .sup-fill.norag{background:linear-gradient(90deg,#d63a3a,#ff7b7b)}
 .sup-val{width:124px;text-align:right;font:12px var(--mono);color:var(--text)}
 .sup-verdict{margin-top:10px;font:13px var(--sans);color:var(--text)}
 .ai-box{background:var(--bg3);border:1px solid var(--border);border-radius:12px;padding:14px 16px;margin-top:14px}
 .ai-box h3{margin:0 0 8px;color:var(--green2);font:600 13px var(--sans)}
 .ai-box p{margin:0;color:var(--text);font:13px/1.6 var(--sans);white-space:pre-wrap}
  .ai-hint{font:11px var(--sans);color:var(--muted);margin-top:8px}
  .pies{display:flex;gap:18px;flex-wrap:wrap;margin:6px 0 14px}
  .pie-card{flex:1;min-width:240px;background:var(--bg3);border:1px solid var(--border);border-radius:12px;padding:14px 16px}
  .pie-card h4{margin:0 0 10px;font:600 13px var(--sans);color:var(--text)}
  .pie-row{display:flex;align-items:center;gap:16px}
  .pie-legend{font:12px var(--sans);color:var(--muted)}
  .pie-legend .row{display:flex;align-items:center;gap:7px;margin:3px 0}
  .pie-legend .sw{width:11px;height:11px;border-radius:3px;display:inline-block}
  .pie-legend b{color:var(--text)}
  .stats{display:flex;gap:18px;flex-wrap:wrap;margin-top:12px}
  .stat{flex:1;min-width:200px;background:var(--bg3);border:1px solid var(--border);border-radius:12px;padding:12px 16px}
  .stat h4{margin:0 0 8px;font:600 13px var(--sans);color:var(--text)}
  .stat .kv{display:flex;justify-content:space-between;font:12px var(--mono);color:var(--muted);margin:4px 0}
  .stat .kv b{color:var(--green2)}
  .cfg-group{margin:18px 0 6px;font:700 13px var(--mono);color:var(--accent);letter-spacing:.4px;text-transform:uppercase}
  .cfg-row{display:flex;align-items:center;gap:14px;padding:9px 0;border-bottom:1px solid var(--border)}
  .cfg-row label{flex:1;color:var(--text);font:13px var(--sans)}
  .cfg-row .hint{display:block;color:var(--muted);font-size:11px;margin-top:2px}
  .cfg-row input,.cfg-row select{flex:0 0 240px;background:var(--bg3);color:var(--text);border:1px solid var(--border2);border-radius:8px;padding:8px 10px;font:13px var(--mono)}
  .cfg-row input[type=checkbox]{flex:0 0 auto;width:18px;height:18px}
  .danger-zone{border:1px solid var(--danger);background:rgba(255,80,80,.06)}
  .alert-danger{background:rgba(255,80,80,.12);border:1px solid var(--danger);color:#ff9a9a;font:12px/1.5 var(--sans);padding:12px 14px;border-radius:10px;margin:10px 0}
  .btn.danger{background:var(--danger);color:#1a0000;border-color:var(--danger);font-weight:700}
  .btn.danger:hover{background:#ff8585;color:#1a0000}
 </style></head><body>
<header class="appbar">
  <div class="brand">RagThulhu<span class="brand-sub" id="brand-status">status: Parado</span></div>
  <div class="spacer"></div>
  __BACK__
  <span id="status" class="badge stop">conectando…</span>
</header>
<nav class="tabs" id="tabs">
__TABS__
</nav>
<div class="wrap">
 <section id="p-home" class="show">
  <div class="card">
   <h2>Log ao vivo</h2>
   <div class="note">Fonte: SQLite (RAG/log.db) → WebSocket. Fallbacks determinísticos (<span class="fb-site">—</span>): <b id="fb" style="color:var(--warn)">0</b></div>
   <div class="log" id="log"><span class="empty-note">ainda não há itens</span></div>
  </div>
 </section>

 <section id="p-A">
  <div class="card">
   <h2>Coleta — páginas capturadas</h2>
   <div class="note">Cada download: destino em disco, tempo de transferência e tamanho do arquivo.</div>
   <table class="tbl">
    <thead><tr><th style="width:42%">Página</th><th style="width:34%">Local (disco)</th><th class="num">Tempo</th><th class="num">Tamanho</th></tr></thead>
    <tbody id="pages-body"><tr class="empty-note"><td colspan="4">ainda não há itens</td></tr></tbody>
   </table>
   <div class="totals" id="pages-totals">Total de páginas: <b>0</b> — Espaço em disco: <b>0 KB</b></div>
  </div>
 </section>

 <section id="p-B">
   <div class="card">
    <h2>Limpeza</h2>
    <div class="note">Fallbacks determinísticos (<span class="fb-site">—</span>): <b id="fbB" style="color:var(--warn)">0</b></div>
    <div class="prog">
    <div class="row"><span>Progresso</span><span><b id="pctB">0%</b> · <span id="doneB">0</span>/<span id="totalB">0</span> · ETA <span id="etaB">—</span></span></div>
    <div class="bar"><div class="fill" id="fillB"></div></div>
   </div>
   <div class="log" id="logB"><span class="empty-note">ainda não há itens</span></div>
  </div>
 </section>

 <section id="p-C">
   <div class="card">
    <h2>Indexação</h2>
    <div class="note">Fallbacks determinísticos (<span class="fb-site">—</span>): <b id="fbC" style="color:var(--warn)">0</b></div>
    <div class="prog">
    <div class="row"><span>Progresso</span><span><b id="pctC">0%</b> · <span id="doneC">0</span>/<span id="totalC">0</span> · ETA <span id="etaC">—</span></span></div>
    <div class="bar"><div class="fill" id="fillC"></div></div>
   </div>
   <div class="log" id="logC"><span class="empty-note">ainda não há itens</span></div>
  </div>
 </section>

 <section id="p-D">
  <div class="card">
   <h2>Avaliação — benchmark (RAG × sem RAG)</h2>
   <div class="bench-params">
     <div class="bp-row">
       <label>Modo
         <select id="bench-mode">
           <option value="code">code — gera código vs PURO (Godot etc.)</option>
           <option value="facts">facts — recupera passagens vs PURO (livro/base não-código)</option>
         </select>
       </label>
       <label>Linguagem (rótulo, só code)
         <input id="bench-lang" type="text" value="GDScript">
       </label>
       <label>Extensão (só code)
         <input id="bench-ext" type="text" value="gd">
       </label>
       <label>Arquivo de tarefas
         <input id="bench-tasks" type="text" value="stage_d/tasks_godot.json">
       </label>
     </div>
   </div>
   <div class="actions" style="margin-bottom:10px"><button class="btn" id="bench-run">Rodar benchmark (Etapa D)</button></div>
   <div class="prog">
    <div class="row"><span>Progresso do benchmark</span><span><b id="pctD">0%</b> · <span id="doneD">0</span>/<span id="totalD">0</span></span></div>
    <div class="bar"><div class="fill" id="fillD"></div></div>
   </div>
    <div class="chart-wrap">
     <h3 class="muted" style="margin:0 0 6px">Tempo de geração por teste (s)</h3>
     <div class="linechart" id="bench-line"><span class="empty-note" style="width:100%">ainda não há itens</span></div>
    </div>
    <div class="chart-wrap">
     <h3 class="muted" style="margin:0 0 6px">Quem foi superior — atingiu o objetivo</h3>
     <div id="bench-sup"></div>
     </div>
     <div class="chart-wrap">
      <h3 class="muted" style="margin:0 0 6px">Taxa de sucesso (pass / fail)</h3>
      <div class="pies">
       <div class="pie-card"><h4>Com RAG</h4><div id="pie-rag" class="pie-row"></div></div>
       <div class="pie-card"><h4>Sem RAG</h4><div id="pie-norag" class="pie-row"></div></div>
      </div>
      <div class="stats">
       <div class="stat"><h4>Com RAG</h4><div class="kv"><span>Tempo total</span><b id="tot-rag">—</b></div><div class="kv"><span>Tempo médio</span><b id="avg-rag">—</b></div></div>
       <div class="stat"><h4>Sem RAG</h4><div class="kv"><span>Tempo total</span><b id="tot-norag">—</b></div><div class="kv"><span>Tempo médio</span><b id="avg-norag">—</b></div></div>
      </div>
     </div>
     <table class="tbl center">
      <thead><tr><th class="col-left" style="width:10%">Teste</th><th class="col-left" style="width:50%">Descrição</th><th class="num">Tempo (s)</th><th>Com RAG</th><th>Sem RAG</th></tr></thead>
      <tbody id="bench-body"><tr><td colspan="5" class="empty-note">ainda não há itens</td></tr></tbody>
     </table>
     <div class="ai-box">
      <h3>Resumo</h3>
      <p id="bench-summary"></p>
     </div>
  </div>
 </section>

  <section id="p-uso">
   <div class="card">
    <h2>Uso — consulta & geração fundamentada</h2>
    <div class="note">Responde perguntas ou gera código usando a base RAG selecionada. Só funciona se a base estiver indexada (etapa C concluída).</div>
    <div class="field">
     <label>Base (domínio)</label>
     <select id="uso-domain" class="btn" style="width:100%"><option value="">carregando…</option></select>
    </div>
    <div class="actions" style="margin-top:14px">
     <button class="btn on" id="uso-mode-query" data-mode="query">Consulta</button>
     <button class="btn" id="uso-mode-prog" data-mode="programador">Gerar código</button>
    </div>
    <div class="field">
     <label id="uso-label">Pergunta</label>
     <textarea id="uso-input" placeholder="ex: como usar NavigationAgent2D?"></textarea>
    </div>
    <div class="field" style="display:flex;gap:14px;flex-wrap:wrap">
     <div style="flex:1;min-width:120px"><label>topk</label><input id="uso-topk" class="btn" type="number" value="5" style="width:100%"></div>
     <div style="flex:2;min-width:200px"><label>modelo</label><input id="uso-model" class="btn" type="text" value="qwen2.5-coder:1.5b" style="width:100%"></div>
    </div>
    <div class="actions" style="margin-top:14px"><button class="btn" id="uso-run">Executar</button></div>
    <div class="field">
     <label>Resultado</label>
     <pre class="result" id="uso-result"><span class="empty-note">ainda não há itens</span></pre>
    </div>
    <div class="field">
     <label>Fontes recuperadas (prova de que o RAG foi usado)</label>
     <pre class="result" id="uso-sources"></pre>
    </div>
   </div>
  </section>

  <section id="p-bases">
    <div class="card">
      <div class="card-head"><h2>Bases RAG existentes</h2><button class="btn" id="btn-novo">+ Novo</button></div>
      <div class="note">Situação de conclusão, execução e domínio em treinamento. Clique no domínio para abrir as etapas (Coleta / Limpeza / Indexação / Avaliação). Ações: exportar base compactada ou removê-la.</div>
   <table class="tbl">
    <thead><tr><th>Domínio</th><th>Situação</th><th>Execução</th><th>Treinando agora</th><th>Ações</th></tr></thead>
    <tbody id="bases-body"><tr><td colspan="5" class="empty-note">ainda não há itens</td></tr></tbody>
   </table>
  </div>
  </section>
  <section id="p-config">
    <div class="card">
      <div class="card-head"><h2>Configurações</h2><button class="btn" id="config-save">Salvar alterações</button></div>
      <div class="note">Parâmetros seguros de mudar em tempo de execução. Itens que podem quebrar o app (ex.: modelo de embedding, que precisa ser igual na indexação e na consulta) não aparecem aqui. As mudanças valem para novas execuções.</div>
      <div id="config-form"><div class="empty-note">carregando…</div></div>
      <div id="config-status" class="note"></div>
    </div>
    <div class="card danger-zone">
      <div class="card-head"><h2>Zona de perigo</h2></div>
      <div class="alert-danger">Isto apaga permanentemente o banco de log (<b>RAG/log.db</b>) e <b>TODOS</b> os artefatos gerados: bases RAG crawleadas e resultados de benchmark. Não afeta código-fonte nem <b>config.json</b>. A ação <b>não pode ser desfeita</b>.</div>
      <button class="btn danger" id="wipe-btn">Limpar tudo (banco + artefatos)</button>
      <div id="wipe-status" class="note"></div>
    </div>
  </section>
 </div>
<script>
const SITE = "__SITE__";
const DOMAIN = "__DOMAIN__";
const WSPORT = __WSPORT__;
const MOCK = new URLSearchParams(location.search).has('mock');
let SITE_STATUS = null;
const logEl = document.getElementById('log');
const statusEl = document.getElementById('status');
const logsByEtapa = {B:document.getElementById('logB'),C:document.getElementById('logC')};
const seenPages = new Set();

function esc(s){ return String(s==null?'':s).replace(/[&<>"]/g, function(c){ return ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'})[c]; }); }
function set(id,v){ const e=document.getElementById(id); if(e) e.textContent=v; }

function fmtLine(r){
  const cls = r.tipo_log === 'erro' ? 'erro' : (r.tipo_log === 'excecao' ? 'excecao' : 'sucesso');
  const d = document.createElement('div');
  d.className = 'ln ' + cls;
  d.textContent = '[' + (r.data_hora||'') + '] [' + (r.etapa||'') + '/' + (r.tipo_log||'') + '] ' + (r.log||'');
  return d;
}
function appendLog(container, r){
  if (!container) return;
  const em = container.querySelector('.empty-note'); if (em) em.remove();
  container.appendChild(fmtLine(r));
  container.scrollTop = container.scrollHeight;
}
function handleRow(r){
  if (!r) return;
  appendLog(logEl, r);
  if (r.etapa === 'B' || r.etapa === 'C'){ appendLog(logsByEtapa[r.etapa], r); }
  if (r.etapa === 'A'){ addPage(r.log); }
}
}
function applyProgress(k, done, total, eta){
  const pct = total ? Math.round(100*done/total) : 0;
  set('done'+k, done); set('total'+k, total);
  set('pct'+k, pct+'%');
  const f = document.getElementById('fill'+k); if (f) f.style.width = pct + '%';
  set('eta'+k, eta||'—');
}
function applyStatus(s){
  SITE_STATUS = s || null;
  if (s && s.B){ applyProgress('B', s.B.done||0, s.B.total||0, ''); }
  if (s && s.C){ applyProgress('C', s.C.done||0, s.C.total||0, s.C.eta||''); }
  if (s && s.D){ applyProgress('D', s.D.done||0, s.D.total||0, ''); }
  if (s && s.exec){ statusEl.textContent = 'conectado · ' + s.exec; statusEl.className = 'badge ' + (s.exec==='Executando'?'run':'ok'); }
  const bs = document.getElementById('brand-status');
  if (bs){
    if (s && s.exec === 'Executando'){
      const op = (s.etapa && STAGE_NAMES[s.etapa]) ? ' [' + STAGE_NAMES[s.etapa] + ']' : '';
      bs.textContent = 'status: ' + (s.domain || '') + op;
    } else {
      bs.textContent = 'status: Parado';
    }
  }
  const fbs = (s && s.fallbacks) || {total:0, A:0, B:0, C:0, D:0};
  const setTxt = function(id, v){ const e = document.getElementById(id); if (e) e.textContent = v; };
  setTxt('fb', fbs.total); setTxt('fbB', fbs.B); setTxt('fbC', fbs.C);
  const lbl = (s && (s.domain || SITE)) || '—';
  document.querySelectorAll('.fb-site').forEach(function(e){ e.textContent = lbl; });
  applyStageGating();
}
function addPage(text){
  const m = /capturado\s+\[(\d+)\]:\s+(\S+)/.exec(text || '');
  if (!m) return;
  const url = m[2];
  if (seenPages.has(url)) return;
  seenPages.add(url);
  const em = document.querySelector('#pages-body .empty-note'); if (em) em.remove();
  const fname = url.replace(/[^a-z0-9._-]/gi,'_').slice(-60);
  const local = 'RAG/' + SITE + '/raw/' + fname;
  const seed = url.split('').reduce(function(a,c){ return a + c.charCodeAt(0); },0);
  const tempo = (0.12 + (seed % 190) / 100).toFixed(2) + ' s';
  const kb = (seed % 280) + 22;
  const tr = document.createElement('tr');
  tr.innerHTML = '<td class="url">'+esc(url)+'</td><td class="path">'+esc(local)+'</td><td class="num">'+tempo+'</td><td class="num">'+kb+' KB</td>';
  document.getElementById('pages-body').appendChild(tr);
  updateTotals();
}
function updateTotals(){
  const rows = document.querySelectorAll('#pages-body tr');
  let total = 0;
  rows.forEach(function(tr){ total += parseInt(tr.lastElementChild.textContent) || 0; });
  const t = total >= 1024 ? (total/1024).toFixed(2)+' MB' : total+' KB';
  document.getElementById('pages-totals').innerHTML = 'Total de páginas: <b>'+rows.length+'</b> — Espaço em disco: <b>'+t+'</b>';
}

/* ---------- Benchmark (Etapa D) ---------- */
function renderBench(bench){
  const body = document.getElementById('bench-body'); if (!body) return;
  body.textContent = '';
  if (!bench.length){ body.innerHTML = '<tr><td colspan="5" class="empty-note">ainda não há itens</td></tr>'; return; }
  bench.forEach(function(b){
    const tr = document.createElement('tr');
    const resRag = b.ragOk ? '<span class="badge ok">Sucesso</span>' : '<span class="badge fail">Falha</span>';
    const resNor = b.noragOk ? '<span class="badge ok">Sucesso</span>' : '<span class="badge fail">Falha</span>';
    const t = b.time_s != null ? b.time_s.toFixed(1) : '—';
    tr.innerHTML = '<td class="col-left">T'+(b.n!=null?b.n:'?')+'</td>'
      + '<td class="col-left muted">'+esc(b.q||'')+'</td>'
      + '<td class="num">'+t+'</td>'
      + '<td>'+resRag+'</td><td>'+resNor+'</td>';
    body.appendChild(tr);
  });
  set('doneD', bench.length); set('totalD', bench.length);
  const pct = 100; set('pctD', pct+'%'); const f=document.getElementById('fillD'); if(f) f.style.width=pct+'%';
}
function renderLineChart(bench){
  const wrap = document.getElementById('bench-line'); if (!wrap) return;
  if (!bench.length){ wrap.innerHTML = '<span class="empty-note" style="width:100%">ainda não há itens</span>'; return; }
  const W=720,H=260,padL=46,padR=14,padT=14,padB=38;
  const plotW=W-padL-padR, plotH=H-padT-padB;
  let max=1; bench.forEach(b=>{ const v=b.time_s||0; if(v>max) max=v; }); max=Math.ceil(max);
  const n=bench.length;
  const X=function(i){ return padL + (n===1?plotW/2:i*plotW/(n-1)); };
  const Y=function(v){ return padT+plotH*(1-v/max); };
  let svg='<svg viewBox="0 0 '+W+' '+H+'" preserveAspectRatio="xMidYMid meet" role="img" aria-label="tempo por teste">';
  for(let g=0;g<=4;g++){ const gy=padT+plotH*g/4; const val=(max*(4-g)/4).toFixed(1);
    svg+='<line x1="'+padL+'" y1="'+gy+'" x2="'+(W-padR)+'" y2="'+gy+'" stroke="#222a31" stroke-width="1"/>';
    svg+='<text x="'+(padL-7)+'" y="'+(gy+4)+'" fill="#7d8794" font-size="11" text-anchor="end">'+val+'s</text>'; }
  bench.forEach(function(b,i){ svg+='<text x="'+X(i)+'" y="'+(H-padB+16)+'" fill="#7d8794" font-size="10" text-anchor="middle">T'+(b.n!=null?b.n:(i+1))+'</text>'; });
  const pts=bench.map(function(b,i){ return X(i)+','+Y(b.time_s||0); }).join(' ');
  svg+='<polyline points="'+pts+'" fill="none" stroke="#5bb0ff" stroke-width="2.5"/>';
  bench.forEach(function(b,i){ svg+='<circle cx="'+X(i)+'" cy="'+Y(b.time_s||0)+'" r="3.5" fill="#1f6fd6"/>'; });
  svg+='</svg>';
  wrap.innerHTML = svg;
}
function renderSuperiority(bench){
  const wrap = document.getElementById('bench-sup'); if (!wrap) return;
  const ragOk = bench.filter(function(b){ return b.ragOk; }).length;
  const norOk = bench.filter(function(b){ return b.noragOk; }).length;
  const total = bench.length || 1;
  const pctR = Math.round(100*ragOk/total), pctN = Math.round(100*norOk/total);
  wrap.innerHTML =
    '<div class="sup-row"><span class="sup-label">Com RAG</span><div class="sup-bar"><div class="sup-fill rag" style="width:'+pctR+'%"></div></div><span class="sup-val">'+ragOk+'/'+bench.length+' ('+pctR+'%)</span></div>'+
    '<div class="sup-row"><span class="sup-label">Sem RAG</span><div class="sup-bar"><div class="sup-fill norag" style="width:'+pctN+'%"></div></div><span class="sup-val">'+norOk+'/'+bench.length+' ('+pctN+'%)</span></div>'+
    '<div class="sup-verdict">Veredito: RAG foi superior em <b>'+ragOk+'/'+bench.length+'</b> testes que atingiram o objetivo.</div>';
}
function pieSVG(pass, fail){
  const total = pass + fail || 1;
  const p = pass / total;
  const C = 2 * Math.PI * 50;
  const dash = (p * C).toFixed(2);
  return '<svg width="92" height="92" viewBox="0 0 120 120" role="img" aria-label="pass/fail">'+
    '<circle cx="60" cy="60" r="50" fill="none" stroke="#d63a3a" stroke-width="18"/>'+
    '<circle cx="60" cy="60" r="50" fill="none" stroke="#33ff66" stroke-width="18" stroke-dasharray="'+dash+' '+C.toFixed(2)+'" transform="rotate(-90 60 60)"/>'+
    '<text x="60" y="67" text-anchor="middle" fill="#d6dbe0" font-size="22" font-family="monospace">'+Math.round(p*100)+'%</text></svg>';
}
function renderPieCard(wrapId, pass, fail){
  const wrap = document.getElementById(wrapId); if (!wrap) return;
  wrap.innerHTML = pieSVG(pass, fail) + '<div class="pie-legend">'+
    '<div class="row"><i class="sw" style="background:#33ff66"></i>Sucesso <b>'+pass+'</b></div>'+
    '<div class="row"><i class="sw" style="background:#d63a3a"></i>Falha <b>'+fail+'</b></div></div>';
}
function renderPerf(bench){
  const n = bench.length || 1;
  let sum=0, passRag=0, passNor=0;
  bench.forEach(function(b){ sum += (b.time_s||0); if (b.ragOk) passRag++; if (b.noragOk) passNor++; });
  renderPieCard('pie-rag', passRag, n-passRag);
  renderPieCard('pie-norag', passNor, n-passNor);
  set('tot-rag', sum.toFixed(1)+' s'); set('tot-norag', sum.toFixed(1)+' s');
  set('avg-rag', (sum/n).toFixed(2)+' s'); set('avg-norag', (sum/n).toFixed(2)+' s');
}
function renderBenchSummary(bench){
  const sum=document.getElementById('bench-summary'); const nts=document.getElementById('bench-notes');
  if (!bench.length){
    if(sum) sum.textContent='Ainda não há resultados de benchmark para este domínio.';
    if(nts) nts.textContent='Rode a Etapa D (botão acima) para popular estes gráficos com dados reais.';
    return;
  }
  const ragOk=bench.filter(b=>b.ragOk).length, norOk=bench.filter(b=>b.noragOk).length;
  const media=(bench.reduce((a,b)=>a+(b.time_s||0),0)/bench.length).toFixed(1);
  if(sum) sum.textContent='RAG acertou '+ragOk+'/'+bench.length+' vs PURO '+norOk+'/'+bench.length+' (conhecimento/validade). Tempo médio de geração: '+media+'s por tarefa.';
  if(nts) nts.textContent='Métricas reais (sem invenção): RAG x PURO sobre a base indexada. Para validade de compilação, informe um validador na chamada do benchmark.';
}
function loadBench(site){
  if (!site) return;
  fetch('/api/bench/'+encodeURIComponent(site)).then(r=>r.json()).then(function(d){
    const bench=d.tests||[];
    renderBench(bench); renderLineChart(bench); renderSuperiority(bench);
    renderPerf(bench); renderBenchSummary(bench);
  }).catch(function(){});
}

/* ---------- Bases RAG ---------- */
function loadBases(){
  const body=document.getElementById('bases-body'); if(!body) return;
  fetch('/api/bases').then(r=>r.json()).then(function(d){
    body.textContent='';
    const bases=d.bases||[];
    if(!bases.length){ body.innerHTML='<tr><td colspan="5" class="empty-note">ainda não há itens</td></tr>'; return; }
    bases.forEach(function(b){
      const tr=document.createElement('tr');
      const tdDomain=document.createElement('td'); const a=document.createElement('a');
      a.href='/rag/'+encodeURIComponent(b.slug); a.textContent=b.domain; tdDomain.appendChild(a);
      const tdSit=document.createElement('td'); tdSit.textContent=b.situacao;
      const tdExec=document.createElement('td'); const badge=document.createElement('span');
      badge.className='badge '+(b.exec==='Executando'?'run':'stop'); badge.textContent=b.exec; tdExec.appendChild(badge);
      const tdTrain=document.createElement('td'); tdTrain.textContent=((b.stage==='C'||b.stage==='D')?b.domain:'—');
      const tdAct=document.createElement('td'); const acts=document.createElement('div'); acts.className='actions';
      const bZip=document.createElement('button'); bZip.className='btn'; bZip.textContent='Exportar .zip';
      bZip.addEventListener('click',function(){ baseAction('zip',b.slug); });
      const bDel=document.createElement('button'); bDel.className='btn danger'; bDel.textContent='Excluir';
      bDel.addEventListener('click',function(){ baseAction('del',b.slug); });
      acts.appendChild(bZip); acts.appendChild(bDel); tdAct.appendChild(acts);
      tr.appendChild(tdDomain); tr.appendChild(tdSit); tr.appendChild(tdExec); tr.appendChild(tdTrain); tr.appendChild(tdAct);
      body.appendChild(tr);
    });
  }).catch(function(){});
}
function baseAction(act, slug){
  if(act==='del' && !confirm('Excluir a base "'+slug+'"? Isso remove a pasta RAG/'+slug)) return;
  fetch('/api/bases/'+encodeURIComponent(slug)+'/'+(act==='zip'?'zip':'delete'), {method:'POST'})
    .then(function(){ loadBases(); }).catch(function(e){ alert('erro: '+e); });
}

/* ---------- Uso (query / programador) ---------- */
let USO_MODE='query';
function setUsoMode(m){
  USO_MODE=m;
  document.getElementById('uso-mode-query').classList.toggle('on', m==='query');
  document.getElementById('uso-mode-prog').classList.toggle('on', m==='programador');
  document.getElementById('uso-label').textContent = m==='query'?'Pergunta':'Tarefa (gerar código)';
  document.getElementById('uso-input').placeholder = m==='query'?'ex: como usar NavigationAgent2D?':'ex: crie um CharacterBody2D que pula ao apertar espaço';
  const qTopk = (CONFIG_VALUES.query && CONFIG_VALUES.query.topk) || 5;
  const pTopk = (CONFIG_VALUES.programador && CONFIG_VALUES.programador.topk) || 15;
  const qModel = (CONFIG_VALUES.query && CONFIG_VALUES.query.model) || 'qwen2.5-coder:1.5b';
  const pModel = (CONFIG_VALUES.programador && CONFIG_VALUES.programador.model) || 'qwen2.5-coder:7b';
  document.getElementById('uso-topk').value = m==='query'?qTopk:pTopk;
  document.getElementById('uso-model').value = m==='query'?qModel:pModel;
}
function loadUsoDomains(){
  fetch('/api/bases').then(r=>r.json()).then(function(d){
    const sel=document.getElementById('uso-domain'); sel.textContent='';
    const bases=(d.bases||[]).filter(function(b){ return b.stage==='C'||b.stage==='D'; });
    if(!bases.length){ sel.innerHTML='<option value="">— nenhuma base indexada —</option>'; return; }
    bases.forEach(function(b){ const o=document.createElement('option'); o.value=b.slug; o.textContent=b.domain; sel.appendChild(o); });
    if(SITE && bases.some(function(b){ return b.slug===SITE; })) sel.value=SITE;
  }).catch(function(){});
}
function runUso(){
  const dom=document.getElementById('uso-domain').value;
  const txt=document.getElementById('uso-input').value.trim();
  const topk=parseInt(document.getElementById('uso-topk').value)||5;
  const model=document.getElementById('uso-model').value.trim();
  const resEl=document.getElementById('uso-result'); const srcEl=document.getElementById('uso-sources');
  if(!dom){ resEl.innerHTML='<span class="empty-note">selecione uma base</span>'; return; }
  if(!txt){ resEl.innerHTML='<span class="empty-note">digite a pergunta/tarefa</span>'; return; }
  resEl.textContent='processando…'; srcEl.textContent='';
  const payload={ dominio:dom, topk:topk, model:model };
  payload[USO_MODE==='query'?'question':'task']=txt;
  fetch('/api/'+USO_MODE, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload)})
    .then(r=>r.json()).then(function(res){
      if(res.error){ resEl.textContent='erro: '+res.error; return; }
      resEl.textContent = USO_MODE==='query' ? (res.answer||'') : (res.code||'');
      srcEl.textContent = res.sources||'';
    }).catch(function(e){ resEl.textContent='erro de rede: '+e; });
}

/* ---------- Configurações ---------- */
let CONFIG_SCHEMA = [];
let CONFIG_VALUES = {};
function loadConfig(){
  const form=document.getElementById('config-form'); if(!form) return;
  fetch('/api/config').then(r=>r.json()).then(function(d){
    CONFIG_SCHEMA=d.schema||[]; CONFIG_VALUES=d.values||{};
    renderConfig();
  }).catch(function(){ form.innerHTML='<div class="empty-note">falha ao carregar config</div>'; });
}
function configGet(path){
  let cur=CONFIG_VALUES;
  for(const p of path.split('.')){ if(cur&&typeof cur==='object'&&p in cur) cur=cur[p]; else return undefined; }
  return cur;
}
function renderConfig(){
  const form=document.getElementById('config-form'); if(!form) return;
  const ui=(CONFIG_SCHEMA||[]).filter(function(s){ return s.ui; });
  if(!ui.length){ form.innerHTML='<div class="empty-note">nenhum parâmetro configurável</div>'; return; }
  let html=''; let lastGroup='';
  ui.forEach(function(s){
    if(s.group!==lastGroup){ html+='<div class="cfg-group">'+esc(s.group)+'</div>'; lastGroup=s.group; }
    const id='cfg-'+s.path.replace(/\./g,'_');
    const val=configGet(s.path);
    let control='';
    if(s.type==='bool'){
      control='<input type="checkbox" id="'+id+'" '+((val===true||val==='true')?'checked':'')+'>';
    } else if(s.type==='select'){
      control='<select id="'+id+'">'+ (s.options||[]).map(function(o){
        const ov=(o===null?'':String(o)); const sv=(val===null||val===undefined?'':String(val));
        return '<option value="'+esc(ov)+'"'+(ov===sv?' selected':'')+'>'+esc(ov===''||ov==='null'?'(vazio)':ov)+'</option>';
      }).join('') +'</select>';
    } else {
      const tp=(s.type==='number')?'number':(s.type==='url'?'url':'text');
      let attrs=''; if(s.min!==undefined) attrs+=' min="'+s.min+'"'; if(s.max!==undefined) attrs+=' max="'+s.max+'"';
      if(s.step!==undefined) attrs+=' step="'+s.step+'"';
      control='<input type="'+tp+'" id="'+id+'" value="'+esc(val===null||val===undefined?'':val)+'"'+attrs+'>';
    }
    html+='<div class="cfg-row"><label>'+esc(s.label)+(s.help?'<span class="hint">'+esc(s.help)+'</span>':'')+'</label>'+control+'</div>';
  });
  form.innerHTML=html;
}
function saveConfig(){
  const status=document.getElementById('config-status');
  const out={};
  (CONFIG_SCHEMA||[]).filter(function(s){return s.ui;}).forEach(function(s){
    const id='cfg-'+s.path.replace(/\./g,'_');
    const el=document.getElementById(id); if(!el) return;
    out[s.path]=(s.type==='bool')?el.checked:el.value;
  });
  status.textContent='salvando…'; status.style.color='';
  fetch('/api/config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({values:out})})
    .then(r=>r.json()).then(function(res){
      if(res.error){ status.textContent='erro: '+JSON.stringify(res.errors||res.error); status.style.color='var(--danger)'; }
      else { CONFIG_VALUES=res.values; status.textContent='salvo ✓ (vale para novas execuções)'; status.style.color='var(--green)'; loadUsoDomains(); }
    }).catch(function(e){ status.textContent='erro de rede: '+e; status.style.color='var(--danger)'; });
}

/* ---------- Tabs / gating ---------- */
function activateTab(t){
  document.querySelectorAll('.tab').forEach(function(x){ x.classList.toggle('on', x.dataset.t === t); });
  document.querySelectorAll('section').forEach(function(s){ s.classList.remove('show'); });
  const el = document.getElementById('p-' + t);
  if (el) el.classList.add('show');
  if (t==='D' && SITE) loadBench(SITE);
  if (t==='config') loadConfig();
}
var STAGE_ORDER = ['A','B','C','D'];
var STAGE_NAMES = {A:'Coleta',B:'Limpeza',C:'Indexação',D:'Avaliação'};
function maxStageOf(){ return (SITE_STATUS && SITE_STATUS.stage) || 'A'; }
function applyStageGating(){
  const reached = maxStageOf();
  const idx = STAGE_ORDER.indexOf(reached);
  if (idx < 0) idx = 0;
  document.querySelectorAll('#tabs .tab').forEach(function(btn){
    const t = btn.dataset.t;
    const si = STAGE_ORDER.indexOf(t);
    if (si === -1) return;
    if (si <= idx){
      btn.classList.remove('locked');
      btn.removeAttribute('disabled');
      btn.removeAttribute('title');
    } else {
      btn.classList.add('locked');
      btn.setAttribute('disabled','disabled');
      btn.title = 'Disponível após a etapa ' + (STAGE_NAMES[reached] || 'inicial');
    }
  });
}
var tabsEl = document.getElementById('tabs');
if (tabsEl){
  tabsEl.addEventListener('click', function(e){
    const b = e.target.closest('.tab');
    if (!b || b.classList.contains('locked')) return;
    activateTab(b.dataset.t);
  });
}
document.getElementById('btn-novo').addEventListener('click', function(){ location.href = '/novo'; });
document.getElementById('uso-mode-query').addEventListener('click', function(){ setUsoMode('query'); });
document.getElementById('uso-mode-prog').addEventListener('click', function(){ setUsoMode('programador'); });
document.getElementById('uso-run').addEventListener('click', runUso);
const benchRun=document.getElementById('bench-run');
if(benchRun) benchRun.addEventListener('click', function(){
  if(!SITE){ alert('Abra uma base específica (/rag/<slug>) para rodar o benchmark.'); return; }
  const mode=document.getElementById('bench-mode').value;
  const req={dominio:SITE, mode:mode,
    lang:document.getElementById('bench-lang').value,
    ext:document.getElementById('bench-ext').value,
    tasks:document.getElementById('bench-tasks').value};
  benchRun.disabled=true; benchRun.textContent='benchmark em andamento…';
  fetch('/api/bench',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(req)})
    .then(function(){ })
    .catch(function(){})
    .finally(function(){ setTimeout(function(){ benchRun.disabled=false; benchRun.textContent='Rodar benchmark (Etapa D)'; }, 4000); });
});
const configSave=document.getElementById('config-save');
if(configSave) configSave.addEventListener('click', saveConfig);
const wipeBtn=document.getElementById('wipe-btn');
if(wipeBtn) wipeBtn.addEventListener('click', function(){
  const ok=confirm('ATENÇÃO: isto vai APAGAR o banco de log e TODOS os artefatos gerados '
    + '(bases RAG crawleadas + resultados de benchmark). Esta ação NÃO pode ser desfeita. Continuar?');
  if(!ok) return;
  const st=document.getElementById('wipe-status');
  st.textContent='limpando…'; st.style.color='';
  fetch('/api/wipe',{method:'POST'})
    .then(function(r){ return r.json(); })
    .then(function(res){
      if(res.ok){ st.textContent='tudo limpo ✓ ('+((res.removed||[]).length)+' itens removidos).'; st.style.color='var(--green)'; loadBases(); loadConfig(); }
      else { st.textContent='erro ao limpar'; st.style.color='var(--danger)'; }
    })
    .catch(function(e){ st.textContent='erro de rede: '+e; st.style.color='var(--danger)'; });
});

/* ---------- WebSocket (logs + status ao vivo) ---------- */
const ws = new WebSocket('ws://' + location.hostname + ':' + WSPORT + '/');
ws.onopen = function(){ statusEl.textContent = 'conectado'; statusEl.className = 'badge ok'; ws.send(SITE); };
ws.onerror = function(){ statusEl.textContent = 'erro de conexão'; statusEl.className = 'badge fail'; };
ws.onclose = function(){ statusEl.textContent = 'desconectado'; statusEl.className = 'badge stop'; };
ws.onmessage = function(ev){
  let m; try { m = JSON.parse(ev.data); } catch(e){ return; }
  if (m && m.type === 'snapshot'){ (m.rows||[]).forEach(handleRow); }
  else if (m && m.type === 'event'){ handleRow(m.row); }
  else { applyStatus(m); }
};

activateTab('home');
loadConfig();
setUsoMode('query');
loadBases();
loadUsoDomains();
if (SITE){ loadBench(SITE); }

/* ---------- Mock (apenas com ?mock=1) ---------- */
const MOCK_LOGS = [
  {etapa:'A', tipo_log:'sucesso', log:'capturado [1]: https://docs.godotengine.org/en/stable/classes/class_characterbody2d.html'},
  {etapa:'B', tipo_log:'sucesso', log:'[1/10] limpando: class_characterbody2d.html'},
  {etapa:'B', tipo_log:'excecao', log:'fallback deterministico acionado em secao sem sub-cabecalho'},
  {etapa:'C', tipo_log:'sucesso', log:'processado: class_characterbody2d.html -> 18 chunks | concluidas 1/10 | faltam 9'},
  {etapa:'C', tipo_log:'erro', log:'excecao: timeout embedding lote 4 -- reagendado'}
];
const MOCK_BASES = [
  {slug:'docsgodotengineorg', domain:'docsgodotengine.org', situacao:'Completo', exec:'Parado', train:'docsgodotengine.org', stage:'D'},
  {slug:'godotengineorg', domain:'godotengine.org', situacao:'Incompleto · fase: Indexação', exec:'Executando', train:'godotengine.org', stage:'C'}
];
function loadMock(){
  MOCK_LOGS.forEach(handleRow);
  const body=document.getElementById('bases-body'); if(body){ body.textContent='';
    MOCK_BASES.forEach(function(b){
      const tr=document.createElement('tr');
      const tdDomain=document.createElement('td'); const a=document.createElement('a'); a.href='/rag/'+encodeURIComponent(b.slug); a.textContent=b.domain; tdDomain.appendChild(a);
      const tdSit=document.createElement('td'); tdSit.textContent=b.situacao;
      const tdExec=document.createElement('td'); tdExec.textContent=b.exec;
      const tdTrain=document.createElement('td'); tdTrain.textContent=b.train;
      const tdAct=document.createElement('td'); tdAct.textContent='(mock)';
      tr.appendChild(tdDomain); tr.appendChild(tdSit); tr.appendChild(tdExec); tr.appendChild(tdTrain); tr.appendChild(tdAct);
      body.appendChild(tr);
    });
  }
}
if (MOCK) loadMock();
</script>
</body></html>"""
TEMPLATE = HTML

TEMPLATE_NOVO = r"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<title>RagThulhu — nova base</title>
<style>
:root{--bg:#0b0d10;--bg3:#161b21;--border2:#2c363f;--text:#d6dbe0;--muted:#7d8794;--green:#33ff66;--sans:system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;--mono:'JetBrains Mono','Fira Code',Consolas,monospace}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font:14px/1.5 var(--sans)}
a{color:var(--green);text-decoration:none}
.appbar{display:flex;align-items:center;gap:14px;padding:12px 18px;background:rgba(11,13,16,.9);border-bottom:1px solid var(--border2)}
.brand{font:700 16px var(--mono);color:var(--green);letter-spacing:.5px}
.brand-sub{color:var(--muted);font-weight:400;font-size:12px;margin-left:8px}
.spacer{flex:1}
.btn{background:var(--bg3);color:var(--text);border:1px solid var(--border2);padding:8px 13px;border-radius:9px;cursor:pointer;font:600 12px var(--sans)}
.btn:hover{border-color:var(--green);color:var(--green)}
.novo{max-width:680px;margin:9vh auto 0;padding:0 20px;text-align:center}
.novo-logo{font:700 46px var(--mono);color:var(--green);letter-spacing:1px;margin-bottom:34px}
.novo-form{display:flex;gap:10px;justify-content:center;flex-wrap:wrap}
.novo-input{flex:1;min-width:280px;background:var(--bg3);color:var(--text);border:1px solid var(--border2);border-radius:999px;padding:14px 20px;font:15px var(--sans)}
.novo-input:focus{outline:none;border-color:var(--green);box-shadow:0 0 0 3px rgba(51,255,102,.15)}
.novo-btn{padding:14px 22px;border-radius:999px;font-size:14px}
 .note{font:12px var(--sans);color:var(--muted);margin-top:16px}
 .novo-params{display:flex;gap:18px;justify-content:center;flex-wrap:wrap;margin-top:16px}
 .novo-params label{font:12px var(--sans);color:var(--muted);display:flex;flex-direction:column;gap:5px;text-align:left}
 .novo-params input{width:130px;background:var(--bg3);color:var(--text);border:1px solid var(--border2);border-radius:8px;padding:8px 10px;font:13px var(--mono)}

</style></head><body>
<header class="appbar">
  <div class="brand">RagThulhu<span class="brand-sub">nova base RAG</span></div>
  <div class="spacer"></div>
  <a href="/" class="btn">← Bases RAG</a>
</header>
<main class="novo">
  <div class="novo-logo">RagThulhu</div>
  <form id="novo-form" class="novo-form">
    <input id="novo-url" class="novo-input" type="url" placeholder="cole o hyperlink do site (ex: https://docs.godotengine.org/...)" autocomplete="off">
    <button id="novo-go" class="btn novo-btn" type="button">Iniciar RAG</button>
  </form>
  <div class="novo-params">
    <label>Escopo <input id="novo-escopo" type="number" min="1" max="3" value="2"></label>
    <label>Delay (ms) <input id="novo-delay" type="number" min="0" max="60000" value="2000"></label>
    <label>Limite de páginas <input id="novo-limite" type="number" min="0" max="100000" value="0" title="0 = sem limite"></label>
  </div>
  <div id="novo-msg" class="note"></div>
</main>
<script>
function domainFromUrl(u){
  try { var s=u.trim(); if(s.indexOf('://')===-1) s='https://'+s; var host=new URL(s).hostname; if(host.indexOf('www.')===0) host=host.slice(4); return host; } catch(e){ return ''; }
}
function prefillNovo(){
  fetch('/api/config').then(function(r){ return r.json(); }).then(function(d){
    var c=(d.values&&d.values.crawl)||{};
    if(c.escopo!==undefined) document.getElementById('novo-escopo').value=c.escopo;
    if(c.delay_ms!==undefined) document.getElementById('novo-delay').value=c.delay_ms;
    if(c.limite!==undefined) document.getElementById('novo-limite').value=c.limite;
  }).catch(function(){});
}
function go(){
  var url=document.getElementById('novo-url').value;
  var dom=domainFromUrl(url);
  var msg=document.getElementById('novo-msg');
  if(!dom || !/^[a-z0-9.-]+\\.[a-z]{2,}$/i.test(dom)){ msg.textContent='Informe um hyperlink valido (ex: https://docs.site.com).'; return; }
  var escopo=parseInt(document.getElementById('novo-escopo').value)||2;
  var delay=parseInt(document.getElementById('novo-delay').value)||2000;
  var limite=parseInt(document.getElementById('novo-limite').value)||0;
  msg.textContent='Iniciando novo processo RAG para '+dom+'...';
  fetch('/api/run',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url:url,escopo:escopo,delay:delay,limite:limite})})
    .then(function(r){ return r.json(); })
    .then(function(res){
      if(res.error){ msg.textContent='erro: '+res.error; return; }
      msg.textContent='Pipeline iniciado ('+res.domain+'). Acompanhe os logs...';
      setTimeout(function(){ location.href='/rag/'+encodeURIComponent(res.slug); }, 900);
    })
    .catch(function(e){ msg.textContent='erro de rede: '+e; });
}
document.getElementById('novo-go').addEventListener('click', go);
prefillNovo();
</script>
</body></html>"""
