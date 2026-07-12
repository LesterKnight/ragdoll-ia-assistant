# Templates (HTML/CSS/JS) do servidor web ragdoll.
# Strings com placeholders: __SITE__, __WSPORT__, __TABS__, __BACK__.

MAIN_TABS = (
  '<button class="tab on" data-t="home">Visão Geral</button>\n'
  '  <button class="tab" data-t="bases">Bases RAG</button>'
)
RAG_TABS = (
  '<button class="tab on" data-t="home">Visão Geral</button>\n'
  '  <button class="tab" data-t="A">Coleta</button>\n'
  '  <button class="tab" data-t="B">Limpeza</button>\n'
  '  <button class="tab" data-t="C">Indexação</button>\n'
  '  <button class="tab" data-t="D">Avaliação</button>')
BACK_LINK = '<a href="/" class="btn">← Bases RAG</a>'

HTML = """<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<title>ragdoll — painel de serviço</title>
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
 .brand small{color:var(--muted);font-weight:400;margin-left:8px}
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
 .btn.danger:hover{border-color:var(--danger);color:#ff8a8a}
 .actions{display:flex;gap:8px}
 textarea,select{background:var(--bg3);color:var(--text);border:1px solid var(--border2);border-radius:9px;padding:9px 11px;font:13px var(--mono);color-scheme:dark}
 textarea{width:100%;min-height:84px;resize:vertical}
 .field{margin-top:14px}
 .field label{display:block;margin-bottom:6px;font:600 12px var(--sans);color:var(--muted)}
 .note{font:12px var(--sans);color:var(--muted);margin:2px 0 0}
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
</style></head><body>
<header class="appbar">
  <div class="brand">ragdoll<span class="brand-sub">base: __DOMAIN__</span></div>
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
   <div class="note">Fonte: SQLite (RAG/log.db) → WebSocket. Fallbacks determinísticos: <b id="fb" style="color:var(--warn)">0</b></div>
   <div class="log" id="log"></div>
  </div>
 </section>

 <section id="p-A">
  <div class="card">
   <h2>Coleta — páginas capturadas</h2>
   <div class="note">Cada download: destino em disco, tempo de transferência e tamanho do arquivo.</div>
   <table class="tbl">
    <thead><tr><th style="width:42%">Página</th><th style="width:34%">Local (disco)</th><th class="num">Tempo</th><th class="num">Tamanho</th></tr></thead>
    <tbody id="pages-body"></tbody>
   </table>
   <div class="totals" id="pages-totals">Total de páginas: <b>0</b> — Espaço em disco: <b>0 KB</b></div>
  </div>
 </section>

 <section id="p-B">
   <div class="card">
    <h2>Limpeza</h2>
    <div class="note">Fallbacks determinísticos: <b id="fbB" style="color:var(--warn)">0</b></div>
    <div class="prog">
    <div class="row"><span>Progresso</span><span><b id="pctB">0%</b> · <span id="doneB">0</span>/<span id="totalB">0</span> · ETA <span id="etaB">—</span></span></div>
    <div class="bar"><div class="fill" id="fillB"></div></div>
   </div>
   <div class="log" id="logB"></div>
  </div>
 </section>

 <section id="p-C">
   <div class="card">
    <h2>Indexação</h2>
    <div class="note">Fallbacks determinísticos: <b id="fbC" style="color:var(--warn)">0</b></div>
    <div class="prog">
    <div class="row"><span>Progresso</span><span><b id="pctC">0%</b> · <span id="doneC">0</span>/<span id="totalC">0</span> · ETA <span id="etaC">—</span></span></div>
    <div class="bar"><div class="fill" id="fillC"></div></div>
   </div>
   <div class="log" id="logC"></div>
  </div>
 </section>

 <section id="p-D">
  <div class="card">
   <h2>Avaliação — benchmark (RAG × sem RAG)</h2>
   <div class="prog">
    <div class="row"><span>Progresso do benchmark</span><span><b id="pctD">0%</b> · <span id="doneD">0</span>/<span id="totalD">0</span></span></div>
    <div class="bar"><div class="fill" id="fillD"></div></div>
   </div>
    <div class="chart-wrap">
     <h3 class="muted" style="margin:0 0 6px">Tempo de geração por teste (visão geral)</h3>
     <div class="linechart" id="bench-line"></div>
     <div class="legend"><span><i class="sw rag"></i>Com RAG (azul)</span><span><i class="sw norag"></i>Sem RAG (vermelho)</span></div>
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
      <thead><tr><th class="col-left" style="width:19%">Teste</th><th class="col-left" style="width:31%">Descrição do teste</th><th class="num">Tempo c/ RAG (s)</th><th class="num">Tempo s/ RAG (s)</th><th>Com RAG</th><th>Sem RAG</th></tr></thead>
     <tbody id="bench-body"></tbody>
    </table>
    <div class="note" style="margin-top:8px">Dados de exemplo — o backend do benchmark ainda será ligado.</div>
    <div class="ai-box">
     <h3>Resumo (gerado pela IA)</h3>
     <p id="bench-summary"></p>
     <div class="ai-hint">Preenchido automaticamente pelo agente de QA a partir dos resultados reais.</div>
    </div>
    <div class="ai-box">
     <h3>Observações (gerado pela IA)</h3>
     <p id="bench-notes"></p>
     <div class="ai-hint">Otimizações, possíveis problemas e sugestões de melhoria do benchmark. Sem invenção de dados.</div>
    </div>
  </div>
 </section>

  <section id="p-bases">
    <div class="card">
      <div class="card-head"><h2>Bases RAG existentes</h2><button class="btn" id="btn-novo">+ Novo</button></div>
      <div class="note">Situação de conclusão, execução e domínio em treinamento. Clique no domínio para abrir as etapas (Coleta / Limpeza / Indexação / Avaliação). Ações: exportar base compactada ou removê-la.</div>
   <table class="tbl">
    <thead><tr><th>Domínio</th><th>Situação</th><th>Execução</th><th>Treinando agora</th><th>Ações</th></tr></thead>
    <tbody id="bases-body"></tbody>
   </table>
  </div>
 </section>
</div>
<script>
const SITE = "__SITE__";
const DOMAIN = "__DOMAIN__";
const WSPORT = __WSPORT__;
const logEl = document.getElementById('log');
const statusEl = document.getElementById('status');
const logsByEtapa = {B:document.getElementById('logB'),C:document.getElementById('logC')};
const seenPages = new Set();

/* ============================================================
   MOCK DATA — frontend-only, para validação visual.
   Quando o backend estiver pronto, estes painéis passam a ser
   alimentados pelo WebSocket (snapshot / event / progress).
   ============================================================ */
const MOCK_LOGS = [
  {etapa:'A', tipo_log:'sucesso', log:'capturando https://docsgodotengineorg/class_characterbody2d.html'},
  {etapa:'A', tipo_log:'sucesso', log:'capturando https://docsgodotengineorg/class_tilemaplayer.html'},
  {etapa:'A', tipo_log:'sucesso', log:'capturando https://docsgodotengineorg/class_node2d.html'},
  {etapa:'A', tipo_log:'sucesso', log:'capturando https://docsgodotengineorg/tutorials/2d/topdown_character.html'},
  {etapa:'A', tipo_log:'sucesso', log:'capturando https://docsgodotengineorg/classes/class_physicsbody2d.html'},
  {etapa:'A', tipo_log:'sucesso', log:'capturando https://docsgodotengineorg/getting_started/step_by_step/index.html'},
  {etapa:'A', tipo_log:'sucesso', log:'seguindo link interno: /tutorials/3d/'},
  {etapa:'A', tipo_log:'sucesso', log:'manifest atualizado (148 paginas)'},
  {etapa:'B', tipo_log:'sucesso', log:'limpando class_characterbody2d.html -> removendo nav/footer/sidebar'},
  {etapa:'B', tipo_log:'sucesso', log:'clean.jsonl +18 linhas'},
  {etapa:'B', tipo_log:'sucesso', log:'preservando bloco de codigo (5 trechos)'},
  {etapa:'B', tipo_log:'sucesso', log:'limpando tutorials/2d/topdown_character.html'},
  {etapa:'B', tipo_log:'excecao', log:'fallback deterministico acionado em secao sem sub-cabecalho'},
  {etapa:'B', tipo_log:'erro', log:'erro ao limpar asset_lib.html (html malformado) -- usando fallback'},
  {etapa:'C', tipo_log:'sucesso', log:'indexando docsgodotengineorg: 12040/96250 chunks'},
  {etapa:'C', tipo_log:'sucesso', log:'embed 240 vetores (nomic-embed-text)'},
  {etapa:'C', tipo_log:'sucesso', log:'summary.md atualizado (CharacterBody2D)'},
  {etapa:'C', tipo_log:'excecao', log:'fallback deterministico acionado em secao sem sub-cabecalho'},
  {etapa:'C', tipo_log:'sucesso', log:'embed 198 vetores (nomic-embed-text)'},
  {etapa:'C', tipo_log:'erro', log:'excecao: timeout embedding lote 412 -- reagendado'},
  {etapa:'C', tipo_log:'sucesso', log:'indexando docsgodotengineorg: 38920/96250 chunks'}
];
const MOCK_BENCH = [
  {test:'CharacterBody2D.move_and_slide', desc:'Gerar chamada de move_and_slide com vetor de velocidade correto', rag:1.9, norag:4.2, ragOk:true, noragOk:false},
  {test:'TileMapLayer.get_cell_source_id', desc:'Obter o id de origem de uma celula do tilemap', rag:2.1, norag:5.1, ragOk:true, noragOk:false},
  {test:'Signal corpo_entrou / corpo_saiu', desc:'Conectar sinais corpo_entrou e corpo_saiu de Area2D', rag:1.6, norag:3.8, ragOk:true, noragOk:false},
  {test:'PhysicsBody2D constante gravidade', desc:'Definir a constante de gravidade do corpo fisico', rag:2.4, norag:4.9, ragOk:false, noragOk:false},
  {test:'AnimationPlayer.play(...)', desc:'Iniciar uma animacao pelo nome', rag:1.3, norag:3.2, ragOk:true, noragOk:false},
  {test:'Area2D.is_in_group', desc:'Verificar se o area pertence a um grupo', rag:1.1, norag:2.9, ragOk:true, noragOk:false},
  {test:'Node.get_node caminho relativo', desc:'Recuperar um no por caminho relativo', rag:2.0, norag:4.6, ragOk:false, noragOk:false},
  {test:'PackedScene.instantiate', desc:'Instanciar uma cena a partir de PackedScene', rag:1.5, norag:3.5, ragOk:true, noragOk:false},
  {test:'CanvasItem.modulate', desc:'Aplicar modulacao de cor em um CanvasItem', rag:1.7, norag:3.9, ragOk:true, noragOk:false},
  {test:'SceneTree.change_scene_to', desc:'Trocar a cena ativa por outra cena', rag:2.2, norag:5.3, ragOk:false, noragOk:false}
];
const MOCK_SUMMARY = 'O modelo com RAG foi superior em 7 de 10 testes, atingindo o objetivo onde o modelo sem RAG falhou. O tempo medio de geracao foi menor com RAG (~1.8s) do que sem RAG (~4.1s), e a taxa de acerto de assinaturas/APIs foi maior. Nos 3 testes em que a base RAG tambem nao atingiu o objetivo, o modelo sem RAG alucinou parametros ou nomes de metodos — indicando que o contexto recuperado ainda omite simbolos nessas tarefas.';
const MOCK_NOTES_LINES = [
  'Melhorias possiveis no benchmark:',
  '- Ampliar a diversidade de dominios (nao so Godot) para reduzir vies.',
  '- Validar nao so compilacao, mas execucao em sandbox (evita falso positivo).',
  '- Medir qualidade (lint/estilo), nao so correcao.',
  'Possiveis problemas:',
  '- topk=15 ainda omite simbolos em 3 tarefas — rever estrategia de chunking/recuperacao.',
  '- Sem RAG nao produziu saida valida em nenhum teste (tempo medido ate a falha).',
  'Otimizacao:',
  '- Cache de embeddings acelera re-execucoes do benchmark.'
];
const MOCK_BASES = [
  {slug:'docsgodotengineorg', domain:'docsgodotengine.org', sit:'Completo', exec:'Parado', train:'—', stage:'D'},
  {slug:'godotengineorg', domain:'godotengine.org', sit:'Incompleto · fase: Indexação', exec:'Executando', train:'godotengine.org', stage:'C'},
  {slug:'docsunity3dcom', domain:'docs.unity3d.com', sit:'Incompleto · fase: Coleta', exec:'Parado', train:'—', stage:'A'}
];

const ws = new WebSocket('ws://' + location.hostname + ':' + WSPORT + '/');
ws.onopen = function(){ statusEl.textContent = 'conectado'; statusEl.className = 'badge ok'; ws.send(SITE); };
ws.onerror = function(){ statusEl.textContent = 'erro de conexão'; statusEl.className = 'badge fail'; };
ws.onclose = function(){ statusEl.textContent = 'desconectado'; statusEl.className = 'badge stop'; };

function esc(s){ return String(s).replace(/[&<>"]/g, function(c){ return ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'})[c]; }); }
function fmtLine(r){
  const cls = r.tipo_log === 'erro' ? 'erro' : (r.tipo_log === 'excecao' ? 'excecao' : 'sucesso');
  const d = document.createElement('div');
  d.className = 'ln ' + cls;
  d.textContent = '[' + r.data_hora + '] [' + r.etapa + '/' + r.tipo_log + '] ' + r.log;
  return d;
}
function appendLog(container, r){
  if (!container) return;
  container.appendChild(fmtLine(r));
  container.scrollTop = container.scrollHeight;
}
function handleRow(r){
  appendLog(logEl, r);
  if (r.etapa === 'B' || r.etapa === 'C'){ appendLog(logsByEtapa[r.etapa], r); }
  if (r.etapa === 'A'){ addPage(r.log); }
  if (/fallback deterministico/.test(r.log)){
    var f = document.getElementById('fb'); if (f) f.textContent = (parseInt(f.textContent)||0)+1;
    if (r.etapa === 'B'){ var fb=document.getElementById('fbB'); if (fb) fb.textContent = (parseInt(fb.textContent)||0)+1; }
    if (r.etapa === 'C'){ var fc=document.getElementById('fbC'); if (fc) fc.textContent = (parseInt(fc.textContent)||0)+1; }
  }
}
function applyProgress(k, done, total, eta){
  const pct = total ? Math.round(100*done/total) : 0;
  document.getElementById('done'+k).textContent = done;
  document.getElementById('total'+k).textContent = total;
  document.getElementById('pct'+k).textContent = pct + '%';
  document.getElementById('fill'+k).style.width = pct + '%';
  document.getElementById('eta'+k).textContent = eta || '—';
}
function addPage(text){
  const m = /capturando\\s+(\\S+)/.exec(text);
  if (!m) return;
  const url = m[1];
  if (seenPages.has(url)) return;
  seenPages.add(url);
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
function renderBench(bench){
  const body = document.getElementById('bench-body');
  if (!body) return;
  body.textContent = '';
  bench.forEach(function(b){
    const tr = document.createElement('tr');
    const resRag = b.ragOk ? '<span class="badge ok">Sucesso</span>' : '<span class="badge fail">Falha</span>';
    const resNor = b.noragOk ? '<span class="badge ok">Sucesso</span>' : '<span class="badge fail">Falha</span>';
    const nr = b.norag ? b.norag.toFixed(1) : '—';
    tr.innerHTML = '<td class="col-left">'+esc(b.test)+'</td>'
      + '<td class="col-left muted">'+esc(b.desc)+'</td>'
      + '<td class="num">'+(b.rag?b.rag.toFixed(1):'—')+'</td>'
      + '<td class="num">'+nr+'</td>'
      + '<td>'+resRag+'</td>'
      + '<td>'+resNor+'</td>';
    body.appendChild(tr);
  });
  const done = bench.length, total = 10;
  document.getElementById('doneD').textContent = done;
  document.getElementById('totalD').textContent = total;
  const pct = Math.round(100*done/total);
  document.getElementById('pctD').textContent = pct + '%';
  document.getElementById('fillD').style.width = pct + '%';
}
function renderBases(bases){
  const body = document.getElementById('bases-body');
  body.textContent = '';
  bases.forEach(function(b){
    const tr = document.createElement('tr');
    const tdDomain = document.createElement('td');
    const domLink = document.createElement('a');
    domLink.href = '/rag/' + encodeURIComponent(b.slug);
    domLink.textContent = b.domain;
    tdDomain.appendChild(domLink);
    const tdSit = document.createElement('td'); tdSit.textContent = b.sit;
    const tdExec = document.createElement('td');
    const badge = document.createElement('span');
    badge.className = 'badge ' + (b.exec === 'Executando' ? 'run' : 'stop');
    badge.textContent = b.exec;
    tdExec.appendChild(badge);
    const tdTrain = document.createElement('td'); tdTrain.textContent = b.train;
    const tdAct = document.createElement('td');
    const actions = document.createElement('div'); actions.className = 'actions';
    const btnZip = document.createElement('button'); btnZip.className = 'btn'; btnZip.textContent = 'Exportar .zip';
    btnZip.addEventListener('click', function(){ baseAction('zip', b.domain); });
    const btnDel = document.createElement('button'); btnDel.className = 'btn danger'; btnDel.textContent = 'Excluir';
    btnDel.addEventListener('click', function(){ baseAction('del', b.domain); });
    actions.appendChild(btnZip); actions.appendChild(btnDel);
    tdAct.appendChild(actions);
    tr.appendChild(tdDomain); tr.appendChild(tdSit); tr.appendChild(tdExec); tr.appendChild(tdTrain); tr.appendChild(tdAct);
    body.appendChild(tr);
  });
}
function renderLineChart(bench){
  const wrap = document.getElementById('bench-line');
  wrap.textContent = '';
  const W = 720, H = 260, padL = 46, padR = 14, padT = 14, padB = 38;
  const plotW = W - padL - padR, plotH = H - padT - padB;
  let max = 0; bench.forEach(function(b){ max = Math.max(max, b.rag, b.norag); });
  max = Math.max(1, Math.ceil(max));
  const n = bench.length;
  const X = function(i){ return padL + (n === 1 ? plotW/2 : i * plotW/(n-1)); };
  const Y = function(v){ return padT + plotH * (1 - v/max); };
  let svg = '<svg viewBox="0 0 '+W+' '+H+'" preserveAspectRatio="xMidYMid meet" role="img" aria-label="tempo por teste">';
  for (let g=0; g<=4; g++){
    const gy = padT + plotH*g/4;
    const val = (max*(4-g)/4).toFixed(1);
    svg += '<line x1="'+padL+'" y1="'+gy+'" x2="'+(W-padR)+'" y2="'+gy+'" stroke="#222a31" stroke-width="1"/>';
    svg += '<text x="'+(padL-7)+'" y="'+(gy+4)+'" fill="#7d8794" font-size="11" text-anchor="end">'+val+'s</text>';
  }
  bench.forEach(function(b,i){
    svg += '<text x="'+X(i)+'" y="'+(H-padB+16)+'" fill="#7d8794" font-size="10" text-anchor="middle">T'+(i+1)+'</text>';
  });
  const ptsRag = bench.map(function(b,i){ return X(i)+','+Y(b.rag); }).join(' ');
  const ptsNor = bench.map(function(b,i){ return X(i)+','+Y(b.norag); }).join(' ');
  svg += '<polyline points="'+ptsRag+'" fill="none" stroke="#5bb0ff" stroke-width="2.5"/>';
  svg += '<polyline points="'+ptsNor+'" fill="none" stroke="#ff7b7b" stroke-width="2.5"/>';
  bench.forEach(function(b,i){
    svg += '<circle cx="'+X(i)+'" cy="'+Y(b.rag)+'" r="3.5" fill="#1f6fd6"/>';
    svg += '<circle cx="'+X(i)+'" cy="'+Y(b.norag)+'" r="3.5" fill="#d63a3a"/>';
  });
  svg += '</svg>';
  wrap.innerHTML = svg;
}
function renderSuperiority(bench){
  const wrap = document.getElementById('bench-sup');
  const ragOk = bench.filter(function(b){ return b.ragOk; }).length;
  const total = bench.length;
  const ragPct = Math.round(100*ragOk/total);
  wrap.innerHTML =
    '<div class="sup-row"><span class="sup-label">Com RAG</span>'+
      '<div class="sup-bar"><div class="sup-fill rag" style="width:'+ragPct+'%"></div></div>'+
      '<span class="sup-val">'+ragOk+'/'+total+' ('+ragPct+'%)</span></div>'+
    '<div class="sup-row"><span class="sup-label">Sem RAG</span>'+
      '<div class="sup-bar"><div class="sup-fill norag" style="width:0%"></div></div>'+
      '<span class="sup-val">0/'+total+' (0%)</span></div>'+
    '<div class="sup-verdict">Veredito: RAG foi superior em <b>'+ragOk+'/'+total+'</b> testes que atingiram o objetivo.</div>';
}
function baseAction(act, domain){
  alert('Backend pendente: ação "'+act+'" na base "'+domain+'".\\n(será implementada quando o backend for liberado)');
}
function pieSVG(pass, fail){
  const total = pass + fail || 1;
  const p = pass / total;
  const C = 2 * Math.PI * 50;
  const dash = (p * C).toFixed(2);
  return '<svg class="pie-svg" width="92" height="92" viewBox="0 0 120 120" role="img" aria-label="pass/fail">'
    + '<circle cx="60" cy="60" r="50" fill="none" stroke="#d63a3a" stroke-width="18"/>'
    + '<circle cx="60" cy="60" r="50" fill="none" stroke="#33ff66" stroke-width="18" stroke-dasharray="'+dash+' '+C.toFixed(2)+'" transform="rotate(-90 60 60)"/>'
    + '<text x="60" y="67" text-anchor="middle" fill="#d6dbe0" font-size="22" font-family="monospace">'+Math.round(p*100)+'%</text>'
    + '</svg>';
}
function renderPieCard(wrapId, pass, fail){
  const wrap = document.getElementById(wrapId);
  if (!wrap) return;
  wrap.innerHTML = pieSVG(pass, fail)
    + '<div class="pie-legend">'
    + '<div class="row"><i class="sw" style="background:#33ff66"></i>Sucesso <b>'+pass+'</b></div>'
    + '<div class="row"><i class="sw" style="background:#d63a3a"></i>Falha <b>'+fail+'</b></div>'
    + '</div>';
}
function renderPerf(bench){
  const n = bench.length || 1;
  let sumRag = 0, sumNor = 0, passRag = 0, passNor = 0;
  bench.forEach(function(b){ sumRag += b.rag || 0; sumNor += b.norag || 0; if (b.ragOk) passRag++; if (b.noragOk) passNor++; });
  renderPieCard('pie-rag', passRag, n - passRag);
  renderPieCard('pie-norag', passNor, n - passNor);
  const set = function(id, v){ const e = document.getElementById(id); if (e) e.textContent = v; };
  set('tot-rag', sumRag.toFixed(1) + ' s');
  set('tot-norag', sumNor.toFixed(1) + ' s');
  set('avg-rag', (sumRag / n).toFixed(2) + ' s');
  set('avg-norag', (sumNor / n).toFixed(2) + ' s');
}
function pad(n){ return String(n).padStart(2,'0'); }
function utc(d){ return d.getUTCFullYear()+'-'+pad(d.getUTCMonth()+1)+'-'+pad(d.getUTCDate())+' '+pad(d.getUTCHours())+':'+pad(d.getUTCMinutes())+':'+pad(d.getUTCSeconds()); }
function loadMock(){
  const now = new Date();
  MOCK_LOGS.forEach(function(r, i){
    r.data_hora = utc(new Date(now.getTime() - (MOCK_LOGS.length - i) * 9000));
  });
  logEl.textContent = '';
  for (const k in logsByEtapa) logsByEtapa[k].textContent = '';
  document.getElementById('pages-body').textContent = '';
  seenPages.clear();
  MOCK_LOGS.forEach(handleRow);
  applyProgress('B', 640, 1000, '2m 10s');
  applyProgress('C', 38920, 96250, '8m 40s');
  renderBench(MOCK_BENCH);
  renderLineChart(MOCK_BENCH);
  renderSuperiority(MOCK_BENCH);
  renderPerf(MOCK_BENCH);
  renderBases(MOCK_BASES);
  var sum = document.getElementById('bench-summary'); if (sum) sum.textContent = MOCK_SUMMARY;
  var nts = document.getElementById('bench-notes'); if (nts) nts.innerHTML = MOCK_NOTES_LINES.join('<br>');
}
function activateTab(t){
  document.querySelectorAll('.tab').forEach(function(x){ x.classList.toggle('on', x.dataset.t === t); });
  document.querySelectorAll('section').forEach(function(s){ s.classList.remove('show'); });
  var el = document.getElementById('p-' + t);
  if (el) el.classList.add('show');
}
var STAGE_ORDER = ['A','B','C','D'];
var STAGE_NAMES = {A:'Coleta',B:'Limpeza',C:'Indexação',D:'Avaliação'};
function maxStageOf(site){
  var list = MOCK_BASES || [];
  for (var i=0;i<list.length;i++){ if (list[i].slug === site) return list[i].stage || 'A'; }
  return 'A';
}
function applyStageGating(){
  var reached = maxStageOf(SITE);
  var idx = STAGE_ORDER.indexOf(reached);
  if (idx < 0) idx = 0;
  document.querySelectorAll('#tabs .tab').forEach(function(btn){
    var t = btn.dataset.t;
    var si = STAGE_ORDER.indexOf(t);
    if (si === -1) return;
    if (si <= idx) return;
    btn.classList.add('locked');
    btn.setAttribute('disabled','disabled');
    btn.title = 'Disponível após a etapa ' + (STAGE_NAMES[reached] || 'inicial');
  });
}
var tabsEl = document.getElementById('tabs');
if (tabsEl){
  tabsEl.addEventListener('click', function(e){
    var b = e.target.closest('.tab');
    if (!b || b.classList.contains('locked')) return;
    activateTab(b.dataset.t);
  });
}
activateTab('home');
applyStageGating();
var btnNovo = document.getElementById('btn-novo');
if (btnNovo) btnNovo.addEventListener('click', function(){ location.href = '/novo'; });
try { loadMock(); } catch (err) { console.error('loadMock falhou:', err); }
// resumo/observacoes agora sao preenchidos pelo loadMock (IA) — sem inputs editaveis
</script>
</body></html>"""
TEMPLATE = HTML

TEMPLATE_NOVO = """<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<title>ragdoll — nova base</title>
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
</style></head><body>
<header class="appbar">
  <div class="brand">ragdoll<span class="brand-sub">nova base RAG</span></div>
  <div class="spacer"></div>
  <a href="/" class="btn">← Bases RAG</a>
</header>
<main class="novo">
  <div class="novo-logo">ragdoll</div>
  <form id="novo-form" class="novo-form">
    <input id="novo-url" class="novo-input" type="url" placeholder="cole o hyperlink do site (ex: https://docs.unity3d.com/...)" autocomplete="off">
    <button id="novo-go" class="btn novo-btn" type="button">Iniciar RAG</button>
  </form>
  <div id="novo-msg" class="note"></div>
</main>
<script>
const KNOWN = ['docsgodotengineorg','godotengineorg','docsunity3dcom'];
function domainFromUrl(u){
  try { var s = u.trim(); if (s.indexOf('://') === -1) s = 'https://' + s; var host = new URL(s).hostname; if (host.indexOf('www.') === 0) host = host.slice(4); return host; } catch(e){ return ''; }
}
function slugOf(dom){ return dom.toLowerCase().replace(/^www\./,'').replace(/[^a-z0-9]/g,''); }
function go(){
  var url = document.getElementById('novo-url').value;
  var dom = domainFromUrl(url);
  var msg = document.getElementById('novo-msg');
  if (!dom || !/^[a-z0-9.-]+\.[a-z]{2,}$/i.test(dom)){ msg.textContent = 'Informe um hyperlink valido (ex: https://docs.site.com).'; return; }
  var slug = slugOf(dom);
  if (KNOWN.indexOf(slug) !== -1){ msg.textContent = 'Base ja existe — redirecionando...'; setTimeout(function(){ location.href = '/rag/' + encodeURIComponent(slug); }, 400); return; }
  msg.textContent = 'Iniciando novo processo RAG para ' + dom + '...';
  setTimeout(function(){ location.href = '/rag/' + encodeURIComponent(slug); }, 600);
}
document.getElementById('novo-go').addEventListener('click', go);
</script>
</body></html>"""
