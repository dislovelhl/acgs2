/**
 * Prism.js Rego Language Definition
 *
 * Provides syntax highlighting for Open Policy Agent's Rego language.
 * Based on the Rego language specification: https://www.openpolicyagent.org/docs/latest/policy-reference/
 */

(function (Prism) {
    'use strict';

    Prism.languages.rego = {
        // Single-line comments
        'comment': {
            pattern: /#.*/,
            greedy: true
        },

        // Raw strings (backtick)
        'string': [
            {
                pattern: /`[^`]*`/,
                greedy: true
            },
            {
                pattern: /"(?:[^"\\]|\\.)*"/,
                greedy: true
            }
        ],

        // Numbers (integers and floats)
        'number': /\b(?:0x[\da-f]+|0o[0-7]+|0b[01]+|\d+(?:\.\d+)?(?:e[+-]?\d+)?)\b/i,

        // Boolean values
        'boolean': /\b(?:true|false)\b/,

        // Null value
        'null': /\bnull\b/,

        // Keywords
        'keyword': [
            // Package and import
            /\b(?:package|import|as)\b/,
            // Control flow
            /\b(?:if|else|not|with|default|some|every|in|contains)\b/
        ],

        // Built-in functions - operators
        'builtin': /\b(?:input|data|print|trace|time|http|opa|crypto|json|yaml|base64|urlquery|regex|glob|net|uuid|semver|graphql|rego|object|array)\b/,

        // Rule definitions and assignments
        'function': /\b[a-z_][a-zA-Z0-9_]*(?=\s*(?:\[|\(|=|{|\:=))/,

        // Operators
        'operator': [
            // Assignment operators
            /:=|==/,
            // Comparison operators
            /[<>]=?|!=|==/,
            // Logical operators
            /[&|]/,
            // Arithmetic operators
            /[+\-*/%]/,
            // Set/array operators
            /\|/
        ],

        // Punctuation
        'punctuation': /[{}[\](),.:;]/,

        // Variables (typically start with lowercase or underscore)
        'variable': /\b[a-z_][a-zA-Z0-9_]*\b/
    };

    // Alias for rego
    Prism.languages.opapolicy = Prism.languages.rego;

}(Prism));

/**
 * Custom Rego Syntax Highlighter (standalone, no Prism dependency)
 *
 * Provides lightweight syntax highlighting for Rego code.
 * Use when Prism.js is not available.
 */
const RegoSyntax = {
    // Token patterns for Rego language
    patterns: {
        comment: /#.*/g,
        string: /"(?:[^"\\]|\\.)*"|`[^`]*`/g,
        number: /\b(?:0x[\da-f]+|0o[0-7]+|0b[01]+|\d+(?:\.\d+)?(?:e[+-]?\d+)?)\b/gi,
        boolean: /\b(?:true|false)\b/g,
        null: /\bnull\b/g,
        keyword: /\b(?:package|import|as|if|else|not|with|default|some|every|in|contains)\b/g,
        builtin: /\b(?:input|data|print|trace|time|http|opa|crypto|json|yaml|base64|urlquery|regex|glob|net|uuid|semver|graphql|rego|object|array)\b/g,
        operator: /:=|==|!=|<=|>=|[<>+\-*/%&|]/g,
        punctuation: /[{}[\](),.:;]/g
    },

    // CSS classes for each token type
    cssClasses: {
        comment: 'token comment',
        string: 'token string',
        number: 'token number',
        boolean: 'token boolean',
        null: 'token null',
        keyword: 'token keyword',
        builtin: 'token builtin',
        operator: 'token operator',
        punctuation: 'token punctuation'
    },

    /**
     * Escape HTML characters
     * @param {string} text - Text to escape
     * @returns {string} Escaped text
     */
    escapeHtml(text) {
        const escapeMap = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return text.replace(/[&<>"']/g, char => escapeMap[char]);
    },

    /**
     * Highlight Rego code with syntax coloring
     * @param {string} code - Rego source code
     * @returns {string} HTML with syntax highlighting
     */
    highlight(code) {
        if (!code) return '';

        // Store tokens with their positions
        const tokens = [];
        const escapedCode = this.escapeHtml(code);

        // Find all tokens
        for (const [type, pattern] of Object.entries(this.patterns)) {
            // Reset regex lastIndex
            pattern.lastIndex = 0;
            let match;

            while ((match = pattern.exec(code)) !== null) {
                tokens.push({
                    type,
                    text: match[0],
                    start: match.index,
                    end: match.index + match[0].length
                });
            }
        }

        // Sort by position (later tokens first for replacement)
        tokens.sort((a, b) => b.start - a.start);

        // Remove overlapping tokens (keep earlier/larger tokens)
        const usedRanges = [];
        const filteredTokens = tokens.filter(token => {
            const overlaps = usedRanges.some(range =>
                (token.start >= range.start && token.start < range.end) ||
                (token.end > range.start && token.end <= range.end) ||
                (token.start <= range.start && token.end >= range.end)
            );
            if (!overlaps) {
                usedRanges.push({ start: token.start, end: token.end });
                return true;
            }
            return false;
        });

        // Sort for forward replacement
        filteredTokens.sort((a, b) => a.start - b.start);

        // Build highlighted HTML
        let result = '';
        let lastIndex = 0;

        for (const token of filteredTokens) {
            // Add unhighlighted text before this token
            if (token.start > lastIndex) {
                result += this.escapeHtml(code.substring(lastIndex, token.start));
            }

            // Add highlighted token
            const cssClass = this.cssClasses[token.type] || 'token';
            result += `<span class="${cssClass}">${this.escapeHtml(token.text)}</span>`;
            lastIndex = token.end;
        }

        // Add remaining unhighlighted text
        if (lastIndex < code.length) {
            result += this.escapeHtml(code.substring(lastIndex));
        }

        return result;
    },

    /**
     * Apply syntax highlighting to an element
     * @param {HTMLElement} element - Element containing Rego code
     */
    highlightElement(element) {
        if (!element) return;

        const code = element.textContent || element.innerText;
        element.innerHTML = this.highlight(code);
    },

    /**
     * Apply syntax highlighting to all elements with a specific class
     * @param {string} className - CSS class to target
     */
    highlightAll(className = 'language-rego') {
        const elements = document.querySelectorAll(`code.${className}, pre.${className}`);
        elements.forEach(el => this.highlightElement(el));
    }
};

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { RegoSyntax };
}

// Make available globally
if (typeof window !== 'undefined') {
    window.RegoSyntax = RegoSyntax;
}
