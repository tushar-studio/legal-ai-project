const API_BASE_URL = ['127.0.0.1', 'localhost'].includes(window.location.hostname) ? 'http://127.0.0.1:8000' : window.location.origin;
const RESULTS_PLACEHOLDER = 'Search results and case analyses will populate here once a query is initiated. Enter keywords, acts, or party names in the search bar above to begin your legal research.';
const DASHBOARD_PLACEHOLDER = 'No active case selected. Please execute a search query to view real-time analytics, timeline visualization, and litigation insights.';

let selectedCase = null;
let selectedParagraphIndex = 0;
let activeResearchTab = 'paragraphs';
let searchResults = [];
let relatedTopics = [];

const escapeHtml = value => String(value ?? '').replace(/[&<>'"]/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[char]));

async function requestApi(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, options);
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `Request failed with status ${response.status}.`);
  }
  return response.json();
}

function citationLink(url, label) {
  return `<a class="source-link" href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(label)}</a>`;
}

function highlightLegalText(text, values = []) {
  const escaped = escapeHtml(text);
  const terms = values.filter(Boolean).sort((a, b) => String(b).length - String(a).length).map(value => escapeHtml(value).replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
  return terms.length ? escaped.replace(new RegExp(`(${terms.join('|')})`, 'gi'), '<mark class="legal-highlight-tint">$1</mark>') : escaped;
}

function renderTopics() {
  const root = document.getElementById('topic-list');
  root.innerHTML = relatedTopics.length ? relatedTopics.map(topic => `<button class="topic-pill" data-topic-query="${escapeHtml(topic.query)}">${escapeHtml(topic.name)}</button>`).join('') : `<p class="empty-state">${RESULTS_PLACEHOLDER}</p>`;
}

function renderCases() {
  const root = document.getElementById('cases-container');
  root.innerHTML = searchResults.length ? `${searchResults.map(item => `<button class="case-card ${selectedCase?.slug === item.slug ? 'active' : ''}" data-case="${escapeHtml(item.slug)}"><div class="case-card-meta"><span class="citation-badge">${escapeHtml(item.citation)}</span></div><h3 class="case-title">${escapeHtml(item.name)}</h3><p class="case-snippet">${escapeHtml(item.overview)}</p></button>`).join('')}<p class="source-attribution">Powered by Indian Kanoon</p>` : `<p class="empty-state">${RESULTS_PLACEHOLDER}</p>`;
}

function renderSearchSummary(data = null) {
  document.getElementById('result-count').textContent = data?.count ?? '—';
  document.getElementById('landmark-count').textContent = data?.landmark_count ?? '—';
  document.getElementById('article-count').textContent = data?.article_count ?? '—';
  document.getElementById('act-count').textContent = data?.act_count ?? '—';
  document.getElementById('search-summary-text').textContent = data?.summary || RESULTS_PLACEHOLDER;
}

function renderDashboard() {
  const root = document.getElementById('case-dashboard');
  if (!selectedCase) {
    root.innerHTML = `<div class="dashboard-empty"><i class="fa-solid fa-chart-line"></i><p>${DASHBOARD_PLACEHOLDER}</p></div>`;
    return;
  }
  const sections = [['Facts', selectedCase.facts], ['Legal Issues', selectedCase.issues], ['Arguments', selectedCase.arguments], ['Judgment', selectedCase.judgment], ['Ratio Decidendi', selectedCase.ratio_decidendi], ['Obiter Dicta', selectedCase.obiter_dicta], ['Final Decision', selectedCase.final_decision]];
  const insightMode = selectedCase.mode === 'llm-source-grounded' ? 'LLM source-grounded insight' : 'Source-grounded concise insight';
  root.innerHTML = `<div class="case-info-header"><span class="info-tag"><i class="fa-solid fa-landmark"></i> Live Indian Kanoon Source</span><h2>${escapeHtml(selectedCase.name)}</h2><div class="metadata-grid"><div><strong>Court:</strong> ${escapeHtml(selectedCase.court)}</div><div><strong>Bench:</strong> ${escapeHtml(selectedCase.bench)}</div><div><strong>Year:</strong> ${escapeHtml(selectedCase.year)}</div><div><strong>Citation:</strong> ${escapeHtml(selectedCase.citation)}</div><div class="meta-wide"><strong>Judges:</strong> ${escapeHtml(selectedCase.judges)}</div></div></div><article class="case-overview"><h3>Case Overview</h3><span class="insight-label">${escapeHtml(insightMode)}</span><p class="ai-insight">${escapeHtml(selectedCase.overview)}</p>${citationLink(selectedCase.source_url, 'Source link: original judgment on Indian Kanoon')}</article><div class="case-sections">${sections.map(([title, text]) => `<details><summary>${title}</summary><div class="case-section-text"><span class="insight-label">${escapeHtml(insightMode)}</span><p class="ai-insight">${escapeHtml(text)}</p>${citationLink(selectedCase.source_url, 'Source link: original judgment on Indian Kanoon')}</div></details>`).join('')}</div><div class="research-actions"><button data-action="citation">Generate Citation</button><button data-action="export-summary">Export Summary</button><button data-action="compare">Compare with another case</button><button data-action="notes">Generate Research Notes</button><button data-action="download-pdf">Print / Save PDF</button></div><p class="source-attribution">Powered by Indian Kanoon</p>`;
}

function renderResearchPanel() {
  const root = document.getElementById('research-panel');
  if (!selectedCase) {
    root.innerHTML = `<p class="empty-state">${RESULTS_PLACEHOLDER}</p>`;
    return;
  }
  const paragraphs = selectedCase.paragraphs || [];
  if (activeResearchTab === 'paragraphs') {
    root.innerHTML = `<div class="research-heading"><h3>Source Paragraphs</h3><p>Original paragraphs retrieved from Indian Kanoon. Select a paragraph to inspect its mapped references.</p></div>${paragraphs.length ? `<div class="para-map-list">${paragraphs.map((item, index) => `<button class="para-map-item ${index === selectedParagraphIndex ? 'active' : ''}" data-paragraph="${index}"><span class="para-label">Paragraph ${escapeHtml(item.paragraph_number)}</span><span class="para-classification-badge">${escapeHtml(item.classification)}</span></button>`).join('')}</div>` : '<p class="empty-state">No source paragraphs were returned for this judgment.</p>'}`;
  } else if (activeResearchTab === 'analysis') {
    const paragraph = paragraphs[selectedParagraphIndex];
    root.innerHTML = paragraph ? `<div class="paragraph-analysis"><h3>Paragraph ${escapeHtml(paragraph.paragraph_number)}: ${escapeHtml(paragraph.classification)}</h3><section><h4>Original Paragraph</h4><blockquote>${highlightLegalText(paragraph.original_text, [...paragraph.legal_terms, ...paragraph.referenced_articles, ...paragraph.referenced_acts, ...paragraph.referenced_cases])}</blockquote><p class="granular-citation"><strong>Source reference:</strong> ${escapeHtml(paragraph.citation_label)} · ${citationLink(paragraph.source_url, 'Open source section')}</p></section><section><h4>Source-Grounded Analysis</h4><p>${escapeHtml(paragraph.simplified_explanation)}</p><p class="granular-citation"><strong>Evidence:</strong> ${escapeHtml(paragraph.citation_label)} · ${citationLink(paragraph.source_url, 'Indian Kanoon')}</p></section><section><h4>Important Legal Terms</h4><div class="tag-row">${paragraph.legal_terms.map(value => `<span>${escapeHtml(value)}</span>`).join('') || '<span>No extracted terms</span>'}</div></section><section><h4>Referenced Authorities</h4><p><strong>Articles:</strong> ${escapeHtml(paragraph.referenced_articles.join(', ') || 'Not identified')}<br><strong>Acts:</strong> ${escapeHtml(paragraph.referenced_acts.join(', ') || 'Not identified')}<br><strong>Previous cases:</strong> ${escapeHtml(paragraph.referenced_cases.join(', ') || 'Not identified')}</p></section><section><h4>Why this paragraph is relevant</h4><p>${escapeHtml(paragraph.relevance)}</p><p class="granular-citation"><strong>Evidence:</strong> ${escapeHtml(paragraph.citation_label)} · ${citationLink(paragraph.source_url, 'Indian Kanoon')}</p></section></div>` : '<p class="empty-state">Select a source paragraph to view its analysis.</p>';
  } else if (activeResearchTab === 'tree') {
    const tree = selectedCase.heritage;
    root.innerHTML = tree ? `<div class="tree-wrapper"><div class="tree-node root-node"><span class="node-badge">Selected judgment</span><h4>${escapeHtml(tree.root.topics[0])}</h4><p>Live citation relationships supplied by the source.</p></div><div class="tree-line"></div>${tree.nodes.map((node, index) => `<div class="tree-node ${node.is_current ? 'tree-current' : ''}"><span class="node-badge branch">${escapeHtml(node.relationship)}</span><h4>${escapeHtml(node.name)} (${escapeHtml(node.year)})</h4></div>${index < tree.nodes.length - 1 ? '<div class="tree-line short"></div>' : ''}`).join('')}</div>` : '<p class="empty-state">Citation relationships are unavailable for this judgment.</p>';
  } else if (activeResearchTab === 'similar') {
    const similar = selectedCase.similar || [];
    root.innerHTML = `<div class="research-heading"><h3>Similar Case Recommendation</h3><p>These are cited authorities returned by the live source, not invented similarity scores.</p></div><div class="similar-list">${similar.length ? similar.map(item => `<div class="similar-card"><strong>Source</strong><span>${escapeHtml(item.name)}<small>${escapeHtml(item.reason)}</small>${citationLink(item.source_url, 'Open on Indian Kanoon')}</span></div>`).join('') : '<p class="empty-state">No cited authorities were supplied by the source.</p>'}</div>`;
  } else {
    const graph = selectedCase.graph;
    root.innerHTML = graph ? `<div class="research-heading"><h3>Knowledge Graph</h3><p>${escapeHtml(graph.case)}</p></div><div class="knowledge-graph">${Object.entries(graph.nodes).map(([label, values]) => `<section><h4>${escapeHtml(label)}</h4>${values.length ? `<div class="tag-row">${values.map(value => `<span>${escapeHtml(value)}</span>`).join('')}</div>` : '<p>Not supplied by the live source.</p>'}</section>`).join('')}</div>` : '<p class="empty-state">Knowledge graph data is unavailable for this judgment.</p>';
  }
}

function renderLiveAnalyzer() {
  const root = document.getElementById('analyzer-results');
  if (!selectedCase) {
    root.innerHTML = `<p>Live Indian Kanoon judgment analysis will populate here after a case is selected from search results.</p>`;
    return;
  }
  const paragraphs = selectedCase.paragraphs || [];
  root.innerHTML = `<h3>${escapeHtml(selectedCase.name)}</h3><p>Live source analysis with granular paragraph citations.</p>${paragraphs.slice(0, 10).map(paragraph => `<details class="document-paragraph"><summary>Paragraph ${escapeHtml(paragraph.paragraph_number)} <span>${escapeHtml(paragraph.classification)}</span></summary><p>${highlightLegalText(paragraph.original_text, paragraph.legal_terms)}</p><p class="granular-citation">${escapeHtml(paragraph.citation_label)} · ${citationLink(paragraph.source_url, 'Open source')}</p></details>`).join('')}<p class="source-attribution">Powered by Indian Kanoon</p>`;
}

async function runSearch(query) {
  const term = query.trim();
  if (!term) {
    searchResults = []; relatedTopics = []; selectedCase = null; renderTopics(); renderCases(); renderSearchSummary(); renderDashboard(); renderResearchPanel(); renderLiveAnalyzer();
    return;
  }
  document.getElementById('search-summary-text').textContent = 'Searching live Indian Kanoon legal data…';
  try {
    const result = await requestApi(`/api/search?${new URLSearchParams({ query: term })}`);
    searchResults = result.results; relatedTopics = result.related_topics; selectedCase = null;
    renderSearchSummary(result); renderTopics(); renderCases(); renderDashboard(); renderResearchPanel(); renderLiveAnalyzer();
  } catch (error) {
    searchResults = []; relatedTopics = []; renderTopics(); renderCases(); renderSearchSummary();
    document.getElementById('search-summary-text').textContent = error.message;
  }
}

async function selectCase(slug) {
  try {
    const [caseData, paragraphs, similar, heritage, graph] = await Promise.all([requestApi(`/api/cases/${slug}`), requestApi(`/api/cases/${slug}/paragraphs`), requestApi(`/api/cases/${slug}/similar`), requestApi(`/api/cases/${slug}/heritage`), requestApi(`/api/cases/${slug}/graph`)]);
    selectedCase = { ...caseData, paragraphs, similar, heritage, graph }; selectedParagraphIndex = 0; activeResearchTab = 'paragraphs';
    document.querySelectorAll('.dash-tab').forEach(button => button.classList.toggle('active', button.dataset.tab === activeResearchTab));
    renderCases(); renderDashboard(); renderResearchPanel(); renderLiveAnalyzer();
  } catch (error) {
    document.getElementById('case-dashboard').innerHTML = `<div class="dashboard-empty"><p>${escapeHtml(error.message)}</p></div>`;
  }
}

function handleResearchAction(action) {
  if (!selectedCase) return;
  const caseData = selectedCase;
  if (action === 'citation') {
    const text = `${caseData.name}. ${caseData.citation}. Indian Kanoon. ${caseData.source_url}`;
    navigator.clipboard?.writeText(text); alert('Citation copied to the clipboard.');
  } else if (action === 'export-summary') {
    const text = `${caseData.name}\n${caseData.citation}\n\n${caseData.overview}\n\nSource: ${caseData.source_url}`;
    const link = document.createElement('a'); link.href = URL.createObjectURL(new Blob([text], { type: 'text/plain' })); link.download = 'legal-research-summary.txt'; link.click(); URL.revokeObjectURL(link.href);
  } else if (action === 'compare') {
    activeResearchTab = 'similar'; document.querySelectorAll('.dash-tab').forEach(button => button.classList.toggle('active', button.dataset.tab === 'similar')); renderResearchPanel();
  } else if (action === 'notes') {
    const text = prompt('Enter a research note for this judgment:'); if (text) localStorage.setItem(`legal-ai-note-${caseData.slug}`, text);
  } else if (action === 'download-pdf') window.print();
}

function generateDraft() {
  const type = document.getElementById('draft-type-select').value;
  const facts = escapeHtml(document.getElementById('draft-variables').value.trim() || '[Enter verified facts and jurisdiction details]');
  const title = { writ: 'WRIT PETITION UNDER ARTICLE 32', nda: 'MUTUAL NON-DISCLOSURE AGREEMENT', defamation: 'LEGAL NOTICE FOR DEFAMATION' }[type];
  document.getElementById('draft-output-container').innerHTML = `<div class="legal-title-center">${title}</div><div class="legal-document-text"><strong>IN THE MATTER OF:</strong><br>${facts}<br><br>This is a baseline template and must be reviewed by a qualified legal professional before use.</div>`;
}

function initializeEvents() {
  document.addEventListener('click', event => {
    const module = event.target.closest('[data-module]'); if (module) { document.querySelectorAll('.nav-item').forEach(button => button.classList.toggle('active', button === module)); document.querySelectorAll('.module-view').forEach(view => view.classList.toggle('active', view.id === `module-${module.dataset.module}`)); }
    const caseButton = event.target.closest('[data-case]'); if (caseButton) selectCase(caseButton.dataset.case);
    const topicButton = event.target.closest('[data-topic-query]'); if (topicButton) { document.getElementById('legal-search').value = topicButton.dataset.topicQuery; runSearch(topicButton.dataset.topicQuery); }
    const paragraph = event.target.closest('[data-paragraph]'); if (paragraph) { selectedParagraphIndex = Number(paragraph.dataset.paragraph); activeResearchTab = 'analysis'; document.querySelectorAll('.dash-tab').forEach(button => button.classList.toggle('active', button.dataset.tab === 'analysis')); renderResearchPanel(); }
    const tab = event.target.closest('[data-tab]'); if (tab) { activeResearchTab = tab.dataset.tab; document.querySelectorAll('.dash-tab').forEach(button => button.classList.toggle('active', button === tab)); renderResearchPanel(); }
    const action = event.target.closest('[data-action]'); if (action) handleResearchAction(action.dataset.action);
  });
  let timer;
  document.getElementById('legal-search').addEventListener('input', event => { clearTimeout(timer); timer = setTimeout(() => runSearch(event.target.value), 350); });
  document.getElementById('generate-draft').addEventListener('click', generateDraft);
  document.getElementById('chat-form').addEventListener('submit', async event => { event.preventDefault(); const input = document.getElementById('chat-user-input'); const question = input.value.trim(); if (!question || !selectedCase) return; const messages = document.getElementById('chat-messages'); messages.insertAdjacentHTML('beforeend', `<div class="user-chat-bubble">${escapeHtml(question)}</div>`); input.value = ''; try { const result = await requestApi('/api/research/answer', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question, case_slug: selectedCase.slug }) }); const sources = result.sources.map(source => `<div class="chat-source"><strong>${escapeHtml(source.name)}</strong> — ${escapeHtml(source.citation)}<br>${citationLink(source.source_url, 'Open source')}<br><span>${escapeHtml(source.excerpt)}</span></div>`).join(''); messages.insertAdjacentHTML('beforeend', `<div class="ai-chat-bubble"><div class="bubble-avatar"><i class="fa-solid fa-robot"></i></div><div class="bubble-content">${escapeHtml(result.answer)}<br><br><strong>Source references</strong>${sources}<br><br><em>${escapeHtml(result.notice)}</em></div></div>`); } catch (error) { messages.insertAdjacentHTML('beforeend', `<div class="ai-chat-bubble"><div class="bubble-avatar"><i class="fa-solid fa-robot"></i></div><div class="bubble-content">${escapeHtml(error.message)}</div></div>`); } messages.scrollTop = messages.scrollHeight; });
}

document.addEventListener('DOMContentLoaded', () => { renderTopics(); renderCases(); renderSearchSummary(); renderDashboard(); renderResearchPanel(); renderLiveAnalyzer(); initializeEvents(); });
