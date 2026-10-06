/**
 * PDF Ink — Frontend Script
 * Gemini 2.0 Flash RAG · Zero Hallucinations · Professional UI
 */

/* ─── Toast Notifications ─────────────────────────────────── */
class Toast {
    static create(message, type = 'info', duration = 3800) {
        const container = document.getElementById('toast-container');
        if (!container) return;

        const icons = { success: 'ri-checkbox-circle-fill', error: 'ri-error-warning-fill', info: 'ri-information-fill', warning: 'ri-alert-fill' };

        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.innerHTML = `<i class="${icons[type] || icons.info}"></i><span>${message}</span>`;
        container.appendChild(toast);

        requestAnimationFrame(() => toast.classList.add('show'));

        if (duration > 0) {
            setTimeout(() => {
                toast.classList.remove('show');
                toast.classList.add('hide');
                setTimeout(() => toast.remove(), 350);
            }, duration);
        }
        return toast;
    }
}

/* ─── API Manager ─────────────────────────────────────────── */
class PDFExtractorAPI {
    static async checkLLMHealth() {
        try {
            const res = await fetch('/api/llm/health');
            return await res.json();
        } catch (e) {
            return { status: 'error', message: e.message };
        }
    }

    static async getConfig() {
        try {
            const res = await fetch('/api/config');
            return await res.json();
        } catch (e) {
            return { has_gemini_key: false, gemini_model: 'gemini-3.8-flash' };
        }
    }

    static async updateConfig(apiKey, model) {
        try {
            const res = await fetch('/api/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ gemini_api_key: apiKey, gemini_model: model })
            });
            return await res.json();
        } catch (e) {
            return { success: false, error: e.message };
        }
    }

    static async extractText(file, onProgress) {
        const formData = new FormData();
        formData.append('file', file);

        return new Promise((resolve, reject) => {
            const xhr = new XMLHttpRequest();
            xhr.open('POST', '/api/extract');
            xhr.upload.onprogress = (e) => {
                if (e.lengthComputable && onProgress) onProgress(Math.round((e.loaded / e.total) * 100));
            };
            xhr.onload = () => {
                if (xhr.status >= 200 && xhr.status < 300) {
                    try { resolve(JSON.parse(xhr.responseText)); }
                    catch { reject(new Error('Invalid server response')); }
                } else {
                    try {
                        const err = JSON.parse(xhr.responseText);
                        reject(new Error(err.detail || `Server error (${xhr.status})`));
                    } catch { reject(new Error(`Server error (${xhr.status})`)); }
                }
            };
            xhr.onerror = () => reject(new Error('Network error during upload'));
            xhr.send(formData);
        });
    }

    static async summarize(pdfText, model) {
        const response = await fetch('/api/summarize', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ pdf_text: pdfText, model: model || 'gemini-3.8-flash' })
        });
        if (!response.ok) {
            const errData = await response.json().catch(() => ({ detail: 'Summarization failed' }));
            throw new Error(errData.detail || 'Summarization failed');
        }
        return await response.json();
    }

    static async askQuestion(pdfText, question, chatHistory = [], model) {
        const response = await fetch('/api/ask', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                pdf_text: pdfText,
                question: question,
                chat_history: chatHistory,
                model: model || 'gemini-3.8-flash'
            })
        });
        if (!response.ok) {
            const errData = await response.json().catch(() => ({ detail: 'Failed to answer question' }));
            throw new Error(errData.detail || 'Failed to answer question');
        }
        return await response.json();
    }
}

/* ─── App Controller ──────────────────────────────────────── */
class App {
    constructor() {
        this.extractedText = '';
        this.pageCount = 0;
        this.currentFilename = '';
        this.chatHistory = [];
        this.currentModel = 'gemini-3.8-flash';
        this.hasGeminiKey = false;
        this.isSending = false;

        this.initDOMElements();
        this.bindEvents();
        this.loadInitialConfig();
    }

    initDOMElements() {
        this.uploadSection    = document.getElementById('upload-section');
        this.loadingSection   = document.getElementById('loading-section');
        this.errorSection     = document.getElementById('error-section');
        this.resultSection    = document.getElementById('result-section');

        this.dropZone         = document.getElementById('drop-zone');
        this.fileInput        = document.getElementById('file-input');
        this.browseBtn        = document.getElementById('browse-btn');
        this.uploadProgressBar= document.getElementById('upload-progress-bar');
        this.uploadProgressWrap=document.getElementById('upload-progress-wrap');

        this.modelStatusBtn   = document.getElementById('model-status-btn');
        this.statusDot        = document.getElementById('status-dot');
        this.statusText       = document.getElementById('status-text');
        this.settingsToggleBtn= document.getElementById('settings-toggle-btn');
        this.settingsModal    = document.getElementById('settings-modal');
        this.modalCloseBtn    = document.getElementById('modal-close-btn');
        this.geminiKeyInput   = document.getElementById('gemini-key-input');
        this.geminiModelSelect= document.getElementById('gemini-model-select');
        this.saveSettingsBtn  = document.getElementById('save-settings-btn');
        this.toggleKeyVisBtn  = document.getElementById('toggle-key-visibility');
        this.settingsStatusBox= document.getElementById('settings-status-box');
        this.settingsStatusText= document.getElementById('settings-status-text');

        this.resultFilename   = document.getElementById('result-filename');
        this.resultPages      = document.getElementById('result-pages');
        this.resultChars      = document.getElementById('result-chars');
        this.outputText       = document.getElementById('output-text');
        this.copyBtn          = document.getElementById('copy-btn');
        this.downloadBtn      = document.getElementById('download-btn');
        this.clearBtn         = document.getElementById('clear-btn');
        this.errorMsg         = document.getElementById('error-message');
        this.errorCloseBtn    = document.getElementById('error-close-btn');

        this.genSummaryBtn    = document.getElementById('gen-summary-btn');
        this.summaryContent   = document.getElementById('summary-content');
        this.summaryText      = document.getElementById('summary-text');
        this.summaryLoading   = document.getElementById('summary-loading');

        this.chatMessages     = document.getElementById('chat-messages');
        this.chatInput        = document.getElementById('chat-input');
        this.chatSendBtn      = document.getElementById('chat-send-btn');
        this.chatClearBtn     = document.getElementById('chat-clear-btn');
        this.suggestionChips  = document.getElementById('suggestion-chips');
        this.charCounter      = document.getElementById('char-counter');
    }

    bindEvents() {
        /* ── Dropzone ── */
        this.dropZone.addEventListener('click', (e) => {
            if (e.target === this.browseBtn || e.target.closest('#browse-btn')) return;
            this.fileInput.click();
        });
        this.browseBtn?.addEventListener('click', (e) => { e.stopPropagation(); this.fileInput.click(); });
        this.fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) this.handleFile(e.target.files[0]);
        });

        ['dragenter', 'dragover'].forEach(ev => this.dropZone.addEventListener(ev, (e) => {
            e.preventDefault(); e.stopPropagation();
            this.dropZone.classList.add('dragover');
        }));
        ['dragleave', 'drop'].forEach(ev => this.dropZone.addEventListener(ev, (e) => {
            e.preventDefault(); e.stopPropagation();
            this.dropZone.classList.remove('dragover');
        }));
        this.dropZone.addEventListener('drop', (e) => {
            const dt = e.dataTransfer;
            if (dt.files && dt.files.length > 0) this.handleFile(dt.files[0]);
        });

        /* ── Settings Modal ── */
        const openModal  = () => { this.settingsModal.classList.remove('hidden'); this.settingsModal.classList.add('open'); };
        const closeModal = () => { this.settingsModal.classList.add('hidden'); this.settingsModal.classList.remove('open'); };

        this.modelStatusBtn.addEventListener('click', openModal);
        this.settingsToggleBtn.addEventListener('click', openModal);
        this.modalCloseBtn.addEventListener('click', closeModal);
        this.settingsModal.addEventListener('click', (e) => { if (e.target === this.settingsModal) closeModal(); });

        this.toggleKeyVisBtn?.addEventListener('click', () => {
            const isPwd = this.geminiKeyInput.type === 'password';
            this.geminiKeyInput.type = isPwd ? 'text' : 'password';
            this.toggleKeyVisBtn.innerHTML = isPwd ? '<i class="ri-eye-off-line"></i>' : '<i class="ri-eye-line"></i>';
        });

        this.saveSettingsBtn.addEventListener('click', async () => {
            const key   = this.geminiKeyInput.value.trim();
            const model = this.geminiModelSelect.value;
            this.saveSettingsBtn.disabled = true;
            this.saveSettingsBtn.innerHTML = '<i class="ri-loader-4-line spin"></i> Saving…';

            const res = await PDFExtractorAPI.updateConfig(key, model);
            this.saveSettingsBtn.disabled = false;
            this.saveSettingsBtn.innerHTML = '<i class="ri-check-line"></i> Save Settings';

            if (res.success) {
                Toast.create('Settings saved successfully', 'success');
                this.currentModel = model;
                closeModal();
                this.loadInitialConfig();
            } else {
                Toast.create('Failed to update configuration', 'error');
            }
        });

        /* ── Document Actions ── */
        this.copyBtn.addEventListener('click', () => {
            if (!this.extractedText) return;
            navigator.clipboard.writeText(this.extractedText);
            Toast.create('Text copied to clipboard', 'success');
        });

        this.downloadBtn.addEventListener('click', () => {
            if (!this.extractedText) return;
            const blob = new Blob([this.extractedText], { type: 'text/plain;charset=utf-8' });
            const url  = URL.createObjectURL(blob);
            const a    = document.createElement('a');
            a.href = url;
            a.download = (this.currentFilename.replace(/\.pdf$/i, '') || 'extracted_text') + '.txt';
            a.click();
            URL.revokeObjectURL(url);
            Toast.create('Downloaded .txt file', 'success');
        });

        this.clearBtn.addEventListener('click', () => this.resetWorkspace());
        this.errorCloseBtn.addEventListener('click', () => this.resetWorkspace());

        /* ── Summary ── */
        this.genSummaryBtn.addEventListener('click', () => this.generateSummary());

        /* ── Chat ── */
        this.chatSendBtn.addEventListener('click', () => this.sendChatMessage());
        this.chatInput.addEventListener('keypress', (e) => { if (e.key === 'Enter' && !e.shiftKey) this.sendChatMessage(); });
        this.chatInput.addEventListener('input', () => {
            const len = this.chatInput.value.length;
            if (this.charCounter) {
                this.charCounter.textContent = `${len}/500`;
                this.charCounter.style.color = len > 450 ? '#f43f5e' : '';
            }
        });

        this.chatClearBtn.addEventListener('click', () => {
            this.chatHistory = [];
            this.chatMessages.innerHTML = this.welcomeCardHTML();
            Toast.create('Chat history cleared', 'info');
        });

        /* ── Chips ── */
        this.suggestionChips?.addEventListener('click', (e) => {
            const btn = e.target.closest('.chip-btn');
            if (btn && btn.dataset.query) {
                this.chatInput.value = btn.dataset.query;
                this.sendChatMessage();
            }
        });

        /* ── Close modal on Escape ── */
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') closeModal();
        });
    }

    /* ── Config / Health ──────────────────────────────────── */
    async loadInitialConfig() {
        const [config, llmHealth] = await Promise.all([
            PDFExtractorAPI.getConfig(),
            PDFExtractorAPI.checkLLMHealth()
        ]);

        this.hasGeminiKey = config.has_gemini_key;
        this.currentModel = config.gemini_model || 'gemini-3.8-flash';
        if (this.geminiModelSelect) {
            // Set the matching option, fall back to first
            const opt = this.geminiModelSelect.querySelector(`option[value="${this.currentModel}"]`);
            if (opt) this.geminiModelSelect.value = this.currentModel;
        }

        const isHealthy = llmHealth.status === 'healthy';
        if (isHealthy) {
            const active = llmHealth.active_provider || 'gemini';
            this.setStatus('online', `Gemini 2.0 Flash · Ready`);
            this.setSettingsStatus('ok', `✅ AI Engine Online — ${this.currentModel}`);
        } else if (!this.hasGeminiKey) {
            this.setStatus('warning', 'Configure API Key');
            this.setSettingsStatus('warn', '⚠️ No Gemini API Key found. Add your key below.');
        } else {
            this.setStatus('offline', 'Service Unavailable');
            this.setSettingsStatus('error', '❌ Health check failed. Verify your API Key is correct.');
        }
    }

    setStatus(state, text) {
        this.statusDot.className = `status-indicator ${state}`;
        this.statusText.textContent = text;
    }

    setSettingsStatus(state, html) {
        const colors = { ok: 'rgba(16, 185, 129, 0.12)', warn: 'rgba(245, 158, 11, 0.12)', error: 'rgba(244, 63, 94, 0.12)' };
        this.settingsStatusBox.style.background = colors[state] || colors.warn;
        this.settingsStatusText.innerHTML = html;
    }

    /* ── File Handling ────────────────────────────────────── */
    async handleFile(file) {
        if (!file || !file.name.toLowerCase().endsWith('.pdf')) {
            Toast.create('Please select a valid PDF file.', 'error'); return;
        }
        if (file.size > 200 * 1024 * 1024) {
            Toast.create('File exceeds 200 MB limit.', 'error'); return;
        }

        this.showLoading('Uploading & extracting document…');
        this.currentFilename = file.name;

        try {
            const res = await PDFExtractorAPI.extractText(file, (pct) => {
                if (this.uploadProgressBar) {
                    this.uploadProgressBar.style.width = pct + '%';
                    document.getElementById('loading-status').textContent =
                        pct < 100 ? `Uploading… ${pct}%` : 'Processing document, please wait…';
                }
            });

            this.extractedText = res.text || '';
            this.pageCount = res.page_count || 1;
            this.showResultSection(res);
            Toast.create(`✅ Processed ${res.page_count} page(s) — ready to ask questions`, 'success');
        } catch (err) {
            this.showError(err.message || 'Failed to extract text from PDF.');
        }
    }

    /* ── View Transitions ────────────────────────────────── */
    showLoading(status) {
        document.getElementById('loading-status').textContent = status;
        if (this.uploadProgressBar) this.uploadProgressBar.style.width = '0%';
        this._setView('loading');
    }

    showError(msg) {
        this.errorMsg.textContent = msg;
        this._setView('error');
    }

    showResultSection(data) {
        this.resultFilename.textContent = data.filename || this.currentFilename;
        this.resultPages.innerHTML = `<i class="ri-pages-line"></i> ${data.page_count} page(s)`;
        this.resultChars.innerHTML = `<i class="ri-text"></i> ${(data.character_count || 0).toLocaleString()} chars`;
        this.outputText.value = data.text;
        this._setView('result');
    }

    _setView(view) {
        const sections = { upload: this.uploadSection, loading: this.loadingSection, error: this.errorSection, result: this.resultSection };
        Object.entries(sections).forEach(([k, el]) => {
            if (!el) return;
            if (k === view) { el.classList.remove('hidden'); el.classList.add('visible'); }
            else { el.classList.add('hidden'); el.classList.remove('visible'); }
        });
    }

    resetWorkspace() {
        this.extractedText = '';
        this.currentFilename = '';
        this.chatHistory = [];
        this.fileInput.value = '';
        this.summaryContent.classList.add('hidden');
        this.summaryText.innerHTML = '';
        this.chatMessages.innerHTML = this.welcomeCardHTML();
        this._setView('upload');
    }

    /* ── Summary ─────────────────────────────────────────── */
    async generateSummary() {
        if (!this.extractedText) return;
        this.summaryContent.classList.add('hidden');
        this.summaryLoading.classList.remove('hidden');
        this.genSummaryBtn.disabled = true;
        this.genSummaryBtn.innerHTML = '<i class="ri-loader-4-line spin"></i> Generating…';

        try {
            const res = await PDFExtractorAPI.summarize(this.extractedText, this.currentModel);
            this.summaryLoading.classList.add('hidden');
            this.summaryText.innerHTML = this.renderMarkdown(res.summary || 'No summary generated.');
            this.summaryContent.classList.remove('hidden');
            Toast.create('AI summary generated', 'success');
        } catch (e) {
            this.summaryLoading.classList.add('hidden');
            Toast.create(e.message || 'Failed to generate summary', 'error');
        } finally {
            this.genSummaryBtn.disabled = false;
            this.genSummaryBtn.innerHTML = '<i class="ri-flashlight-line"></i> Summarize';
        }
    }

    /* ── Chat ────────────────────────────────────────────── */
    async sendChatMessage() {
        const question = this.chatInput.value.trim();
        if (!question || !this.extractedText || this.isSending) return;

        this.isSending = true;
        document.getElementById('chat-welcome')?.remove();

        this.appendUserMsg(question);
        this.chatHistory.push({ role: 'user', content: question });
        this.chatInput.value = '';
        if (this.charCounter) this.charCounter.textContent = '0/500';

        const typingEl = this.appendTypingIndicator();
        this.chatSendBtn.disabled = true;
        this.chatSendBtn.innerHTML = '<i class="ri-loader-4-line spin"></i>';

        try {
            const res = await PDFExtractorAPI.askQuestion(
                this.extractedText, question, this.chatHistory, this.currentModel
            );
            typingEl.remove();
            const answer = res.answer || 'No answer generated.';
            const modelUsed = res.model_used || this.currentModel;
            this.appendAssistantMsg(answer, modelUsed, res.chunks_used);
            this.chatHistory.push({ role: 'assistant', content: answer });
        } catch (e) {
            typingEl.remove();
            this.appendAssistantMsg(`⚠️ ${e.message || 'Could not answer question.'}`, null, 0);
        } finally {
            this.isSending = false;
            this.chatSendBtn.disabled = false;
            this.chatSendBtn.innerHTML = '<i class="ri-send-plane-fill"></i>';
            this.scrollToBottom();
        }
    }

    appendUserMsg(text) {
        const el = document.createElement('div');
        el.className = 'chat-msg user';
        el.innerHTML = `
            <div class="chat-bubble user-bubble">${this.escapeHTML(text)}</div>
            <div class="chat-meta"><span><i class="ri-time-line"></i> ${this.now()}</span></div>`;
        this.chatMessages.appendChild(el);
        this.scrollToBottom();
    }

    appendAssistantMsg(content, modelUsed, chunksUsed) {
        const el = document.createElement('div');
        el.className = 'chat-msg assistant';

        const rendered = this.renderMarkdown(content);
        const modelBadge = modelUsed ? `<span class="model-badge"><i class="ri-sparkles-line"></i> ${modelUsed}</span>` : '';
        const chunkBadge = chunksUsed != null ? `<span class="chunk-badge"><i class="ri-file-search-line"></i> ${chunksUsed} chunk(s) searched</span>` : '';

        el.innerHTML = `
            <div class="assistant-avatar"><i class="ri-brain-line"></i></div>
            <div class="assistant-content">
                <div class="chat-bubble assistant-bubble">${rendered}</div>
                <div class="chat-meta">${modelBadge}${chunkBadge}<span><i class="ri-time-line"></i> ${this.now()}</span></div>
            </div>`;
        this.chatMessages.appendChild(el);
        this.scrollToBottom();
    }

    appendTypingIndicator() {
        const el = document.createElement('div');
        el.className = 'chat-msg assistant typing-wrapper';
        el.id = 'chat-typing-indicator';
        el.innerHTML = `
            <div class="assistant-avatar"><i class="ri-brain-line"></i></div>
            <div class="chat-typing"><span></span><span></span><span></span></div>`;
        this.chatMessages.appendChild(el);
        this.scrollToBottom();
        return el;
    }

    scrollToBottom() {
        requestAnimationFrame(() => {
            this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
        });
    }

    welcomeCardHTML() {
        return `<div class="chat-welcome-card" id="chat-welcome">
            <div class="welcome-icon"><i class="ri-chat-smile-2-line"></i></div>
            <h4>Ask Anything About Your PDF</h4>
            <p>Powered by Gemini RAG — answers are grounded 100% in document content.</p>
        </div>`;
    }

    /* ── Helpers ─────────────────────────────────────────── */
    renderMarkdown(text) {
        if (window.marked && typeof marked.parse === 'function') {
            return marked.parse(text, { breaks: true, gfm: true });
        }
        return this.escapeHTML(text).replace(/\n/g, '<br>');
    }

    escapeHTML(str) {
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    now() {
        return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }
}

/* ─── Boot ────────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
    window.pdfApp = new App();
});
