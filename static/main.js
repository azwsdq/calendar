(function() {
    'use strict';

    // --- Мобильное меню ---
    window.toggleMobileMenu = function() {
        const nav = document.getElementById('mobileNav');
        if (nav) nav.classList.toggle('active');
    };
    document.addEventListener('click', function(e) {
        const nav = document.getElementById('mobileNav');
        const btn = document.querySelector('.mobile-menu-btn');
        if (nav && !nav.contains(e.target) && !btn.contains(e.target)) {
            nav.classList.remove('active');
        }
    });

    // --- Модальное окно ---
    window.openDayModal = function(day) {
        const modal = document.getElementById('dayModal');
        const body = document.getElementById('modal-body');
        const title = document.getElementById('modal-title');
        const days = document.querySelectorAll('.day.clickable-day');
        let formattedDate = `${day}.04.2026`;

        for (let d of days) {
            if (d.querySelector('.day-num').textContent == day) {
                const hiddenSpan = d.querySelector('.hidden-date');
                if (hiddenSpan) formattedDate = hiddenSpan.textContent;
                break;
            }
        }

        title.textContent = formattedDate;

        const contentSrc = document.getElementById('modal-content-' + day);
        if (contentSrc) {
            body.innerHTML = contentSrc.innerHTML;
        } else {
            body.innerHTML = '<p style="text-align:center; padding:20px; color:var(--text-muted)">Нет событий</p>';
        }

        modal.classList.add('active');
    };

    window.closeDayModal = function(e) {
        if (!e || e.target.id === 'dayModal' || e.target.classList.contains('modal-close')) {
            document.getElementById('dayModal').classList.remove('active');
        }
    };

    // --- Задачи ---
    window.openEdit = function(id) {
        const card = document.getElementById('task-' + id);
        if (!card) return;
        card.querySelector('.task-top-row').style.display = 'none';
        card.querySelector('.task-meta').style.display = 'none';
        card.querySelector('.task-card__desc').style.display = 'none';
        document.getElementById('edit-form-' + id).style.display = 'flex';
    };

    window.closeEdit = function(id) {
        const card = document.getElementById('task-' + id);
        if (!card) return;
        card.querySelector('.task-top-row').style.display = 'flex';
        card.querySelector('.task-meta').style.display = 'block';
        const desc = card.querySelector('.task-card__desc');
        if(desc) desc.style.display = 'block';
        document.getElementById('edit-form-' + id).style.display = 'none';
    };
    function initCalendar() {
        const dataEl = document.getElementById('calendar-data');
        if (!dataEl) return;
        const today = new Date();
        const yearEl = document.querySelector('.month-title');
        const yearText = yearEl ? yearEl.textContent.split(' ')[1] : today.getFullYear();
        const month = dataEl.dataset.month;
        const year = parseInt(yearText, 10);

        if (year === today.getFullYear() && month == (today.getMonth() + 1)) {
            document.querySelectorAll('.day .day-num').forEach(el => {
                if (parseInt(el.textContent, 10) === today.getDate()) {
                    el.closest('.day').classList.add('today');
                }
            });
        }

        const dateInput = document.querySelector('.add-form input[type="date"]');
        if (dateInput && !dateInput.value) dateInput.value = today.toISOString().slice(0, 10);
    }

    document.addEventListener('DOMContentLoaded', () => {
        initCalendar();
    });
})();