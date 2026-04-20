/**
 * Calendar App - Main JavaScript
 * Все клиентские скрипты вынесены из HTML-шаблонов
 */
(function() {
    'use strict';

    // ==================== MOBILE MENU ====================
    function initMobileMenu() {
        const toggle = document.getElementById('mobileMenuToggle');
        const overlay = document.getElementById('mobileMenuOverlay');
        if (!toggle || !overlay) return;

        function closeMenu() {
            toggle.setAttribute('aria-expanded', 'false');
            overlay.classList.remove('active');
            document.body.style.overflow = '';
        }

        toggle.addEventListener('click', () => {
            const isExpanded = toggle.getAttribute('aria-expanded') === 'true';
            toggle.setAttribute('aria-expanded', !isExpanded);
            overlay.classList.toggle('active');
            document.body.style.overflow = isExpanded ? '' : 'hidden';
        });

        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) closeMenu();
        });

        overlay.querySelectorAll('a, button').forEach(el => {
            el.addEventListener('click', closeMenu);
        });

        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && overlay.classList.contains('active')) closeMenu();
        });
    }

    // ==================== CALENDAR PAGE ====================
    function initCalendar() {
        const yearEl = document.getElementById('calendar-year');
        const monthEl = document.getElementById('calendar-month');
        if (!yearEl || !monthEl) return;

        const year = parseInt(yearEl.dataset.year, 10);
        const month = parseInt(monthEl.dataset.month, 10);
        const today = new Date();

        // Highlight today
        if (year === today.getFullYear() && month === today.getMonth() + 1) {
            document.querySelectorAll('.day .day-num').forEach(el => {
                if (parseInt(el.textContent, 10) === today.getDate()) {
                    el.closest('.day')?.classList.add('today');
                }
            });
        }

        // Pre-fill date input
        const dateInput = document.querySelector('.add-form input[type="date"]');
        if (dateInput && !dateInput.value) {
            dateInput.value = today.toISOString().slice(0, 10);
        }
    }

    // ==================== REGISTER PAGE ====================
    function initRegister() {
        const form = document.getElementById('register-form');
        if (!form) return;

        const pw = document.getElementById('password');
        const confirm = document.getElementById('password_confirm');
        const hint = document.getElementById('confirm-hint');
        if (!pw || !confirm || !hint) return;

        function checkMatch() {
            if (!confirm.value) { hint.textContent = ''; return; }
            if (pw.value === confirm.value) {
                hint.textContent = 'Пароли совпадают';
                hint.className = 'auth-field-hint auth-field-hint--ok';
            } else {
                hint.textContent = 'Пароли не совпадают';
                hint.className = 'auth-field-hint auth-field-hint--err';
            }
        }

        confirm.addEventListener('input', checkMatch);
        pw.addEventListener('input', checkMatch);

        form.addEventListener('submit', (e) => {
            if (pw.value !== confirm.value) {
                e.preventDefault();
                hint.textContent = 'Пароли не совпадают';
                hint.className = 'auth-field-hint auth-field-hint--err';
                confirm.focus();
            } else if (pw.value.length < 8) {
                e.preventDefault();
                pw.focus();
            }
        });
    }

    // ==================== TASKS PAGE ====================
    function initTasks() {
        // Pre-fill date input
        const dateInput = document.querySelector('.add-form--tasks input[type="date"]');
        if (dateInput && !dateInput.value) {
            dateInput.value = new Date().toISOString().slice(0, 10);
        }

        // Expose edit functions globally for inline onclick handlers
        window.openEdit = function(id) {
            const card = document.getElementById('task-' + id);
            if (!card) return;
            card.querySelector('.task-view').style.display = 'none';
            document.getElementById('edit-form-' + id).style.display = 'flex';
        };

        window.closeEdit = function(id) {
            const card = document.getElementById('task-' + id);
            if (!card) return;
            card.querySelector('.task-view').style.display = 'flex';
            document.getElementById('edit-form-' + id).style.display = 'none';
        };

        // Confirm delete
        document.querySelectorAll('form[action*="delete"]').forEach(form => {
            form.addEventListener('submit', (e) => {
                if (!confirm('Удалить это событие?')) e.preventDefault();
            });
        });
    }

    // ==================== INIT ====================
    document.addEventListener('DOMContentLoaded', () => {
        initMobileMenu();
        initCalendar();
        initRegister();
        initTasks();
    });
})();