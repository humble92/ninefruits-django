// Portal and sign-in pages: Tailwind CSS 4, HTMX 2, Alpine.js 3 (CSP build).
//
// Content Security Policy: scripts need the per-request nonce (settings SECURE_CSP), so there
// are no inline event handlers. Alpine uses its CSP build (no eval): components are
// registered with Alpine.data() below and templates reference them by name.
import '../css/app.css';

import htmx from 'htmx.org';
import Alpine from '@alpinejs/csp';

// HTMX: no eval (hx-on, js: values), our own indicator styles in app.css. The CSRF token is
// sent on every request through hx-headers on <body> (templates/base.html).
htmx.config.allowEval = false;
htmx.config.allowScriptTags = false;
htmx.config.includeIndicatorStyles = false;
htmx.config.selfRequestsOnly = true;
window.htmx = htmx;

// Dismissible flash message.
Alpine.data('dismissible', () => ({
    visible: true,
    dismiss() {
        this.visible = false;
    },
}));

window.Alpine = Alpine;
Alpine.start();
