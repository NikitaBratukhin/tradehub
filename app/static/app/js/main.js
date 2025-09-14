// app/static/app/js/main.js

/**
 * Главный объект приложения TradeHub
 * Инкапсулирует всю фронтенд-логику.
 */
const TradeHub = {
    // --- Свойства и Утилиты --- //

    /**
     * Получает CSRF-токен для безопасных POST-запросов.
     * @returns {string|null} CSRF-токен.
     */
    getCsrfToken() {
        if (typeof CSRF_TOKEN !== 'undefined' && CSRF_TOKEN) return CSRF_TOKEN;

        // Попытка получить из meta-тега
        const metaToken = document.querySelector('[name=csrfmiddlewaretoken]');
        if (metaToken) return metaToken.value;

        // Попытка получить из cookie
        const cookie = document.cookie.match(/csrftoken=([^;]+)/);
        return cookie ? cookie[1] : null;
    },

    /**
     * Создает URL для API-запроса, подставляя ID в базовый URL.
     * @param {string} baseUrl - Базовый URL с плейсхолдером '0' или '/0/' (например, '/api/endpoint/0/').
     * @param {string|number} id - ID для вставки.
     * @returns {string|null} Готовый URL.
     */
    buildUrl(baseUrl, id) {
        if (!baseUrl) return null;
        // Поддерживаем как '/0/' так и '/0' в конце URL, а также просто '0' в любом месте
        return baseUrl.replace(/\/0(\/?)$/, `/${id}$1`).replace(/\b0\b/, id);
    },

    /**
     * Форматирует числа для отображения (1K, 1M и т.д.)
     * @param {number} num - Число для форматирования
     * @returns {string} Отформатированное число
     */
    formatNumber(num) {
        if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
        if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
        return num.toString();
    },

    /**
     * Копирует текст в буфер обмена
     * @param {string} text - Текст для копирования
     */
    async copyToClipboard(text) {
        try {
            await navigator.clipboard.writeText(text);
            this.showNotification('Скопировано в буфер обмена!', 'success');
        } catch (error) {
            this.showNotification('Не удалось скопировать', 'error');
        }
    },

    // --- Компоненты UI --- //

    /**
     * Показывает всплывающее уведомление (alert).
     * @param {string} message - Текст сообщения.
     * @param {string} type - Тип ('success' или 'error').
     */
    showNotification(message, type = 'success') {
        let container = document.querySelector('.messages');
        if (!container) {
            container = document.createElement('div');
            container.className = 'messages';
            container.style.cssText = `
                position: fixed;
                top: 80px;
                right: 20px;
                z-index: 1001;
                width: 320px;
            `;
            document.body.appendChild(container);
        }

        const alert = document.createElement('div');
        alert.className = `alert alert-${type}`;
        alert.innerHTML = `
            <span>${message}</span>
            <button class="alert-close" onclick="this.parentElement.remove()">&times;</button>
        `;

        container.appendChild(alert);

        setTimeout(() => {
            if (alert.parentElement) {
                alert.style.animation = 'slide-out-right 0.3s ease-in forwards';
                alert.addEventListener('animationend', () => {
                    if (alert.parentElement) alert.remove();
                });
            }
        }, 5000);
    },

    /**
     * Управляет модальным окном приветствия.
     */
    initWelcomeModal() {
        const modal = document.getElementById('welcome-modal');
        const closeButton = document.getElementById('close-welcome-modal');
        if (!modal) return;

        const show = () => modal.style.display = 'flex';
        const hide = () => modal.style.display = 'none';

        if (closeButton) {
            closeButton.addEventListener('click', hide);
        }
        window.addEventListener('keydown', (e) => e.key === 'Escape' && hide());

        // Экспонируем функцию для вызова из шаблона
        this.showWelcomeModal = show;
    },

    // --- Логика Уведомлений --- //

    /**
     * Инициализирует систему уведомлений.
     */
    initNotifications() {
        // Скрываем существующие алерты через 5 секунд
        const alerts = document.querySelectorAll('.alert');
        alerts.forEach(alert => {
            setTimeout(() => {
                if (alert.parentElement) {
                    alert.style.animation = 'slide-out-right 0.3s ease-in forwards';
                    setTimeout(() => {
                        if (alert.parentElement) alert.remove();
                    }, 300);
                }
            }, 5000);
        });

        // Элементы уведомлений
        const bellButton = document.getElementById('notification-button');
        const bellCount = document.getElementById('notification-count');
        const dropdown = document.getElementById('notification-dropdown');
        const listContainer = document.getElementById('notification-list');

        if (!bellButton || !dropdown || !listContainer) {
            this.updateUnreadCountBadge();
            return;
        }

        // Переключение видимости dropdown
        bellButton.addEventListener('click', (e) => {
            e.stopPropagation();
            const expanded = dropdown.getAttribute('aria-hidden') === 'false';
            if (expanded) {
                this.hideNotificationDropdown(dropdown);
            } else {
                this.showNotificationDropdown(dropdown, listContainer);
            }
        });

        // Закрытие dropdown при клике вне его
        document.addEventListener('click', () => {
            this.hideNotificationDropdown(dropdown);
        });

        // Предотвращение закрытия при клике внутри dropdown
        dropdown.addEventListener('click', (e) => {
            e.stopPropagation();
        });

        // Обработка кнопок "отметить как прочитанное"
        listContainer.addEventListener('click', async (e) => {
            const btn = e.target.closest('.mark-read-btn');
            if (!btn) return;

            const id = btn.dataset.id;
            if (!id) return;

            const base = (typeof MARK_NOTIFICATION_READ_API_URL_BASE !== 'undefined')
                ? MARK_NOTIFICATION_READ_API_URL_BASE
                : null;
            const url = this.buildUrl(base, id) || `/api/notifications/mark-read/${id}/`;

            try {
                const response = await fetch(url, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': this.getCsrfToken(),
                        'Accept': 'application/json'
                    },
                    credentials: 'same-origin'
                });

                if (!response.ok) throw new Error('Network response was not ok');

                const data = await response.json();
                if (data.status === 'ok') {
                    const li = btn.closest('.notification-item');
                    if (li) {
                        li.classList.remove('unread');
                        btn.remove();
                    }
                    this.decrementUnreadCount();
                } else {
                    this.showNotification('Не удалось пометить уведомление как прочитанное', 'error');
                }
            } catch (error) {
                console.error('Mark as read error:', error);
                this.showNotification('Ошибка сети при отметке уведомления', 'error');
            }
        });

        // Инициальное обновление счетчика
        this.updateUnreadCountBadge();
    },

    showNotificationDropdown(dropdown, listContainer) {
        dropdown.style.display = 'block';
        dropdown.setAttribute('aria-hidden', 'false');
        this.fetchAndRenderNotifications(listContainer);
    },

    hideNotificationDropdown(dropdown) {
        dropdown.style.display = 'none';
        dropdown.setAttribute('aria-hidden', 'true');
    },

    async fetchAndRenderNotifications(listContainer) {
        try {
            const url = (typeof NOTIFICATIONS_API_URL !== 'undefined') ? NOTIFICATIONS_API_URL : null;
            if (!url) return;

            const response = await fetch(url, {
                method: 'GET',
                headers: { 'Accept': 'application/json' },
                credentials: 'same-origin'
            });

            if (!response.ok) throw new Error('Network response was not ok');

            const data = await response.json();
            const notifications = Array.isArray(data.notifications) ? data.notifications : [];
            this.renderNotificationList(listContainer, notifications);

            if (typeof data.unread_count !== 'undefined') {
                this.setUnreadCount(data.unread_count);
            } else {
                this.updateUnreadCountBadge();
            }
        } catch (error) {
            console.error('Не удалось загрузить уведомления:', error);
        }
    },

    renderNotificationList(container, notifications) {
        container.innerHTML = '';

        if (!notifications || notifications.length === 0) {
            container.innerHTML = '<div class="notification-empty">Непрочитанных уведомлений нет</div>';
            return;
        }

        const ul = document.createElement('ul');
        ul.className = 'notification-items list-unstyled';

        notifications.forEach(notification => {
            const li = this.createNotificationItem(notification);
            ul.appendChild(li);
        });

        container.appendChild(ul);
    },

    createNotificationItem(notification) {
        const li = document.createElement('li');
        li.className = 'notification-item';
        if (!notification.is_read) li.classList.add('unread');
        li.dataset.id = notification.id;

        const inner = document.createElement('div');
        inner.className = 'notification-inner';

        const title = document.createElement('div');
        title.className = 'notification-title';
        title.textContent = notification.title || '';

        const time = document.createElement('small');
        time.className = 'notification-time';
        time.textContent = notification.created_at || '';

        const message = document.createElement('div');
        message.className = 'notification-message';
        message.textContent = notification.message || '';

        inner.appendChild(title);
        inner.appendChild(time);
        inner.appendChild(message);

        const actions = document.createElement('div');
        actions.className = 'notification-actions';

        if (notification.link) {
            const openBtn = document.createElement('a');
            openBtn.className = 'btn btn-sm btn-link';
            openBtn.href = notification.link;
            openBtn.textContent = 'Открыть';
            actions.appendChild(openBtn);
        }

        if (!notification.is_read) {
            const markBtn = document.createElement('button');
            markBtn.className = 'btn btn-sm btn-primary mark-read-btn';
            markBtn.textContent = 'Отметить как прочитанное';
            markBtn.dataset.id = notification.id;
            actions.appendChild(markBtn);
        }

        li.appendChild(inner);
        li.appendChild(actions);
        return li;
    },

    async updateUnreadCountBadge() {
        try {
            const url = (typeof UNREAD_NOTIFICATIONS_COUNT_API_URL !== 'undefined')
                ? UNREAD_NOTIFICATIONS_COUNT_API_URL
                : null;

            let count = 0;

            if (url) {
                const response = await fetch(url, {
                    method: 'GET',
                    headers: { 'Accept': 'application/json' },
                    credentials: 'same-origin'
                });

                if (response.ok) {
                    const data = await response.json();
                    count = data.unread_count || 0;
                }
            }

            this.setUnreadCount(count);
        } catch (error) {
            console.error('Не удалось обновить счётчик уведомлений:', error);
        }
    },

    setUnreadCount(count) {
        const bellCount = document.getElementById('notification-count');
        if (!bellCount) return;

        const numCount = Number(count) || 0;
        if (numCount > 0) {
            bellCount.textContent = numCount;
            bellCount.style.display = 'inline-block';
        } else {
            bellCount.style.display = 'none';
        }
    },

    decrementUnreadCount() {
        const bellCount = document.getElementById('notification-count');
        if (!bellCount) return;

        let current = parseInt(bellCount.textContent || '0', 10);
        current = Math.max(0, current - 1);
        this.setUnreadCount(current);
    },

    // --- Логика Бустов --- //

    /**
     * Инициализирует логику для кнопок "буста" (лайков) с подтверждением.
     */
    initBoostButtons() {
        document.body.addEventListener('click', async (e) => {
            const button = e.target.closest('.boost-btn');
            if (!button || button.classList.contains('processing')) return;

            const pubId = button.dataset.pubId;
            if (!pubId) return;

            // Добавлено подтверждение действия
            const isBoosted = button.classList.contains('boosted');
            const confirmationMessage = isBoosted
                ? "Вы уверены, что хотите убрать свой буст?"
                : "Вы хотите использовать один из своих дневных бустов для этой идеи?";

            if (!confirm(confirmationMessage)) {
                return;
            }

            button.classList.add('processing');

            let url = null;
            if (typeof TOGGLE_BOOST_API_URL_BASE !== 'undefined' && TOGGLE_BOOST_API_URL_BASE) {
                url = this.buildUrl(TOGGLE_BOOST_API_URL_BASE, pubId);
            } else {
                url = `/api/publication/${pubId}/toggle_boost/`;
            }

            try {
                const response = await fetch(url, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': this.getCsrfToken(),
                        'Content-Type': 'application/json',
                        'Accept': 'application/json'
                    },
                    credentials: 'same-origin'
                });

                const data = await response.json();

                if (!response.ok) {
                    throw new Error(data.detail || 'Ошибка сети');
                }

                if (data.status === 'ok') {
                    this.updateBoostButtonUI(button, data);
                } else {
                    this.showNotification(data.message || 'Произошла ошибка', 'error');
                }
            } catch (error) {
                console.error('Boost error:', error);
                this.showNotification(error.message, 'error');
            } finally {
                button.classList.remove('processing');
            }
        });
    },

    /**
     * Обновляет состояние и внешний вид кнопки буста.
     * @param {HTMLElement} button - Элемент кнопки.
     * @param {object} data - Данные от API { boost_count, boosted }.
     */
    updateBoostButtonUI(button, data) {
        const countEl = button.querySelector('.boost-count');
        if (countEl && typeof data.boost_count !== 'undefined') {
            countEl.textContent = data.boost_count;
        }

        button.classList.toggle('boosted', data.boosted);

        if (data.boosted) {
            button.style.animation = 'boost-effect 0.6s ease-out';
            this.createBoostParticles(button);
        } else {
            button.style.animation = 'unboost-effect 0.3s ease-out';
        }

        button.addEventListener('animationend', () => button.style.animation = '', { once: true });
    },

    /**
     * Создает анимированные частицы при "бусте".
     * @param {HTMLElement} button - Элемент кнопки, от которой идет анимация.
     */
    createBoostParticles(button) {
        const particles = ['🚀', '⭐', '💫', '✨'];
        const rect = button.getBoundingClientRect();

        for (let i = 0; i < 8; i++) {
            const particle = document.createElement('div');
            particle.className = 'boost-particle';
            particle.textContent = particles[Math.floor(Math.random() * particles.length)];

            const dx = (Math.random() - 0.5) * 120;
            const dy = -Math.random() * 100 - 30;

            particle.style.cssText = `
                left: ${rect.left + rect.width / 2}px;
                top: ${rect.top + rect.height / 2}px;
                --dx: ${dx}px;
                --dy: ${dy}px;
            `;
            document.body.appendChild(particle);
            setTimeout(() => particle.remove(), 1000);
        }
    },

    // --- Логика Подписок --- //

    /**
     * Инициализирует кнопку подписки/отписки.
     */
    initFollowButton() {
        const followBtn = document.getElementById('follow-btn');
        if (!followBtn) return;

        followBtn.addEventListener('click', async () => {
            const username = followBtn.dataset.username;
            if (!username) return;

            const url = `/api/user/${username}/toggle-follow/`;

            try {
                const response = await fetch(url, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': this.getCsrfToken(),
                        'Accept': 'application/json'
                    },
                    credentials: 'same-origin'
                });

                if (!response.ok) throw new Error('Ошибка сети');

                const data = await response.json();
                if (data.status === 'ok') {
                    this.updateFollowButtonUI(followBtn, data.following);
                    const message = data.following ? 'Вы успешно подписались' : 'Вы отписались';
                    this.showNotification(message, 'success');
                }
            } catch (error) {
                console.error('Follow error:', error);
                this.showNotification('Не удалось выполнить действие', 'error');
            }
        });
    },

    /**
     * Обновляет состояние и внешний вид кнопки подписки.
     * @param {HTMLElement} button - Элемент кнопки.
     * @param {boolean} isFollowing - Текущий статус подписки.
     */
    updateFollowButtonUI(button, isFollowing) {
        if (isFollowing) {
            button.textContent = 'Отписаться';
            button.classList.remove('btn-primary');
            button.classList.add('btn-secondary');
        } else {
            button.textContent = 'Подписаться';
            button.classList.remove('btn-secondary');
            button.classList.add('btn-primary');
        }
    },

    // --- Прочие Инициализации --- //

    /**
     * Инициализирует фильтры публикаций
     */
    initFilterButtons() {
        const filterButtons = document.querySelectorAll('.filter-btn');

        filterButtons.forEach(button => {
            button.addEventListener('click', () => {
                filterButtons.forEach(btn => btn.classList.remove('active'));
                button.classList.add('active');

                const filter = button.dataset.filter;
                console.log('Фильтр:', filter);
                // TODO: Реализовать фильтрацию публикаций
            });
        });
    },

    /**
     * Инициализирует мобильное меню
     */
    initMobileMenu() {
        if (window.innerWidth <= 768) {
            this.addMobileMenuButton();
        }

        window.addEventListener('resize', () => {
            if (window.innerWidth <= 768) {
                this.addMobileMenuButton();
            } else {
                this.removeMobileMenuButton();
            }
        });
    },

    addMobileMenuButton() {
        if (document.querySelector('.mobile-menu-btn')) return;

        const navbar = document.querySelector('.nav-container');
        const navMenu = document.querySelector('.nav-menu');
        if (!navMenu || !navbar) return;

        const mobileMenuBtn = document.createElement('button');
        mobileMenuBtn.className = 'mobile-menu-btn';
        mobileMenuBtn.innerHTML = '☰';
        mobileMenuBtn.style.cssText = `
            display: block;
            background: none;
            border: none;
            color: #8b5cf6;
            font-size: 1.5rem;
            cursor: pointer;
            padding: 0.5rem;
        `;

        const navUser = document.querySelector('.nav-user');
        const navAuth = document.querySelector('.nav-auth');
        const insertBefore = navUser || navAuth;

        if (insertBefore) {
            navbar.insertBefore(mobileMenuBtn, insertBefore);
        }

        mobileMenuBtn.addEventListener('click', () => this.toggleMobileMenu());
    },

    removeMobileMenuButton() {
        const mobileMenuBtn = document.querySelector('.mobile-menu-btn');
        if (mobileMenuBtn) mobileMenuBtn.remove();
    },

    toggleMobileMenu() {
        const navMenu = document.querySelector('.nav-menu');
        if (!navMenu) return;

        if (navMenu.style.display === 'flex') {
            navMenu.style.display = 'none';
        } else {
            navMenu.style.display = 'flex';
            navMenu.style.flexDirection = 'column';
            navMenu.style.position = 'absolute';
            navMenu.style.top = '100%';
            navMenu.style.left = '0';
            navMenu.style.right = '0';
            navMenu.style.background = 'rgba(15, 15, 35, 0.98)';
            navMenu.style.border = '1px solid #8b5cf6';
            navMenu.style.borderTop = 'none';
            navMenu.style.borderRadius = '0 0 15px 15px';
            navMenu.style.padding = '1rem';
            navMenu.style.gap = '0.5rem';
            navMenu.style.zIndex = '1001';
        }
    },

    /**
     * Инициализирует плавную прокрутку
     */
    initSmoothScrolling() {
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', (e) => {
                e.preventDefault();
                const target = document.querySelector(anchor.getAttribute('href'));
                if (target) {
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            });
        });
    },

    /**
     * Инициализирует валидацию форм
     */
    initFormValidation() {
        const forms = document.querySelectorAll('form');

        forms.forEach(form => {
            form.addEventListener('submit', (e) => {
                const requiredFields = form.querySelectorAll('[required]');
                let isValid = true;

                requiredFields.forEach(field => {
                    if (!field.value.trim()) {
                        field.classList.add('error');
                        isValid = false;
                    } else {
                        field.classList.remove('error');
                    }
                });

                if (!isValid) {
                    e.preventDefault();
                    this.showNotification('Заполните все обязательные поля', 'error');
                }
            });
        });
    },

    /**
     * Инициализирует тему
     */
    initTheme() {
        try {
            const savedTheme = localStorage.getItem('theme') || 'dark';
            document.body.classList.add(savedTheme + '-theme');
        } catch (error) {
            // localStorage недоступен
            document.body.classList.add('dark-theme');
        }
    },

    /**
     * Инициализирует анимации появления элементов при прокрутке.
     */
    initScrollAnimations() {
        const animatedElements = document.querySelectorAll(
            '.publication-card, .feature-card, .stat-card, .auth-card, .profile-card, .achievement-card, .menu-item'
        );

        const observer = new IntersectionObserver((entries, obs) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.style.animation = 'fade-in-up 0.6s ease-out forwards';
                    obs.unobserve(entry.target);
                }
            });
        }, {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        });

        animatedElements.forEach((el, index) => {
            el.style.opacity = '0';
            el.style.transform = 'translateY(30px)';
            el.style.animationDelay = `${index * 0.1}s`;
            observer.observe(el);
        });
    },

    /**
     * Инициализирует все необходимые стили
     */
    initStyles() {
        // Стили для анимаций
        if (!document.querySelector('#tradehub-animations')) {
            const animationStyles = document.createElement('style');
            animationStyles.id = 'tradehub-animations';
            animationStyles.textContent = `
                @keyframes fade-in-up {
                    from {
                        opacity: 0;
                        transform: translateY(30px);
                    }
                    to {
                        opacity: 1;
                        transform: translateY(0);
                    }
                }

                @keyframes slide-out-right {
                    from { 
                        transform: translateX(0); 
                        opacity: 1; 
                    }
                    to { 
                        transform: translateX(100%); 
                        opacity: 0; 
                    }
                }

                @keyframes boost-effect {
                    0% { transform: scale(1); }
                    50% { transform: scale(1.2); }
                    100% { transform: scale(1); }
                }
                
                @keyframes unboost-effect {
                    0% { transform: scale(1); }
                    50% { transform: scale(0.8); }
                    100% { transform: scale(1); }
                }

                @keyframes particleFloat {
                    0% {
                        transform: translate(0, 0) scale(1);
                        opacity: 1;
                    }
                    100% {
                        transform: translate(var(--dx), var(--dy)) scale(0);
                        opacity: 0;
                    }
                }

                .boost-btn.boosted {
                    color: #22c55e !important;
                    background: rgba(34, 197, 94, 0.06) !important;
                }
                
                .boost-btn.processing {
                    opacity: 0.7;
                    pointer-events: none;
                }
                
                .boost-particle {
                    position: absolute;
                    pointer-events: none;
                    font-size: 12px;
                    animation: particleFloat 1s ease-out forwards;
                    z-index: 1000;
                }

                .form-input.error,
                .form-textarea.error {
                    border-color: #ef4444 !important;
                    box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.1) !important;
                }

                .alert-close {
                    background: none;
                    border: none;
                    color: inherit;
                    font-size: 1.2em;
                    cursor: pointer;
                    padding: 0;
                    margin-left: 10px;
                    opacity: 0.7;
                }

                .alert-close:hover {
                    opacity: 1;
                }
            `;
            document.head.appendChild(animationStyles);
        }
    },

    // --- Главный метод инициализации --- //

    /**
     * Инициализирует все компоненты приложения после загрузки DOM.
     */
    init() {
        // Создаем глобальный объект
        window.TradeHub = this;

        // Инициализируем стили
        this.initStyles();

        // Инициализируем все компоненты
        this.initTheme();
        this.initNotifications();
        this.initBoostButtons();
        this.initFollowButton(); // Добавлен вызов инициализации кнопки подписки
        this.initFilterButtons();
        this.initMobileMenu();
        this.initSmoothScrolling();
        this.initFormValidation();
        this.initWelcomeModal();
        this.initScrollAnimations();

        console.log('TradeHub UI Initialized');
    }
};

// --- Запуск приложения --- //
document.addEventListener('DOMContentLoaded', () => {
    TradeHub.init();
});