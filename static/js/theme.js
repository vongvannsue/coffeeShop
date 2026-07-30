(function () {
    var toggle = document.getElementById('theme-toggle');
    if (!toggle) return;
    var label = toggle.querySelector('.theme-toggle-label');

    function effectiveTheme() {
        var explicit = document.documentElement.getAttribute('data-theme');
        if (explicit === 'light' || explicit === 'dark') return explicit;
        return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }

    function syncLabel() {
        label.textContent = effectiveTheme() === 'dark' ? 'Light' : 'Dark';
    }

    syncLabel();

    toggle.addEventListener('click', function () {
        var next = effectiveTheme() === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', next);
        localStorage.setItem('theme', next);
        syncLabel();
    });
})();
