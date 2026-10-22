/* AquaWord Android-only distraction-free reading/editing mode.
 * Installs inside the real Collabora browser bootstrap; does not replace its engine.
 * This block is independently testable in a small DOM harness.
 */
(function installAquaWordFocusMode() {
    if (!window.ThisIsTheAndroidApp || !document.body || !window.app || !app.map)
        return;
    var documentMap = app.map;
    var mounted = false;
    var active = false;
    var control = null;

    function redraw() {
        window.requestAnimationFrame(function () {
            window.dispatchEvent(new Event('resize'));
            if (typeof documentMap.invalidateSize === 'function')
                documentMap.invalidateSize();
        });
    }

    function setActive(value) {
        active = !!value;
        document.body.classList.toggle('aquaword-focus-active', active);
        control.setAttribute('aria-pressed', active ? 'true' : 'false');
        control.setAttribute('aria-label', active ? 'Exit focus mode' : 'Enter focus mode');
        control.setAttribute('title', active ? 'Exit focus mode' : 'Enter focus mode');
        control.textContent = active ? '\u2715' : '\u2922';
        redraw();
    }

    function mount() {
        if (mounted || !documentMap.getDocType || documentMap.getDocType() !== 'text')
            return;
        mounted = true;
        control = document.createElement('button');
        control.type = 'button';
        control.id = 'aquaword-focus-toggle';
        control.className = 'aquaword-focus-toggle';
        control.setAttribute('aria-controls', 'document-container');
        control.addEventListener('click', function () {
            setActive(!active);
        });
        document.body.appendChild(control);
        setActive(false);
        document.addEventListener('keydown', function (event) {
            if (active && event.key === 'Escape') {
                event.preventDefault();
                setActive(false);
            }
        });
    }

    if (typeof documentMap.on === 'function')
        documentMap.on('docloaded', mount);
    mount();
})();
