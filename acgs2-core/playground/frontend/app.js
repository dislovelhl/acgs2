/**
 * ACGS-2 Policy Playground - Frontend Application
 *
 * Provides interactive policy testing with OPA backend integration.
 * Handles policy validation, evaluation, and example loading.
 */

(function () {
    'use strict';

    // Configuration
    const API_BASE = window.location.origin;
    const ENDPOINTS = {
        validate: `${API_BASE}/api/validate`,
        evaluate: `${API_BASE}/api/evaluate`,
        examples: `${API_BASE}/api/examples`,
        health: `${API_BASE}/health`
    };

    // DOM Elements
    const elements = {
        // Editors
        policyEditor: document.getElementById('policyEditor'),
        inputEditor: document.getElementById('inputEditor'),

        // Buttons
        validateBtn: document.getElementById('validateBtn'),
        evaluateBtn: document.getElementById('evaluateBtn'),
        formatPolicyBtn: document.getElementById('formatPolicyBtn'),
        formatInputBtn: document.getElementById('formatInputBtn'),
        clearPolicyBtn: document.getElementById('clearPolicyBtn'),
        clearInputBtn: document.getElementById('clearInputBtn'),
        helpBtn: document.getElementById('helpBtn'),

        // Dropdowns
        exampleSelect: document.getElementById('exampleSelect'),

        // Results
        resultsContainer: document.getElementById('resultsContainer'),
        explanationContainer: document.getElementById('explanationContainer'),
        resultStatus: document.getElementById('resultStatus'),
        statusMessage: document.getElementById('statusMessage'),

        // Connection status
        connectionDot: document.getElementById('connectionDot'),
        connectionText: document.getElementById('connectionText'),

        // Help modal
        helpModalOverlay: document.getElementById('helpModalOverlay'),
        helpModalClose: document.getElementById('helpModalClose')
    };

    // State
    let isLoading = false;
    let examples = [];
    let currentExample = null;

    /**
     * Initialize the application
     */
    async function init() {
        setupEventListeners();
        await checkConnection();
        await loadExamples();
        updateStatus('Ready');
    }

    /**
     * Setup event listeners
     */
    function setupEventListeners() {
        // Button clicks
        elements.validateBtn.addEventListener('click', handleValidate);
        elements.evaluateBtn.addEventListener('click', handleEvaluate);
        elements.formatPolicyBtn?.addEventListener('click', handleFormatPolicy);
        elements.formatInputBtn?.addEventListener('click', handleFormatInput);
        elements.clearPolicyBtn?.addEventListener('click', () => {
            elements.policyEditor.value = '';
            updateStatus('Policy cleared');
        });
        elements.clearInputBtn?.addEventListener('click', () => {
            elements.inputEditor.value = '';
            updateStatus('Input cleared');
        });

        // Help modal
        elements.helpBtn.addEventListener('click', toggleHelpModal);
        elements.helpModalClose.addEventListener('click', hideHelpModal);
        elements.helpModalOverlay.addEventListener('click', (e) => {
            if (e.target === elements.helpModalOverlay) {
                hideHelpModal();
            }
        });

        // Example selection
        elements.exampleSelect.addEventListener('change', handleExampleSelect);

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            // ? to toggle help modal
            if (e.key === '?' && !e.ctrlKey && !e.metaKey && !e.shiftKey && !e.altKey) {
                e.preventDefault();
                toggleHelpModal();
                return;
            }

            // Escape to close help modal (if open) or clear focused editor
            if (e.key === 'Escape') {
                if (elements.helpModalOverlay.classList.contains('active')) {
                    e.preventDefault();
                    hideHelpModal();
                    return;
                }

                const activeElement = document.activeElement;

                if (activeElement === elements.policyEditor) {
                    e.preventDefault();
                    elements.policyEditor.value = '';
                    elements.resultsContainer.innerHTML = '';
                    elements.explanationContainer.innerHTML = '';
                    elements.resultStatus.innerHTML = '';
                    updateStatus('Policy cleared');
                } else if (activeElement === elements.inputEditor) {
                    e.preventDefault();
                    elements.inputEditor.value = '';
                    elements.resultsContainer.innerHTML = '';
                    elements.explanationContainer.innerHTML = '';
                    elements.resultStatus.innerHTML = '';
                    updateStatus('Input cleared');
                }
                return;
            }

            // Don't process other shortcuts if help modal is open
            if (elements.helpModalOverlay.classList.contains('active')) {
                return;
            }

            // Ctrl/Cmd + Enter to evaluate
            if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                e.preventDefault();
                handleEvaluate();
            }
            // Ctrl/Cmd + Shift + V to validate
            if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'V') {
                e.preventDefault();
                handleValidate();
            }
            // R to refresh connection and reload examples
            if (e.key === 'r' || e.key === 'R') {
                e.preventDefault();
                updateStatus('Refreshing...');
                checkConnection().then(() => loadExamples());
            }
        });

        // Tab support in editors
        [elements.policyEditor, elements.inputEditor].forEach(editor => {
            editor.addEventListener('keydown', (e) => {
                if (e.key === 'Tab') {
                    e.preventDefault();
                    const start = editor.selectionStart;
                    const end = editor.selectionEnd;
                    editor.value = editor.value.substring(0, start) + '  ' + editor.value.substring(end);
                    editor.selectionStart = editor.selectionEnd = start + 2;
                }
            });
        });
    }

    /**
     * Check connection to the backend
     */
    async function checkConnection() {
        setConnectionStatus('checking', 'Checking OPA...');

        try {
            const response = await fetch(ENDPOINTS.health);
            const data = await response.json();

            if (data.status === 'ready' || data.status === 'alive') {
                setConnectionStatus('connected', 'OPA Connected');
            } else if (data.status === 'degraded') {
                setConnectionStatus('disconnected', 'OPA Degraded');
            } else {
                setConnectionStatus('disconnected', 'OPA Not Ready');
            }
        } catch (error) {
            setConnectionStatus('disconnected', 'Backend Offline');
        }
    }

    /**
     * Set connection status indicator
     */
    function setConnectionStatus(status, text) {
        elements.connectionDot.className = 'connection-dot ' + status;
        elements.connectionText.textContent = text;
    }

    /**
     * Load example policies from the backend
     */
    async function loadExamples() {
        try {
            const response = await fetch(ENDPOINTS.examples);

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            examples = await response.json();

            // Populate example dropdown
            elements.exampleSelect.innerHTML = '<option value="">Load Example...</option>';

            // Group by category
            const categories = {};
            examples.forEach(example => {
                if (!categories[example.category]) {
                    categories[example.category] = [];
                }
                categories[example.category].push(example);
            });

            // Add optgroups for each category
            Object.keys(categories).sort().forEach(category => {
                const optgroup = document.createElement('optgroup');
                optgroup.label = category;

                categories[category].forEach(example => {
                    const option = document.createElement('option');
                    option.value = example.id;
                    option.textContent = `${example.name} (${example.difficulty})`;
                    optgroup.appendChild(option);
                });

                elements.exampleSelect.appendChild(optgroup);
            });

            updateStatus(`Loaded ${examples.length} examples`);
        } catch (error) {
            updateStatus('Failed to load examples');
        }
    }

    /**
     * Handle example selection
     */
    function handleExampleSelect(e) {
        const exampleId = e.target.value;

        if (!exampleId) {
            currentExample = null;
            return;
        }

        currentExample = examples.find(ex => ex.id === exampleId);

        if (currentExample) {
            // Load policy and input
            elements.policyEditor.value = currentExample.policy;
            elements.inputEditor.value = JSON.stringify(currentExample.test_input, null, 2);

            // Show explanation
            showExplanation(currentExample);

            updateStatus(`Loaded: ${currentExample.name}`);
        }
    }

    /**
     * Show example explanation
     */
    function showExplanation(example) {
        elements.explanationContainer.innerHTML = `
            <div class="explanation-box">
                <div class="explanation-title">${escapeHtml(example.name)}</div>
                <p>${escapeHtml(example.explanation)}</p>
            </div>
            <div style="margin-top: 16px;">
                <strong style="color: var(--accent-green);">Expected Result:</strong>
                <pre class="language-json"><code>${escapeHtml(JSON.stringify(example.expected_result, null, 2))}</code></pre>
            </div>
        `;
    }

    /**
     * Handle validate button click
     */
    async function handleValidate() {
        if (isLoading) return;

        const policy = elements.policyEditor.value.trim();

        if (!policy) {
            showError('Please enter a Rego policy to validate');
            return;
        }

        setLoading(true);
        updateStatus('Validating policy...');

        try {
            const response = await fetch(ENDPOINTS.validate, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ policy })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || `HTTP ${response.status}`);
            }

            if (data.valid) {
                showValidationSuccess(data);
                updateStatus('Policy is valid');
            } else {
                showValidationErrors(data);
                updateStatus('Policy has errors');
            }
        } catch (error) {
            showError(`Validation failed: ${error.message}`);
            updateStatus('Validation failed');
        } finally {
            setLoading(false);
        }
    }

    /**
     * Handle evaluate button click
     */
    async function handleEvaluate() {
        if (isLoading) return;

        const policy = elements.policyEditor.value.trim();
        const inputText = elements.inputEditor.value.trim();

        if (!policy) {
            showError('Please enter a Rego policy to evaluate');
            return;
        }

        // Parse input JSON
        let inputData = {};
        if (inputText) {
            try {
                inputData = JSON.parse(inputText);
            } catch (e) {
                showError(`Invalid JSON input: ${e.message}`);
                return;
            }
        }

        setLoading(true);
        updateStatus('Evaluating policy...');

        try {
            const response = await fetch(ENDPOINTS.evaluate, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    policy,
                    input: inputData
                })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || `HTTP ${response.status}`);
            }

            if (data.success) {
                showEvaluationResult(data);
                updateStatus('Evaluation complete');
            } else {
                showError(data.error || 'Evaluation failed');
                updateStatus('Evaluation failed');
            }
        } catch (error) {
            showError(`Evaluation failed: ${error.message}`);
            updateStatus('Evaluation failed');
        } finally {
            setLoading(false);
        }
    }

    /**
     * Handle format policy button
     */
    function handleFormatPolicy() {
        // Basic formatting - normalize whitespace
        // Full formatting would require server-side `opa fmt`
        const policy = elements.policyEditor.value;

        // Remove trailing whitespace from lines
        const formatted = policy
            .split('\n')
            .map(line => line.trimEnd())
            .join('\n')
            .replace(/\n{3,}/g, '\n\n'); // Max 2 consecutive newlines

        elements.policyEditor.value = formatted;
        updateStatus('Policy formatted');
    }

    /**
     * Handle format input button
     */
    function handleFormatInput() {
        try {
            const input = elements.inputEditor.value.trim();
            if (!input) return;

            const parsed = JSON.parse(input);
            elements.inputEditor.value = JSON.stringify(parsed, null, 2);
            updateStatus('Input formatted');
        } catch (e) {
            showError(`Cannot format: ${e.message}`);
        }
    }

    /**
     * Show validation success
     */
    function showValidationSuccess(data) {
        let html = `
            <div class="result-success">
                <span class="status-badge status-valid">
                    &#10003; Valid
                </span>
                <p style="margin-top: 12px;">Policy syntax is valid.</p>
        `;

        if (data.warnings && data.warnings.length > 0) {
            html += `
                <div style="margin-top: 16px; color: var(--warning-color);">
                    <strong>Warnings:</strong>
                    <ul style="margin-top: 8px; padding-left: 20px;">
                        ${data.warnings.map(w => `<li>${escapeHtml(w)}</li>`).join('')}
                    </ul>
                </div>
            `;
        }

        html += '</div>';
        elements.resultsContainer.innerHTML = html;
        setResultStatus('valid', 'Valid');
    }

    /**
     * Show validation errors
     */
    function showValidationErrors(data) {
        let html = `
            <div class="result-error">
                <span class="status-badge status-invalid">
                    &#10007; Invalid
                </span>
                <div style="margin-top: 16px;">
                    <strong>Errors:</strong>
                    <ul style="margin-top: 8px; padding-left: 20px;">
                        ${data.errors.map(e => `<li class="error-line">${escapeHtml(e)}</li>`).join('')}
                    </ul>
                </div>
            </div>
        `;

        elements.resultsContainer.innerHTML = html;
        setResultStatus('invalid', 'Invalid');
    }

    /**
     * Show evaluation result
     */
    function showEvaluationResult(data) {
        const allowStatus = data.allowed;
        const statusClass = allowStatus === true ? 'result-success' :
            allowStatus === false ? 'result-error' : '';

        const statusBadge = allowStatus === true ?
            '<span class="status-badge status-valid">&#10003; Allowed</span>' :
            allowStatus === false ?
                '<span class="status-badge status-invalid">&#10007; Denied</span>' :
                '<span class="status-badge status-loading">Result</span>';

        let html = `
            <div class="${statusClass}">
                ${statusBadge}
                <div style="margin-top: 16px;">
                    <strong style="color: var(--text-secondary);">Full Result:</strong>
                    <pre class="language-json" style="margin-top: 8px; background: var(--bg-tertiary); padding: 12px; border-radius: 4px; overflow: auto;"><code>${escapeHtml(JSON.stringify(data.result, null, 2))}</code></pre>
                </div>
            </div>
        `;

        elements.resultsContainer.innerHTML = html;

        // Highlight JSON if Prism is available
        if (window.Prism) {
            Prism.highlightAllUnder(elements.resultsContainer);
        }

        setResultStatus(
            allowStatus === true ? 'valid' : allowStatus === false ? 'invalid' : 'loading',
            allowStatus === true ? 'Allowed' : allowStatus === false ? 'Denied' : 'Evaluated'
        );
    }

    /**
     * Show error message
     */
    function showError(message) {
        elements.resultsContainer.innerHTML = `
            <div class="error-message">
                <strong>Error:</strong> ${escapeHtml(message)}
            </div>
            <p style="color: var(--text-secondary); margin-top: 12px;">
                Make sure the OPA server is running and accessible.
            </p>
        `;
        setResultStatus('invalid', 'Error');
    }

    /**
     * Set result status badge
     */
    function setResultStatus(status, text) {
        const statusClass = status === 'valid' ? 'status-valid' :
            status === 'invalid' ? 'status-invalid' : 'status-loading';

        elements.resultStatus.innerHTML = `
            <span class="status-badge ${statusClass}">${text}</span>
        `;
    }

    /**
     * Set loading state
     */
    function setLoading(loading) {
        isLoading = loading;

        elements.validateBtn.disabled = loading;
        elements.evaluateBtn.disabled = loading;

        if (loading) {
            elements.evaluateBtn.innerHTML = '<span class="spinner"></span> Evaluating...';
        } else {
            elements.evaluateBtn.innerHTML = '<span>Evaluate</span>';
        }
    }

    /**
     * Update status message
     */
    function updateStatus(message) {
        elements.statusMessage.textContent = message;
    }

    /**
     * Escape HTML special characters
     */
    function escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Show help modal
     */
    function showHelpModal() {
        elements.helpModalOverlay.classList.add('active');
        updateStatus('Help modal opened');
    }

    /**
     * Hide help modal
     */
    function hideHelpModal() {
        elements.helpModalOverlay.classList.remove('active');
        updateStatus('Help modal closed');
    }

    /**
     * Toggle help modal
     */
    function toggleHelpModal() {
        if (elements.helpModalOverlay.classList.contains('active')) {
            hideHelpModal();
        } else {
            showHelpModal();
        }
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
