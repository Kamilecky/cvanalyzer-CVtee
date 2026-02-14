/* CV Analyzer - Main JavaScript */

document.addEventListener('DOMContentLoaded', function() {
    initThemeToggle();
    initSidebarToggle();
    initUploadZone();
    initAutoCloseAlerts();
});

/* Theme toggle (light/dark) with localStorage persistence */
function initThemeToggle() {
    var toggle = document.getElementById('themeToggle');
    if (!toggle) return;

    var saved = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', saved);
    updateThemeIcon(saved);

    toggle.addEventListener('click', function() {
        var current = document.documentElement.getAttribute('data-theme');
        var next = current === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', next);
        localStorage.setItem('theme', next);
        updateThemeIcon(next);
    });
}

function updateThemeIcon(theme) {
    var toggle = document.getElementById('themeToggle');
    if (!toggle) return;
    toggle.innerHTML = theme === 'dark'
        ? '<i class="bi bi-sun"></i>'
        : '<i class="bi bi-moon"></i>';
}

/* Sidebar toggle (mobile) */
function initSidebarToggle() {
    var btn = document.getElementById('sidebarToggle');
    var sidebar = document.getElementById('sidebar');
    if (!btn || !sidebar) return;

    btn.addEventListener('click', function() {
        sidebar.classList.toggle('show');
    });

    document.addEventListener('click', function(e) {
        if (window.innerWidth <= 992 &&
            !sidebar.contains(e.target) &&
            !btn.contains(e.target)) {
            sidebar.classList.remove('show');
        }
    });
}

/* Drag & drop upload for CV files (PDF, DOCX, TXT) */
function initUploadZone() {
    var zone = document.getElementById('uploadZone');
    var input = document.getElementById('cvFileInput');
    if (!zone || !input) return;

    var allowedExtensions = ['.pdf', '.docx', '.txt'];

    zone.addEventListener('click', function() {
        input.click();
    });

    zone.addEventListener('dragover', function(e) {
        e.preventDefault();
        zone.classList.add('dragover');
    });

    zone.addEventListener('dragleave', function(e) {
        e.preventDefault();
        zone.classList.remove('dragover');
    });

    zone.addEventListener('drop', function(e) {
        e.preventDefault();
        zone.classList.remove('dragover');
        var files = e.dataTransfer.files;
        if (files.length > 0) {
            var file = files[0];
            var ext = file.name.toLowerCase().substring(file.name.lastIndexOf('.'));
            if (allowedExtensions.indexOf(ext) === -1) {
                showAlert('Only PDF, DOCX, and TXT files are accepted.', 'danger');
                return;
            }
            input.files = files;
            updateFileName(file.name);
            document.getElementById('uploadForm').submit();
        }
    });

    input.addEventListener('change', function() {
        if (input.files.length > 0) {
            updateFileName(input.files[0].name);
            document.getElementById('uploadForm').submit();
        }
    });
}

function updateFileName(name) {
    var zone = document.getElementById('uploadZone');
    if (!zone) return;
    var textEl = zone.querySelector('.upload-text');
    if (textEl) {
        textEl.textContent = 'Uploading: ' + name;
    }
}

/* Auto-close alerts after 5 seconds */
function initAutoCloseAlerts() {
    var alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            var bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            bsAlert.close();
        }, 5000);
    });
}

/* Programmatic alert display */
function showAlert(message, type) {
    var container = document.getElementById('alertContainer');
    if (!container) return;
    var alert = document.createElement('div');
    alert.className = 'alert alert-' + type + ' alert-dismissible fade show';
    alert.innerHTML = message + '<button type="button" class="btn-close" data-bs-dismiss="alert"></button>';
    container.prepend(alert);
    setTimeout(function() {
        if (alert.parentNode) {
            var bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            bsAlert.close();
        }
    }, 5000);
}
