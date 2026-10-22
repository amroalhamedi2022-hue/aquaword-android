/* AquaWord Focus Mode DOM contract tests in Node (no network or dependencies).
 * Test the exact JavaScript inserted in the pinned Collabora bootstrap. */
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');

const code = fs.readFileSync('branding/focus_mode.js', 'utf8');
const selectors = new Set();
const handlers = {};
const listeners = {};
const body = {
    classList: {
        toggle(name, active) {
            if (active) selectors.add(name); else selectors.delete(name);
        }
    },
    appendChild(el) { body.child = el; }
};
function createButton() {
    return {
        attributes: {},
        addEventListener(name, cb) { handlers[name] = cb; },
        setAttribute(name, value) { this.attributes[name] = value; },
        textContent: '',
    };
}
const map = {
    type: 'text',
    callbacks: {},
    resizeCount: 0,
    getDocType() { return this.type; },
    invalidateSize() { this.resizeCount++; },
    on(event, cb) { this.callbacks[event] = cb; }
};
const windowShim = {
    ThisIsTheAndroidApp: true,
    app: { map },
    requestAnimationFrame(cb) { cb(); },
    dispatchEvent(evt) { windowShim.lastEvent = evt.type; },
};
const documentShim = {
    body,
    createElement(tag) { assert.equal(tag,'button'); return createButton(); },
    addEventListener(event, cb) { listeners[event] = cb; }
};
function run() {
    vm.runInNewContext(code, {
        window: windowShim, app: windowShim.app, document: documentShim,
        Event: function Event(type) { this.type = type; }
    }, {timeout: 1500});
}
run();
assert.equal(body.child.id, 'aquaword-focus-toggle');
assert.equal(body.child.attributes['aria-pressed'], 'false');
assert.equal(body.child.attributes['aria-label'], 'Enter focus mode');
handlers.click();
assert.equal(selectors.has('aquaword-focus-active'), true);
assert.equal(body.child.attributes['aria-pressed'], 'true');
assert.equal(body.child.attributes['aria-label'], 'Exit focus mode');
assert.equal(windowShim.lastEvent, 'resize');
assert.ok(map.resizeCount >= 2);
handlers.click();
assert.equal(selectors.has('aquaword-focus-active'), false);
handlers.click();
listeners.keydown({key:'Escape', preventDefault(){windowShim.escaped=true;}});
assert.equal(windowShim.escaped, true);
assert.equal(selectors.has('aquaword-focus-active'), false);
map.callbacks.docloaded();
assert.equal(body.child.id, 'aquaword-focus-toggle');

const original = body.child;
windowShim.ThisIsTheAndroidApp = false;
run();
assert.equal(body.child, original);

console.log('PASS: native-only focus toggle, reversible, Escape, resize, ARIA and no duplicate');
