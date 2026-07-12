const casesData = {
  romesh: { name: 'Romesh Thappar v. State of Madras', year: '1950', citation: '1950 AIR 124', bench: '5 Judges', judges: 'Supreme Court of India', topics: ['Press Freedom', 'Freedom of Speech', 'Reasonable Restrictions'], overview: 'A foundational decision holding that freedom of speech includes the freedom to circulate ideas.', facts: 'The Madras Government prohibited the entry and circulation of the weekly journal Cross Roads under the Madras Maintenance of Public Order Act, 1949.', issues: 'Whether the prohibition violated Article 19(1)(a), and whether the statute was protected by Article 19(2).', arguments: 'The petitioner challenged the circulation ban as an unconstitutional restriction on press freedom.', judgment: 'The Court struck down the order because public order was not then a permitted ground under Article 19(2).', ratio: 'Freedom of speech includes freedom of propagation, which requires freedom of circulation.', obiter: 'Restrictions on speech must fall strictly within the constitutional exceptions.', decision: 'Petition allowed; prohibition order invalidated.', paragraphs: [{ number: 'Paragraph 8', tag: 'Facts', original: 'The petitioner is the printer, publisher and editor of a weekly journal called Cross Roads. The Madras Government issued an order imposing a total ban on its circulation inside the State.', simple: 'The State completely stopped this magazine from being distributed in Madras.', terms: ['Circulation', 'Executive order'], articles: ['Article 19(1)(a)'], acts: ['Madras Maintenance of Public Order Act, 1949'], references: [], relevance: 'It establishes the factual basis for testing the restriction on free speech.' }, { number: 'Paragraph 14', tag: 'Freedom of Speech', original: 'Freedom of speech and expression includes freedom of propagation of ideas, and that freedom is ensured by the freedom of circulation.', simple: 'Ideas are useful only when people can receive them; therefore, circulation is part of free speech.', terms: ['Freedom of circulation', 'Propagation of ideas'], articles: ['Article 19(1)(a)'], acts: [], references: [], relevance: 'This is the core legal principle of the case.' }, { number: 'Paragraph 20', tag: 'Public Order', original: 'A law restricting expression can survive only when the restriction is authorised by the constitutional grounds then available under Article 19(2).', simple: 'The government cannot limit speech for reasons that the Constitution does not permit.', terms: ['Reasonable restriction', 'Public order'], articles: ['Article 19(2)'], acts: ['Madras Maintenance of Public Order Act, 1949'], references: [], relevance: 'It explains why the impugned law could not justify the circulation ban.' }], similar: [['Brij Bhushan v. State of Delhi', '92%'], ['Bennett Coleman v. Union of India', '89%'], ['Indian Express Newspapers v. Union of India', '85%'], ['Shreya Singhal v. Union of India', '82%']] },
  brij: { name: 'Brij Bhushan v. State of Delhi', year: '1950', citation: '1950 AIR 129', bench: '5 Judges', judges: 'Supreme Court of India', topics: ['Press Freedom', 'Prior Restraint', 'Freedom of Speech'], overview: 'A leading decision against prior censorship of the press.', facts: 'The publisher of Organizer was directed to submit specified material for scrutiny before publication.', issues: 'Whether pre-censorship violated Article 19(1)(a).', arguments: 'The order imposed an unconstitutional prior restraint on publication.', judgment: 'The Court invalidated the pre-censorship order.', ratio: 'Prior restraint is a serious restriction on press freedom.', obiter: 'Any restraint must satisfy Article 19(2).', decision: 'Order struck down.', paragraphs: [], similar: [['Romesh Thappar v. State of Madras', '92%'], ['Bennett Coleman v. Union of India', '87%']] },
  bennett: { name: 'Bennett Coleman v. Union of India', year: '1972', citation: '1973 SCR (2) 757', bench: '5 Judges', judges: 'Supreme Court of India', topics: ['Press Freedom', 'Media Regulation', 'Freedom of Speech'], overview: 'Newsprint controls could not indirectly restrict the reach of newspapers.', facts: 'Newsprint policy limited newspaper page capacity.', issues: 'Whether economic regulation directly affected free speech.', arguments: 'Page limits reduced circulation and expression.', judgment: 'The policy was held unconstitutional in relevant respects.', ratio: 'Direct impact on speech matters even if the law concerns an economic subject.', obiter: 'Press freedom protects circulation and content choices.', decision: 'Petition allowed.', paragraphs: [], similar: [['Romesh Thappar v. State of Madras', '89%'], ['Indian Express Newspapers v. Union of India', '91%']] },
  indian_express: { name: 'Indian Express Newspapers v. Union of India', year: '1985', citation: '1985 SCC (1) 641', bench: '2 Judges', judges: 'Supreme Court of India', topics: ['Press Freedom', 'Media Regulation', 'Reasonable Restrictions'], overview: 'Taxes on newsprint cannot become a tool to suppress the press.', facts: 'Import duty on newsprint increased publication costs.', issues: 'Whether the fiscal burden impaired press freedom.', arguments: 'The levy threatened circulation and access to information.', judgment: 'The Court required special care when taxation affects the press.', ratio: 'Taxes must not be excessive enough to stifle free expression.', obiter: 'The press holds a vital democratic role.', decision: 'Directions issued for reconsideration.', paragraphs: [], similar: [['Bennett Coleman v. Union of India', '91%'], ['Romesh Thappar v. State of Madras', '85%']] },
  shreya: { name: 'Shreya Singhal v. Union of India', year: '2015', citation: '(2015) 5 SCC 1', bench: '2 Judges', judges: 'Supreme Court of India', topics: ['Freedom of Speech', 'Media Regulation', 'Reasonable Restrictions'], overview: 'Section 66A of the IT Act was struck down for vagueness and overbreadth.', facts: 'Arrests were made over online comments under Section 66A.', issues: 'Whether vague online speech restrictions create a chilling effect.', arguments: 'The provision lacked clear standards and enabled arbitrary enforcement.', judgment: 'Section 66A was struck down.', ratio: 'Vague and overbroad restrictions chill protected speech.', obiter: 'Discussion, advocacy and incitement require different treatment.', decision: 'Section 66A invalidated.', paragraphs: [], similar: [['Romesh Thappar v. State of Madras', '82%'], ['Brij Bhushan v. State of Delhi', '80%']] }
};

const API_BASE_URL = ['127.0.0.1', 'localhost'].includes(window.location.hostname) ? 'http://127.0.0.1:8000' : window.location.origin;
let selectedCaseKey = 'romesh';
let selectedParagraphIndex = 0;
let activeResearchTab = 'paragraphs';
let allTopics = [...new Set(Object.values(casesData).flatMap(item => item.topics))];
let searchMeta = null;

const escapeHtml = value => String(value).replace(/[&<>'"]/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[char]));

function normalizeApiCase(raw) {
  const topics = Array.isArray(raw.topics) ? raw.topics : String(raw.topics || '').split(/\s{2,}|(?<=Rights)|(?<=Speech)|(?<=Freedom)|(?<=Regulation)|(?<=Restraint)|(?<=Restrictions)/).map(value => value.trim()).filter(Boolean);
  return { ...raw, year: String(raw.year), topics, ratio: raw.ratio_decidendi, obiter: raw.obiter_dicta, decision: raw.final_decision, paragraphs: [], similar: [] };
}

function normalizeParagraph(raw) {
  return { number: raw.paragraph_number, tag: raw.classification, original: raw.original_text, simple: raw.simplified_explanation, terms: raw.legal_terms, articles: raw.referenced_articles, acts: raw.referenced_acts, references: raw.referenced_cases, relevance: raw.relevance };
}

async function requestApi(path) {
  const response = await fetch(`${API_BASE_URL}${path}`);
  if (!response.ok) throw new Error(`API request failed: ${response.status}`);
  return response.json();
}

async function postApi(path, body) {
  const response = await fetch(`${API_BASE_URL}${path}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  if (!response.ok) throw new Error(`API request failed: ${response.status}`);
  return response.json();
}

function renderAnalyzerResult(analysis, paragraphs = []) {
  const root = document.getElementById('analyzer-results');
  const risks = analysis.risk_vectors || [];
  const summary = analysis.paragraph_summary || [];
  const paragraphList = paragraphs.slice(0, 12).map(paragraph => `<details class="document-paragraph"><summary>Page ${paragraph.page_number}, Paragraph ${paragraph.paragraph_number} <span>${escapeHtml(paragraph.classification)}</span></summary><p>${highlightLegalText(paragraph.original_text, [...paragraph.legal_terms, ...paragraph.referenced_articles, ...paragraph.referenced_acts, ...paragraph.referenced_cases])}</p></details>`).join('');
  root.innerHTML = `<h3>${escapeHtml(analysis.filename)}</h3><p>${analysis.page_count} page(s) · ${analysis.extracted_characters.toLocaleString()} characters · ${escapeHtml(analysis.status)}</p>${summary.length ? `<div class="paragraph-summary"><strong>Processed paragraphs</strong>${summary.map(item => `<span>${escapeHtml(item.classification)}: ${item.count}</span>`).join('')}</div>` : ''}${paragraphList ? `<h3 class="paragraph-list-title">AI-read paragraphs</h3>${paragraphList}` : ''}${risks.length ? risks.map(risk => `<section class="risk-card"><strong>${escapeHtml(risk.title)}</strong><span>${risk.mentions} mention(s)</span><p>${escapeHtml(risk.recommendation)}</p></section>`).join('') : '<p>No configured risk terms were found. This does not mean the document is risk-free.</p>'}<p class="analysis-notice">${escapeHtml(analysis.notice)}</p>`;
}

function handleResearchAction(action) {
  const item = casesData[selectedCaseKey];
  if (action === 'citation') {
    const citation = `${item.name}, ${item.citation} (${item.year}).`;
    navigator.clipboard?.writeText(citation).catch(() => {});
    alert(`Citation copied:\n${citation}`);
  } else if (action === 'notes') {
    const notes = prompt('Add a research note for this case:');
    if (notes) { localStorage.setItem(`legal-ai-note-${selectedCaseKey}`, notes); alert('Research note saved in this browser.'); }
  } else if (action === 'compare') {
    const choices = Object.entries(casesData).filter(([key]) => key !== selectedCaseKey);
    const selection = prompt(`Compare with:\n${choices.map(([key, value], index) => `${index + 1}. ${value.name}`).join('\n')}\n\nEnter a number:`);
    const other = choices[Number(selection) - 1]?.[1];
    if (other) alert(`${item.name}\nRatio: ${item.ratio}\n\n${other.name}\nRatio: ${other.ratio}`);
  } else if (action === 'export-summary') {
    const text = `${item.name}\n${item.citation} (${item.year})\n\nOverview\n${item.overview}\n\nFacts\n${item.facts}\n\nLegal Issues\n${item.issues}\n\nRatio Decidendi\n${item.ratio}\n\nFinal Decision\n${item.decision}`;
    const link = document.createElement('a'); link.href = URL.createObjectURL(new Blob([text], { type: 'text/plain' })); link.download = `${selectedCaseKey}-research-summary.txt`; link.click(); URL.revokeObjectURL(link.href);
  } else if (action === 'download-pdf') {
    window.print();
  }
}

async function loadCasesFromApi(query = '', topic = '') {
  const params = new URLSearchParams();
  if (query) params.set('query', query);
  if (topic) params.set('topic', topic);
  const result = await requestApi(`/api/search?${params.toString()}`);
  searchMeta = result;
  Object.keys(casesData).forEach(key => delete casesData[key]);
  result.results.forEach(raw => { casesData[raw.slug] = normalizeApiCase(raw); });
  renderTopics(query ? result.related_topics : allTopics, topic);
  if (!casesData[selectedCaseKey]) selectedCaseKey = Object.keys(casesData)[0] || selectedCaseKey;
  renderCases();
  if (casesData[selectedCaseKey]) { renderDashboard(); renderResearchPanel(); }
}

async function loadSelectedCaseFromApi(slug) {
  const [rawCase, rawParagraphs, rawSimilar, heritage, graph] = await Promise.all([
    requestApi(`/api/cases/${slug}`),
    requestApi(`/api/cases/${slug}/paragraphs`),
    requestApi(`/api/cases/${slug}/similar`),
    requestApi(`/api/cases/${slug}/heritage`),
    requestApi(`/api/cases/${slug}/graph`)
  ]);
  casesData[slug] = { ...normalizeApiCase(rawCase), paragraphs: rawParagraphs.map(normalizeParagraph), similar: rawSimilar.map(item => ({ ...item, score: `${Math.round(item.similarity_score * 100)}%` })), heritage, graph };
}

function renderTopics(topics = allTopics, activeTopic = '') {
  document.getElementById('topic-list').innerHTML = topics.map(topic => `<button class="topic-pill ${topic === activeTopic ? 'active' : ''}" data-topic="${topic}">${topic}</button>`).join('') || '<p class="empty-state">No related topics found.</p>';
}

function highlightLegalText(text, values = []) {
  const escaped = escapeHtml(text);
  const terms = values.filter(Boolean).sort((a, b) => b.length - a.length).map(value => escapeHtml(value).replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
  return terms.length ? escaped.replace(new RegExp(`(${terms.join('|')})`, 'gi'), '<mark class="legal-highlight-tint">$1</mark>') : escaped;
}

function renderCases(query = '', topic = '') {
  const needle = query.toLowerCase();
  const entries = Object.entries(casesData).filter(([, item]) => (!topic || item.topics.includes(topic)) && `${item.name} ${item.year} ${item.overview} ${item.topics.join(' ')}`.toLowerCase().includes(needle));
  document.getElementById('cases-container').innerHTML = entries.map(([key, item]) => `<button class="case-card ${key === selectedCaseKey ? 'active' : ''}" data-case="${key}"><div class="case-card-meta"><span class="year-badge">${item.year}</span><span class="citation-badge">${item.citation}</span></div><h3 class="case-title">${item.name}</h3><p class="case-snippet">${item.overview}</p></button>`).join('') || '<p class="empty-state">No matching cases found.</p>';
  document.getElementById('result-count').textContent = searchMeta?.count ?? entries.length;
  document.getElementById('landmark-count').textContent = searchMeta?.landmark_count ?? entries.length;
  document.getElementById('article-count').textContent = searchMeta?.article_count ?? '—';
  document.getElementById('act-count').textContent = searchMeta?.act_count ?? '—';
  document.getElementById('search-summary-text').textContent = searchMeta?.summary ?? (query ? `${entries.length} local judgment(s) found for ${query}.` : 'Browse landmark Indian constitutional-law precedents.');
}

function renderDashboard() {
  const item = casesData[selectedCaseKey];
  const sections = [['Facts', item.facts], ['Legal Issues', item.issues], ['Arguments', item.arguments], ['Judgment', item.judgment], ['Ratio Decidendi', item.ratio], ['Obiter Dicta', item.obiter], ['Final Decision', item.decision]];
  document.getElementById('case-dashboard').innerHTML = `<div class="case-info-header"><span class="info-tag"><i class="fa-solid fa-landmark"></i> Supreme Court of India</span><h2>${item.name}</h2><div class="metadata-grid"><div><strong>Bench:</strong> ${item.bench}</div><div><strong>Year:</strong> ${item.year}</div><div><strong>Citation:</strong> ${item.citation}</div><div class="meta-wide"><strong>Judges:</strong> ${item.judges}</div></div></div><article class="case-overview"><h3>Case Overview</h3><p>${item.overview}</p></article><div class="case-sections">${sections.map(([title, text]) => `<details><summary>${title}</summary><p>${text}</p></details>`).join('')}</div><div class="research-actions"><button data-action="citation">Generate Citation</button><button data-action="export-summary">Export Summary</button><button data-action="compare">Compare Case</button><button data-action="notes">Research Notes</button><button data-action="download-pdf">Print / Save PDF</button></div>`;
}

function renderResearchPanel() {
  const item = casesData[selectedCaseKey];
  const root = document.getElementById('research-panel');
  if (activeResearchTab === 'paragraphs') {
    root.innerHTML = `<div class="research-heading"><h3>AI Highlighted Paragraphs</h3><p>Select a paragraph for detailed analysis.</p></div>${item.paragraphs.length ? `<div class="para-map-list">${item.paragraphs.map((p, index) => `<button class="para-map-item ${index === selectedParagraphIndex ? 'active' : ''}" data-paragraph="${index}"><span class="para-label">${p.number}</span><span class="para-classification-badge">${p.tag}</span></button>`).join('')}</div>` : '<p class="empty-state">Paragraph extraction will appear after judgment ingestion.</p>'}`;
  } else if (activeResearchTab === 'analysis') {
    const p = item.paragraphs[selectedParagraphIndex];
    root.innerHTML = p ? `<div class="paragraph-analysis"><h3>${p.number}: ${p.tag}</h3><section><h4>Original Paragraph</h4><blockquote>${highlightLegalText(p.original, [...p.terms, ...p.articles, ...p.acts, ...p.references])}</blockquote></section><section><h4>AI Simplified Explanation</h4><p>${escapeHtml(p.simple)}</p></section><section><h4>Legal Terms</h4><div class="tag-row">${p.terms.map(value => `<span>${escapeHtml(value)}</span>`).join('')}</div></section><section><h4>Referenced Authorities</h4><p><strong>Articles:</strong> ${escapeHtml(p.articles.join(', ') || '—')}<br><strong>Acts:</strong> ${escapeHtml(p.acts.join(', ') || '—')}<br><strong>Previous cases:</strong> ${escapeHtml(p.references.join(', ') || '—')}</p></section><section><h4>Why it is relevant</h4><p>${escapeHtml(p.relevance)}</p></section></div>` : '<p class="empty-state">Choose a case with extracted paragraphs to view analysis.</p>';
  } else if (activeResearchTab === 'tree') {
    const heritage = item.heritage;
    root.innerHTML = heritage ? `<div class="tree-wrapper"><div class="tree-node root-node"><span class="node-badge">Research topics</span><h4>${heritage.root.topics.map(escapeHtml).join(', ')}</h4><p>Cases connected by shared topics in the local database.</p></div><div class="tree-line"></div>${heritage.nodes.map((node, index) => `<div class="tree-node ${node.is_current ? 'tree-current' : ''}"><span class="node-badge branch">${escapeHtml(node.relationship)}</span><h4>${escapeHtml(node.name)} (${node.year})</h4></div>${index < heritage.nodes.length - 1 ? '<div class="tree-line short"></div>' : ''}`).join('')}</div>` : '<p class="empty-state">Load a case from the local API to view its research tree.</p>';
  } else if (activeResearchTab === 'graph') {
    const graph = item.graph;
    root.innerHTML = graph ? `<div class="research-heading"><h3>Knowledge Graph</h3><p>${escapeHtml(graph.case)}</p></div><div class="knowledge-graph">${Object.entries(graph.nodes).map(([label, values]) => `<section><h4>${escapeHtml(label)}</h4>${values.length ? `<div class="tag-row">${values.map(value => `<span>${escapeHtml(value)}</span>`).join('')}</div>` : '<p>Not available in this local record.</p>'}</section>`).join('')}</div>` : '<p class="empty-state">Load a case from the local API to view its graph.</p>';
  } else {
    root.innerHTML = `<div class="research-heading"><h3>Similar Case Recommendation</h3><p>Scores are calculated from shared legal topics and case-language overlap.</p></div><div class="similar-list">${item.similar.map(entry => { const data = Array.isArray(entry) ? { name: entry[0], score: entry[1], reason: 'Local fallback record' } : entry; return `<div class="similar-card"><strong>${escapeHtml(data.score)}</strong><span>${escapeHtml(data.name)}<small>${escapeHtml(data.reason)}</small></span></div>`; }).join('')}</div>`;
  }
}

async function selectCase(key) {
  selectedCaseKey = key;
  selectedParagraphIndex = 0;
  try { await loadSelectedCaseFromApi(key); } catch (error) { console.warn('Using local case fallback.', error); }
  renderCases(document.getElementById('legal-search').value);
  renderDashboard();
  renderResearchPanel();
}

function initializeEvents() {
  document.addEventListener('click', event => {
    const module = event.target.closest('[data-module]'); if (module) { document.querySelectorAll('.nav-item').forEach(btn => btn.classList.toggle('active', btn === module)); document.querySelectorAll('.module-view').forEach(view => view.classList.toggle('active', view.id === `module-${module.dataset.module}`)); }
    const caseButton = event.target.closest('[data-case]'); if (caseButton) selectCase(caseButton.dataset.case);
    const topicButton = event.target.closest('[data-topic]'); if (topicButton) { document.querySelectorAll('.topic-pill').forEach(btn => btn.classList.toggle('active', btn === topicButton)); loadCasesFromApi('', topicButton.dataset.topic).catch(error => { console.warn('Topic API search failed.', error); renderCases('', topicButton.dataset.topic); }); }
    const paragraph = event.target.closest('[data-paragraph]'); if (paragraph) { selectedParagraphIndex = Number(paragraph.dataset.paragraph); activeResearchTab = 'analysis'; document.querySelectorAll('.dash-tab').forEach(btn => btn.classList.toggle('active', btn.dataset.tab === activeResearchTab)); renderResearchPanel(); }
    const tab = event.target.closest('[data-tab]'); if (tab) { activeResearchTab = tab.dataset.tab; document.querySelectorAll('.dash-tab').forEach(btn => btn.classList.toggle('active', btn === tab)); renderResearchPanel(); }
    const action = event.target.closest('[data-action]'); if (action) handleResearchAction(action.dataset.action);
  });
  document.getElementById('legal-search').addEventListener('input', event => { loadCasesFromApi(event.target.value).catch(error => { console.warn('Search API failed.', error); renderCases(event.target.value); }); });
  document.getElementById('browse-file').addEventListener('click', () => document.getElementById('case-file-input').click());
  document.getElementById('case-file-input').addEventListener('change', async event => {
    const file = event.target.files[0]; const status = document.getElementById('file-name');
    if (!file) return;
    status.textContent = `Uploading ${file.name}…`;
    try { const form = new FormData(); form.append('file', file); const response = await fetch(`${API_BASE_URL}/api/documents/upload`, { method: 'POST', body: form }); if (!response.ok) throw new Error(`Upload failed (${response.status})`); const result = await response.json(); status.textContent = `${file.name} processed.`; renderAnalyzerResult(result.analysis, result.paragraphs); } catch (error) { status.textContent = 'Upload failed. Ensure the local API is running and upload a text-based PDF.'; }
  });
  document.getElementById('generate-draft').addEventListener('click', generateDraft);
  document.getElementById('chat-form').addEventListener('submit', async event => { event.preventDefault(); const input = document.getElementById('chat-user-input'); const question = input.value.trim(); if (!question) return; const messages = document.getElementById('chat-messages'); messages.insertAdjacentHTML('beforeend', `<div class="user-chat-bubble">${escapeHtml(question)}</div>`); input.value = ''; try { const result = await postApi('/api/research/answer', { question, case_slug: selectedCaseKey }); const sources = result.sources.map(source => `<div class="chat-source"><strong>${escapeHtml(source.name)}</strong> — ${escapeHtml(source.citation)}${source.excerpt ? `<br><span>${escapeHtml(source.excerpt)}</span>` : ''}</div>`).join(''); messages.insertAdjacentHTML('beforeend', `<div class="ai-chat-bubble"><div class="bubble-avatar"><i class="fa-solid fa-robot"></i></div><div class="bubble-content">${escapeHtml(result.answer)}${sources ? `<br><br><strong>Sources</strong>${sources}` : ''}<br><br><em>${escapeHtml(result.notice)}</em></div></div>`); } catch (error) { messages.insertAdjacentHTML('beforeend', '<div class="ai-chat-bubble"><div class="bubble-avatar"><i class="fa-solid fa-robot"></i></div><div class="bubble-content">The local research service is unavailable. Start the backend and try again.</div></div>'); } messages.scrollTop = messages.scrollHeight; });
}

function draftText(type, facts) {
  const templates = {
    writ: `IN THE SUPREME COURT OF INDIA\nCIVIL ORIGINAL JURISDICTION\n\nWRIT PETITION (CIVIL) UNDER ARTICLE 32 OF THE CONSTITUTION OF INDIA\n\nIN THE MATTER OF:\n${facts}\n\nTO,\nTHE HON'BLE CHIEF JUSTICE OF INDIA AND HIS COMPANION JUSTICES OF THE SUPREME COURT OF INDIA\n\nMOST RESPECTFULLY SHOWETH:\n\n1. The Petitioner is aggrieved by the action/inaction described above, which is alleged to affect the Petitioner's fundamental rights.\n\n2. The cause of action arose on [DATE] at [PLACE]. This Hon'ble Court has jurisdiction under Article 32 of the Constitution of India.\n\nGROUNDS\nA. Because the impugned action is arbitrary, unreasonable and violative of the fundamental rights pleaded herein.\nB. Because no adequate or efficacious remedy is available to protect the Petitioner's constitutional rights.\n\nPRAYER\nIt is therefore prayed that this Hon'ble Court may be pleased to issue an appropriate writ, order or direction; grant interim protection as warranted; and pass such further orders as justice requires.\n\nPLACE: [PLACE]\nDATE: [DATE]\n\nPETITIONER / AUTHORISED ADVOCATE`,
    nda: `MUTUAL NON-DISCLOSURE AGREEMENT\n\nThis Mutual Non-Disclosure Agreement ("Agreement") is made on [DATE] between:\n\n1. [PARTY A], having its address at [ADDRESS]; and\n2. [PARTY B], having its address at [ADDRESS].\n\nBACKGROUND\n${facts}\n\n1. CONFIDENTIAL INFORMATION\n"Confidential Information" means all non-public business, technical, financial, legal, commercial and other information disclosed by either party, whether written, oral, visual or electronic.\n\n2. PERMITTED USE\nThe receiving party shall use Confidential Information solely to evaluate or pursue the stated purpose and shall disclose it only to personnel who need to know it and are bound by equivalent confidentiality obligations.\n\n3. EXCLUSIONS\nConfidential Information does not include information that is publicly available without breach, already lawfully known, independently developed, or required to be disclosed by law (subject to prior notice where lawful).\n\n4. TERM AND RETURN\nThis Agreement begins on the date above. Confidentiality obligations continue for [TERM]. On request, the receiving party shall return or securely destroy Confidential Information, subject to lawful retention requirements.\n\n5. GOVERNING LAW\nThis Agreement is governed by the laws of India. Courts at [CITY] shall have jurisdiction.\n\nSIGNED by authorised representatives of the parties.`,
    defamation: `LEGAL NOTICE FOR DEFAMATION\n\nDate: [DATE]\n\nTo,\n[RECIPIENT NAME AND ADDRESS]\n\nSubject: Notice requiring cessation, retraction and apology for defamatory statements\n\nUnder instructions from and on behalf of my client:\n${facts}\n\n1. You have made and/or published statements concerning my client on or about [DATE] through [MEDIUM].\n\n2. The statements are false, disparaging and have caused, or are likely to cause, serious harm to my client's reputation.\n\n3. You are called upon to, within [7/15] days of receipt of this notice:\n(a) cease further publication or repetition of the statements;\n(b) remove the statements from all platforms within your control;\n(c) issue an unconditional written retraction and apology; and\n(d) preserve all relevant records and communications.\n\nFailing compliance, my client reserves all rights to initiate appropriate civil and criminal proceedings at your risk as to costs and consequences.\n\nYours faithfully,\n[ADVOCATE / AUTHORISED REPRESENTATIVE]`
  };
  return templates[type];
}

function generateDraft() { const type = document.getElementById('draft-type-select').value; const facts = document.getElementById('draft-variables').value.trim() || '[Enter party details, material facts and jurisdiction]'; const text = draftText(type, facts); const title = { writ: 'WRIT PETITION UNDER ARTICLE 32', nda: 'MUTUAL NON-DISCLOSURE AGREEMENT', defamation: 'LEGAL NOTICE FOR DEFAMATION' }[type]; document.getElementById('draft-output-container').innerHTML = `<div class="legal-title-center">${title}</div><div id="generated-draft" class="legal-document-text">${escapeHtml(text)}</div><div class="draft-actions"><button id="copy-draft">Copy draft</button><button id="download-draft">Download .txt</button></div><p class="draft-notice">This is a general baseline. It must be reviewed, completed and adapted by a qualified legal professional before use.</p>`; document.getElementById('copy-draft').addEventListener('click', () => navigator.clipboard?.writeText(text).then(() => { document.getElementById('copy-draft').textContent = 'Copied'; }).catch(() => {})); document.getElementById('download-draft').addEventListener('click', () => { const link = document.createElement('a'); link.href = URL.createObjectURL(new Blob([text], { type: 'text/plain' })); link.download = `${type}-draft.txt`; link.click(); URL.revokeObjectURL(link.href); }); }

document.addEventListener('DOMContentLoaded', async () => {
  renderTopics(); renderCases(); renderDashboard(); renderResearchPanel(); initializeEvents();
  try {
    allTopics = await requestApi('/api/topics');
    renderTopics();
    await loadCasesFromApi();
    await selectCase(selectedCaseKey);
  } catch (error) {
    console.warn('Legal API unavailable; using local prototype data.', error);
  }
});
