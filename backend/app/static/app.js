const CACHE_NAME = 'cerebro-v3.0.14';
const CONFIG = {
    // Dynamically use the current hostname. 
    // If running on localhost (dev), assume port 8001. 
    // If running in production (Railway), use relative path (same origin).
    API_BASE: window.location.hostname === '127.0.0.1' || window.location.hostname === 'localhost'
        ? `http://${window.location.hostname}:8001/api/v1`
        : `/api/v1`,
};

class FinanceApp {
    constructor() {
        this.currentView = 'inicio';
        this.token = localStorage.getItem('auth_token');
        this.sectionsData = {};
        this.dashboardData = null;
        this.commitments = [];
        this.init();
    }

    /* REMOVED MUTATION OBSERVER TO PPREVENT FREEZE */

    toggleBodyModal(isOpen) {
        if (isOpen) {
            document.body.classList.add('body-modal-open');
            const fab = document.querySelector('.fab');
            if (fab) fab.style.display = 'none';
        } else {
            document.body.classList.remove('body-modal-open');
            const fab = document.querySelector('.fab');
            if (fab) fab.style.display = 'flex';
        }
    }

    getHeaders() {
        const headers = {};
        if (this.token) {
            headers['Authorization'] = `Bearer ${this.token}`;
        }
        return headers;
    }

    init() {
        this.setupNavigation();
        this.setupModal();
        this.setupCamera();
        this.setupForms();
        this.setupSettings();
        this.setupAuth();

        this.setupAuth();

        // FIX: Always activate the default view, otherwise screen is white if logged in
        this.switchView('inicio');

        if (this.token) {
            this.hideLogin();
            this.refreshData();
        } else {
            this.showLogin();
        }
    }

    async refreshData() {
        await this.loadDashboard();
        await this.loadExpenses();
        if (this.currentView === 'compromisos') {
            await this.loadCompromisos();
        }
    }

    setupNavigation() {
        const navItems = document.querySelectorAll('.nav-item');
        navItems.forEach(item => {
            item.addEventListener('click', () => {
                const view = item.dataset.view;
                this.switchView(view);
                navItems.forEach(ni => ni.classList.remove('active'));
                item.classList.add('active');
            });
        });
    }

    switchView(viewId) {
        document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
        const target = document.getElementById(`view-${viewId}`);
        if (target) {
            target.classList.add('active');
            this.currentView = viewId;

            // FAB Context Logic
            const fab = document.getElementById('fab-add');
            if (viewId === 'compromisos') {
                fab.querySelector('.label').textContent = 'Nuevo Compromiso';
                fab.querySelector('.icon').textContent = '🤝';
                this.loadCompromisos();
            } else {
                fab.querySelector('.label').textContent = 'Agregar Gasto';
                fab.querySelector('.icon').textContent = '+';
            }

            if (viewId === 'stats') {
                this.loadStatistics();
            }
            if (viewId === 'mas') {
                this.loadSettings();
            }
        }
    }

    loadSettings() {
        if (this.dashboardData) {
            const input = document.getElementById('global-budget-input');
            if (input) input.value = this.dashboardData.monthly_budget;
        }
        document.getElementById('app-version-display').textContent = CURRENT_VERSION;

        // Restore toggle states
        const themeToggle = document.getElementById('toggle-dark-mode');
        if (themeToggle) themeToggle.checked = localStorage.getItem('theme') === 'dark';

        const alertToggle = document.getElementById('toggle-smart-alerts');
        if (alertToggle) alertToggle.checked = localStorage.getItem('smart_alerts') !== 'false';
    }

    setupSettings() {
        // Dark Mode
        const themeToggle = document.getElementById('toggle-dark-mode');
        if (themeToggle) {
            // Check saved theme on load
            if (localStorage.getItem('theme') === 'dark') {
                document.body.classList.add('dark-mode');
                themeToggle.checked = true;
            }

            themeToggle.addEventListener('change', (e) => {
                if (e.target.checked) {
                    document.body.classList.add('dark-mode');
                    localStorage.setItem('theme', 'dark');
                } else {
                    document.body.classList.remove('dark-mode');
                    localStorage.setItem('theme', 'light');
                }
            });
        }

        // Other Toggles (Mock persistence)
        const alertToggle = document.getElementById('toggle-smart-alerts');
        if (alertToggle) {
            alertToggle.addEventListener('change', (e) => {
                localStorage.setItem('smart_alerts', e.target.checked);
            });
        }

        const autoCatToggle = document.getElementById('toggle-auto-cat');
        if (autoCatToggle) {
            autoCatToggle.addEventListener('change', (e) => {
                localStorage.setItem('auto_cat', e.target.checked);
            });
        }

        // Hard Reset Button
        const btnReset = document.getElementById('btn-hard-reset');
        if (btnReset) {
            btnReset.addEventListener('click', async () => {
                if (confirm('¿Seguro que quieres borrar todos los datos locales y reiniciar la app? Esto solucionará problemas de actualización.')) {
                    // 1. Unregister SW
                    if ('serviceWorker' in navigator) {
                        const registrations = await navigator.serviceWorker.getRegistrations();
                        for (let registration of registrations) {
                            await registration.unregister();
                        }
                    }
                    // 2. Clear Storage
                    localStorage.clear();
                    sessionStorage.clear();

                    // 3. Reload from server
                    window.location.reload(true);
                }
            });
        }
    }

    async handleUpdateBudget() {
        const input = document.getElementById('global-budget-input');
        const val = parseInt(input.value);
        if (!val || val <= 0) return alert('⚠️ Ingresa un monto válido');

        const btn = document.getElementById('btn-save-budget');
        btn.textContent = 'Guardando...';
        btn.disabled = true;

        try {
            const response = await fetch(`${CONFIG.API_BASE}/expenses/budget`, {
                method: 'POST',
                headers: { ...this.getHeaders(), 'Content-Type': 'application/json' },
                body: JSON.stringify({ new_budget: val })
            });

            if (response.ok) {
                alert('✅ ¡Presupuesto actualizado!');
                await this.refreshData();
            } else {
                const err = await response.json();
                alert(`❌ Error: ${err.detail || 'No se pudo actualizar'}`);
            }
        } catch (e) {
            console.error(e);
            alert(`⚠️ Error de conexión: ${e.message}`);
        } finally {
            btn.textContent = 'Guardar Nuevo Presupuesto';
            btn.disabled = false;
        }
    }

    loadStatistics() {
        console.log('Loading statistics dashboard...');
        const container = document.getElementById('stats-main-chart-container');
        if (!container || !this.dashboardData) return;

        container.innerHTML = '<canvas id="mainDashboardChart"></canvas>';

        const totalBudget = this.dashboardData.monthly_budget;
        const available = this.dashboardData.available_balance;
        const totalSpent = totalBudget - available;

        setTimeout(() => {
            const ctx = document.getElementById('mainDashboardChart').getContext('2d');
            new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: ['Gastado', 'Disponible'],
                    datasets: [{
                        data: [totalSpent, available],
                        backgroundColor: ['#ef4444', '#10b981'],
                        borderWidth: 0,
                        hoverOffset: 4
                    }]
                },
                options: {
                    cutout: '70%',
                    responsive: true,
                    maintainAspectRatio: false,
                    layout: {
                        padding: { top: 10, bottom: 10 }
                    },
                    plugins: {
                        legend: { position: 'bottom', labels: { font: { family: 'Outfit', size: 11, weight: 'bold' }, padding: 15 } }
                    }
                }
            });
        }, 100);
    }

    setupModal() {
        const fab = document.getElementById('fab-add');
        const modal = document.getElementById('modal-add');
        const detailModal = document.getElementById('modal-detail');
        const statsModal = document.getElementById('modal-stats-detail');
        const commModal = document.getElementById('modal-add-commitment');

        if (fab) {
            fab.addEventListener('click', () => {
                if (this.currentView === 'compromisos') {
                    commModal.classList.add('active');
                } else {
                    modal.classList.add('active');
                }
                this.toggleBodyModal(true);
            });
        }

        const closeBtns = document.querySelectorAll('.btn-close');
        closeBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                btn.closest('.modal').classList.remove('active');
                this.toggleBodyModal(false);
            });
        });

        // Close when clicking outside content
        document.querySelectorAll('.modal').forEach(m => {
            m.addEventListener('click', (e) => {
                if (e.target === m) {
                    m.classList.remove('active');
                    this.toggleBodyModal(false);
                }
            });
        });
    }

    setupCamera() {
        const btnCamera = document.getElementById('btn-camera');
        const inputUpload = document.getElementById('image-upload');
        if (btnCamera && inputUpload) {
            btnCamera.addEventListener('click', () => inputUpload.click());
            inputUpload.addEventListener('change', (e) => {
                if (e.target.files.length > 0) btnCamera.textContent = '✅ Boleta Adjunta';
            });
        }
    }

    setupForms() {
        const form = document.getElementById('expense-form');
        const sectionSelect = document.getElementById('section-select');
        const commForm = document.getElementById('commitment-form');
        const budgetBtn = document.getElementById('btn-save-budget');

        if (sectionSelect) {
            sectionSelect.addEventListener('change', () => this.updateSubcategories());
        }

        if (form) {
            form.addEventListener('submit', async (e) => {
                e.preventDefault();
                await this.handleExpenseSubmit();
            });
        }

        if (commForm) {
            commForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                await this.handleCommitmentSubmit();
            });
        }

        if (budgetBtn) {
            budgetBtn.addEventListener('click', async () => await this.handleUpdateBudget());
        }

        const btnSaveEdit = document.getElementById('btn-save-edit-cat');
        if (btnSaveEdit) {
            btnSaveEdit.addEventListener('click', async () => await this.submitEditCategory());
        }
    }

    setupAuth() {
        const loginForm = document.getElementById('login-form');
        if (loginForm) {
            loginForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                await this.handleLogin();
            });
        }
    }

    showLogin() {
        const overlay = document.getElementById('login-overlay');
        if (overlay) {
            overlay.classList.add('active');
            this.toggleBodyModal(true);
        }
    }

    hideLogin() {
        const overlay = document.getElementById('login-overlay');
        if (overlay) {
            overlay.classList.remove('active');
            this.toggleBodyModal(false);
        }
    }

    async handleLogin() {
        const email = document.getElementById('login-email').value;
        const password = document.getElementById('login-password').value;
        const remember = document.getElementById('login-remember').checked;
        const errorDiv = document.getElementById('login-error');
        const btn = document.getElementById('btn-login');

        btn.disabled = true;
        btn.textContent = 'Cargando...';
        errorDiv.textContent = '';

        try {
            const formData = new FormData();
            formData.append('username', email);
            formData.append('password', password);

            const response = await fetch(`${CONFIG.API_BASE}/auth/login`, {
                method: 'POST',
                body: formData
            });

            if (response.ok) {
                const data = await response.json();
                this.token = data.access_token;
                if (remember) {
                    localStorage.setItem('auth_token', this.token);
                }
                this.hideLogin();
                await this.refreshData();
            } else {
                errorDiv.textContent = 'Credenciales inválidas';
            }
        } catch (error) {
            console.error('Login error:', error);
            errorDiv.textContent = 'Error de conexión';
        } finally {
            btn.disabled = false;
            btn.textContent = 'Entrar';
        }
    }

    async loadDashboard() {
        try {
            const response = await fetch(`${CONFIG.API_BASE}/expenses/dashboard`, {
                headers: this.getHeaders()
            });
            if (response.ok) {
                const data = await response.json();
                this.dashboardData = data;
                this.renderDashboard(data);
            } else if (response.status === 401) {
                this.showLogin();
            } else {
                document.getElementById('sync-time').textContent = `Err ${response.status}`;
            }
        } catch (error) {
            console.error('Error loading dashboard:', error);
            document.getElementById('sync-time').textContent = "Err Conexión";
        }
    }

    renderDashboard(data) {
        const user = data.user_name || "Usuario";
        const greeting = document.getElementById('greeting-text');
        if (greeting) greeting.textContent = `Hola, ${user} 👋`;

        const balance = document.getElementById('available-balance');
        if (balance) balance.textContent = `$${data.available_balance.toLocaleString()}`;

        const budget = document.getElementById('total-budget');
        if (budget) budget.textContent = `$${data.monthly_budget.toLocaleString()}`;

        const syncTime = document.getElementById('sync-time');
        if (syncTime) syncTime.textContent = new Date().toLocaleTimeString();

        const container = document.getElementById('categories-container');
        if (!container) return;
        container.innerHTML = '';

        this.sectionsData = data.categories;
        this.updateModalCategories();

        Object.entries(data.categories).forEach(([name, sec]) => {
            const percent = sec.budget > 0 ? (sec.spent / sec.budget) * 100 : 0;
            const remaining = sec.budget - sec.spent;
            const isOver = remaining < 0;
            const barColor = percent >= 90 ? 'red' : (percent >= 70 ? 'orange' : 'green');
            const icon = this.getIconForSection(name);

            const card = document.createElement('div');
            card.className = 'category-card';
            card.innerHTML = `
                <div class="cat-header">
                    <span class="cat-icon">${icon}</span>
                    <span class="cat-title">${name}</span>
                </div>
                <div class="cat-values">
                    $${sec.spent.toLocaleString()} / $${sec.budget.toLocaleString()} ${!isOver ? `(${percent.toFixed(1)}%)` : ''}
                    ${isOver ? '<span class="over-alert">⚠️ Te pasaste!</span>' : ''}
                </div>
                <div class="progress-container">
                    <div class="progress-bar ${barColor}" style="width: ${Math.min(percent, 100)}%"></div>
                </div>
                <div class="cat-remaining" style="color: ${isOver ? 'var(--danger)' : 'var(--text-muted)'}">
                    ${isOver ? `Excedido por $${Math.abs(remaining).toLocaleString()}` : `Queda $${remaining.toLocaleString()}`}
                </div>
            `;
            card.addEventListener('click', () => this.showCategoryDetail(name));
            container.appendChild(card);
        });

        const addCard = document.createElement('div');
        addCard.className = 'category-card';
        addCard.style.cssText = 'border: 2px dashed #cbd5e1; justify-content: center; align-items: center; cursor: pointer; background: rgba(255,255,255,0.5);';
        addCard.innerHTML = `
            <div style="font-size: 2rem; color: #94a3b8;">+</div>
            <div style="font-size: 0.9rem; color: #94a3b8; font-weight: 500;">Nueva Sección</div>
        `;
        addCard.addEventListener('click', () => this.handleAddSection());
        container.appendChild(addCard);
    }

    getIconForSection(name) {
        const n = name.toUpperCase();
        if (n.includes('COMIDA') || n.includes('FOOD') || n.includes('ALMUERZO')) return '🍕';
        if (n.includes('CASA') || n.includes('HOME') || n.includes('ARRIENDO')) return '🏠';
        if (n.includes('TRANSPORTE') || n.includes('UBER') || n.includes('AUTO') || n.includes('BENCINA')) return '🚗';
        if (n.includes('VICIO') || n.includes('ALCOHOL') || n.includes('FIESTA')) return '🎉';
        if (n.includes('STREAM') || n.includes('NETFLIX') || n.includes('SPOTIFY')) return '📺';
        if (n.includes('SALUD') || n.includes('FARMACIA') || n.includes('DOCTOR')) return '💊';
        if (n.includes('MASCOTA') || n.includes('PERRO') || n.includes('GATO') || n.includes('VET')) return '🐶';
        if (n.includes('ROP') || n.includes('ZAPAT') || n.includes('VESTIMENTA')) return '👕';
        if (n.includes('DEUDA') || n.includes('CREDITO') || n.includes('PRESTAMO')) return '💸';
        if (n.includes('EDUCACION') || n.includes('CURSO') || n.includes('U')) return '🎓';
        if (n.includes('VIAJE') || n.includes('VACACION')) return '✈️';
        if (n.includes('SUPER') || n.includes('MERCADO')) return '🛒';
        if (n.includes('SEGUR') || n.includes('SEGURO')) return '🛡️';
        return '📦';
    }

    showCategoryDetail(sectionName) {
        const sec = this.sectionsData[sectionName];
        if (!sec) return;

        const modal = document.getElementById('modal-detail');
        const title = document.getElementById('detail-title');
        const spentVal = document.getElementById('detail-spent');
        const budgetVal = document.getElementById('detail-budget');
        const progressBar = document.getElementById('detail-progress-bar');
        const subList = document.getElementById('detail-subcategories');
        const iconContainer = document.getElementById('detail-icon');

        const percent = sec.budget > 0 ? (sec.spent / sec.budget) * 100 : 0;

        title.textContent = sectionName;
        iconContainer.textContent = this.getIconForSection(sectionName);
        spentVal.innerHTML = `$${sec.spent.toLocaleString()} ${percent <= 100 ? `(${percent.toFixed(1)}%)` : ''} ${sec.spent > sec.budget ? '<span class="over-alert small">🚨</span>' : ''}`;
        budgetVal.textContent = `$${sec.budget.toLocaleString()}`;

        progressBar.style.width = `${Math.min(percent, 100)}%`;
        progressBar.className = `progress-bar ${percent >= 90 ? 'red' : (percent >= 70 ? 'orange' : 'green')}`;

        subList.innerHTML = '';
        Object.entries(sec.categories).forEach(([catName, catData]) => {
            const item = document.createElement('div');
            item.className = 'subcat-item';
            const catPercent = catData.budget > 0 ? (catData.spent / catData.budget) * 100 : 0;
            const remaining = catData.budget - catData.spent;
            const isOver = remaining < 0;
            const barColor = catPercent >= 90 ? 'red' : (catPercent >= 70 ? 'orange' : 'green');

            item.innerHTML = `
                <div class="subcat-header-row">
                    <h4 style="font-size: 1rem;">${catName}</h4>
                    <div class="subcat-actions" style="display: flex; gap: 10px;">
                        <button class="btn-edit-cat" data-sec="${sectionName}" data-cat="${catName}" 
                            style="background:#f1f5f9; border:1px solid #cbd5e1; padding: 8px 12px; border-radius: 8px; color:var(--primary); cursor:pointer; font-size:0.8rem; font-weight: 700; display: flex; align-items:center; gap:5px;">
                            ✏️ EDITAR
                        </button>
                        <button class="btn-delete-cat" data-sec="${sectionName}" data-cat="${catName}" 
                            style="background:#fee2e2; border:1px solid #fecaca; padding: 8px 12px; border-radius: 8px; color:#ef4444; cursor:pointer; font-size:0.8rem;">
                            🗑️
                        </button>
                    </div>
                </div>
                 <div class="subcat-header-row">
                    <span class="subcat-values" style="font-size: 0.9rem; color: var(--text-main); font-weight: 500;">
                        $${catData.spent.toLocaleString()} / $${catData.budget.toLocaleString()} ${!isOver ? `(${catPercent.toFixed(1)}%)` : ''}
                        ${isOver ? '<span class="over-alert small">⚠️</span>' : ''}
                    </span>
                </div>
                <div class="progress-container small">
                    <div class="progress-bar ${barColor}" style="width: ${Math.min(catPercent, 100)}%"></div>
                </div>
                <div class="subcat-footer-row" style="color: ${isOver ? 'var(--danger)' : 'var(--text-muted)'}">
                     ${isOver ? `Excedido por $${Math.abs(remaining).toLocaleString()}` : `Queda $${remaining.toLocaleString()}`}
                </div>
            `;

            const delBtn = item.querySelector('.btn-delete-cat');
            delBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.handleDeleteCategory(sectionName, catName);
            });

            const editBtn = item.querySelector('.btn-edit-cat');
            editBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.handleUpdateCategory(sectionName, catName, catData.budget);
            });

            subList.appendChild(item);
        });

        const addBtn = document.createElement('button');
        addBtn.className = 'btn-add-cat';
        addBtn.textContent = '+ Agregar Subcategoría';
        addBtn.style.cssText = 'width: 100%; padding: 12px; margin-top: 15px; background: #f1f5f9; border: 1px dashed #cbd5e1; border-radius: 8px; color: var(--text-main); font-weight: 500; cursor: pointer;';
        addBtn.addEventListener('click', () => this.handleAddCategory(sectionName));
        subList.appendChild(addBtn);

        const delSecBtn = document.createElement('button');
        delSecBtn.textContent = '⚠️ Eliminar Sección Completa';
        delSecBtn.style.cssText = 'width: 100%; padding: 10px; margin-top: 20px; background: none; border: 1px solid #fee2e2; border-radius: 8px; color: #ef4444; font-size: 0.8rem; cursor: pointer;';
        delSecBtn.addEventListener('click', () => this.handleDeleteSection(sectionName));
        subList.appendChild(delSecBtn);

        modal.classList.add('active');
        this.toggleBodyModal(true);
    }

    showStatDetail(type) {
        const modal = document.getElementById('modal-stats-detail');
        const title = document.getElementById('stats-detail-title');
        const icon = document.getElementById('stats-detail-icon');
        const content = document.getElementById('stats-detail-content');

        const configs = {
            'general': { title: 'Indicadores Generales', icon: '⚡' },
            'prediction': { title: 'Predicción de Gastos', icon: '🔮' },
            'comparison': { title: 'Comparación Mensual', icon: '⚖️' },
            'savings': { title: 'Proyección Ahorro', icon: '🐖' }
        };

        const config = configs[type];
        if (!config) return;

        title.textContent = config.title;
        icon.textContent = config.icon;
        content.innerHTML = '';

        if (type === 'general') {
            if (!this.dashboardData) {
                content.innerHTML = '<p class="placeholder-text">Sin datos disponibles.</p>';
                modal.classList.add('active');
                this.toggleBodyModal(true);
                return;
            }

            const totalBudget = this.dashboardData.monthly_budget;
            const totalSpent = totalBudget - this.dashboardData.available_balance;
            const available = this.dashboardData.available_balance;

            const barContainer = document.createElement('div');
            barContainer.style.height = '120px';
            barContainer.style.width = '100%';
            barContainer.style.marginBottom = '20px';
            barContainer.innerHTML = '<canvas id="statsChartBar"></canvas>';
            content.appendChild(barContainer);

            const pieContainer = document.createElement('div');
            pieContainer.style.height = '180px';
            pieContainer.style.width = '100%';
            pieContainer.style.marginTop = '10px';
            pieContainer.innerHTML = '<canvas id="statsChartPie"></canvas>';
            pieContainer.style.borderTop = '1px solid #f1f5f9';
            pieContainer.style.paddingTop = '15px';
            content.appendChild(pieContainer);

            modal.classList.add('active');
            this.toggleBodyModal(true);

            setTimeout(() => {
                // 1. Bar Chart (Spent vs Available)
                const ctxBar = document.getElementById('statsChartBar').getContext('2d');
                new Chart(ctxBar, {
                    type: 'bar',
                    data: {
                        labels: ['Gastado', 'Disponible'],
                        datasets: [{
                            data: [totalSpent, available],
                            backgroundColor: ['#ef4444', '#10b981'],
                            borderRadius: 6
                        }]
                    },
                    options: {
                        indexAxis: 'y',
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: { legend: { display: false } },
                        scales: { x: { beginAtZero: true } }
                    }
                });

                // 2. Pie Chart (Spending by Section)
                const ctxPie = document.getElementById('statsChartPie').getContext('2d');
                const secLabels = Object.keys(this.sectionsData);
                const secSpent = Object.values(this.sectionsData).map(s => s.spent);

                new Chart(ctxPie, {
                    type: 'pie',
                    data: {
                        labels: secLabels,
                        datasets: [{
                            data: secSpent,
                            backgroundColor: ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4'],
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: { position: 'right', labels: { font: { family: 'Outfit', size: 9 } } }
                        }
                    }
                });
            }, 100);
            return;
        } else if (type === 'prediction') {
            if (!this.dashboardData) {
                content.innerHTML = '<p class="placeholder-text">Sin datos disponibles.</p>';
            } else {
                const totalBudget = this.dashboardData.monthly_budget;
                const available = this.dashboardData.available_balance;
                const totalSpent = totalBudget - available;

                const now = new Date();
                const currentDay = now.getDate();
                const totalDays = new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate();
                const daysRemaining = totalDays - currentDay;

                // 1. Daily Average so far
                const dailyAvg = currentDay > 0 ? totalSpent / currentDay : 0;

                // 2. Projected Finish
                const projectedSpent = (dailyAvg * totalDays);
                const projectedBalance = totalBudget - projectedSpent;
                const isProjectedOver = projectedBalance < 0;

                // 3. Recommended Daily (to match budget)
                const recommendedDaily = daysRemaining > 0 && available > 0 ? available / daysRemaining : 0;

                content.innerHTML = `
                    <div class="stat-detail-card">
                        <div class="projection-header" style="text-align: center; margin-bottom: 25px;">
                            <p style="color: var(--text-muted); font-size: 0.9rem; margin-bottom: 5px;">Proyección Cierre de Mes</p>
                            <h2 style="font-size: 2.2rem; color: ${isProjectedOver ? '#ef4444' : '#10b981'}; font-weight: 700;">
                                $${projectedSpent.toLocaleString()}
                            </h2>
                            <p style="font-size: 0.85rem; color: ${isProjectedOver ? '#ef4444' : '#10b981'}; background: ${isProjectedOver ? '#fee2e2' : '#d1fae5'}; display: inline-block; padding: 4px 12px; border-radius: 20px; margin-top: 5px;">
                                ${isProjectedOver ? `Excedido por $${Math.abs(projectedBalance).toLocaleString()}` : `Ahorro posible: $${projectedBalance.toLocaleString()}`}
                            </p>
                        </div>

                        <div class="projection-stats" style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                            <div class="p-stat-box" style="background: #f8fafc; padding: 15px; border-radius: 12px; text-align: center;">
                                <div style="font-size: 1.5rem; margin-bottom: 5px;">📅</div>
                                <div style="font-size: 0.8rem; color: var(--text-muted);">Gasto Diario Actual</div>
                                <div style="font-weight: 600; font-size: 1.1rem; color: var(--text-main);">$${Math.round(dailyAvg).toLocaleString()}</div>
                            </div>
                            <div class="p-stat-box" style="background: #f0fdf4; padding: 15px; border-radius: 12px; text-align: center; border: 1px solid #bbf7d0;">
                                <div style="font-size: 1.5rem; margin-bottom: 5px;">🎯</div>
                                <div style="font-size: 0.8rem; color: #15803d;">Meta Diaria Restante</div>
                                <div style="font-weight: 600; font-size: 1.1rem; color: #15803d;">$${Math.round(recommendedDaily).toLocaleString()}</div>
                            </div>
                        </div>

                        <div class="projection-note" style="margin-top: 25px; font-size: 0.85rem; color: var(--text-muted); text-align: center; line-height: 1.5;">
                            ${daysRemaining} días restantes. <br>
                            ${dailyAvg > recommendedDaily ? '⚠️ Estás gastando más de lo recomendado.' : '✅ Estás bajo la meta diaria. ¡Bien hecho!'}
                        </div>
                    </div>
                `;
            }
        }
        modal.classList.add('active');
        this.toggleBodyModal(true);
    }

    updateModalCategories() {
        const sectionSelect = document.getElementById('section-select');
        if (!sectionSelect) return;
        const currentSec = sectionSelect.value;
        sectionSelect.innerHTML = '<option value="">Selecciona Sección...</option>';
        Object.keys(this.sectionsData).forEach(sec => {
            const opt = document.createElement('option');
            opt.value = sec;
            opt.textContent = sec;
            sectionSelect.appendChild(opt);
        });
        if (currentSec) sectionSelect.value = currentSec;
        this.updateSubcategories();
    }

    updateSubcategories() {
        const sectionSelect = document.getElementById('section-select');
        const categorySelect = document.getElementById('category');
        const selectedSec = sectionSelect.value;
        categorySelect.innerHTML = '<option value="">Selecciona Categoría...</option>';
        if (selectedSec && this.sectionsData[selectedSec]) {
            Object.keys(this.sectionsData[selectedSec].categories).forEach(cat => {
                const opt = document.createElement('option');
                opt.value = cat;
                opt.textContent = cat;
                categorySelect.appendChild(opt);
            });
        }
    }

    async loadExpenses() {
        try {
            const response = await fetch(`${CONFIG.API_BASE}/expenses/`, {
                headers: this.getHeaders()
            });
            if (response.ok) {
                const expenses = await response.json();
                this.renderExpenses(expenses);
            }
        } catch (error) {
            console.error('Error loading expenses:', error);
        }
    }

    renderExpenses(expenses) {
        const list = document.getElementById('expense-list');
        if (!list) return;
        list.innerHTML = '';
        const icons = { 'COMIDAS': '🍕', 'TRANSPORTE': '🚗', 'VICIOS': '🎉', 'OTROS': '📦' };
        expenses.slice(0, 5).forEach(exp => {
            const item = document.createElement('div');
            item.className = 'expense-item';

            // Try to find section from dashboard data if missing
            let section = exp.section || "OTROS";
            const icon = icons[section] || '💰';
            const payMethod = exp.payment_method ? ` • ${exp.payment_method}` : '';

            item.innerHTML = `
                <div class="exp-icon-box">${icon}</div>
                <div class="exp-details">
                    <h4>${exp.concept}</h4>
                    <p>${new Date(exp.date).toLocaleDateString()} • ${exp.category}${payMethod}</p>
                </div>
                <div class="exp-amount">$${exp.amount.toLocaleString()}</div>
            `;
            list.appendChild(item);
        });
    }

    async handleExpenseSubmit() {
        const btn = document.getElementById('btn-submit-expense');
        btn.disabled = true;
        btn.textContent = 'Guardando...';

        const formData = new FormData();
        formData.append('amount', document.getElementById('amount').value);
        formData.append('concept', document.getElementById('concept').value || '');
        formData.append('section', document.getElementById('section-select').value || '');
        formData.append('category', document.getElementById('category').value || '');
        formData.append('payment_method', document.getElementById('payment-method').value);
        const photo = document.getElementById('image-upload').files[0];
        if (photo) formData.append('image', photo);

        try {
            const response = await fetch(`${CONFIG.API_BASE}/expenses/`, {
                method: 'POST',
                headers: this.getHeaders(),
                body: formData
            });
            if (response.ok) {
                document.getElementById('modal-add').classList.remove('active');
                this.toggleBodyModal(false);
                document.getElementById('expense-form').reset();
                document.getElementById('btn-camera').textContent = '📸 Adjuntar Boleta';
                await this.refreshData();
            } else {
                alert('Fallo al guardar');
            }
        } catch (error) {
            console.error(error);
            alert('Error de conexión');
        } finally {
            btn.disabled = false;
            btn.textContent = 'Guardar';
        }
    }

    async loadCompromisos() {
        const list = document.getElementById('compromisos-list');
        if (!list) return;
        list.innerHTML = '<p class="placeholder-text">Cargando...</p>';
        try {
            const response = await fetch(`${CONFIG.API_BASE}/commitments/`, {
                headers: this.getHeaders()
            });
            if (response.ok) {
                const data = await response.json();
                this.commitments = data;
                this.renderCompromisos(data);
            }
        } catch (error) {
            console.error(error);
        }
    }

    renderCompromisos(data) {
        let totalDebt = 0, countDebt = 0, totalLoan = 0, countLoan = 0;
        data.forEach(c => {
            if (c.status !== 'PAID') {
                const rem = c.total_amount - c.paid_amount;
                if (c.type === 'DEBT') { totalDebt += rem; countDebt++; }
                else { totalLoan += rem; countLoan++; }
            }
        });

        // Update KPIs with higher visibility
        const debtAmtEl = document.getElementById('kpi-debt-amount');
        const debtCntEl = document.getElementById('kpi-debt-count');
        if (debtAmtEl) {
            debtAmtEl.textContent = `$${totalDebt.toLocaleString()}`;
            debtAmtEl.style.color = totalDebt > 0 ? 'var(--danger)' : 'var(--text-muted)';
        }
        if (debtCntEl) debtCntEl.textContent = `${countDebt} items`;

        const loanAmtEl = document.getElementById('kpi-loan-amount');
        const loanCntEl = document.getElementById('kpi-loan-count');
        if (loanAmtEl) {
            loanAmtEl.textContent = `$${totalLoan.toLocaleString()}`;
            loanAmtEl.style.color = totalLoan > 0 ? 'var(--accent)' : 'var(--text-muted)';
        }
        if (loanCntEl) loanCntEl.textContent = `${countLoan} items`;

        const balanceAmtEl = document.getElementById('kpi-total-balance');
        const balanceDetEl = document.getElementById('kpi-balance-detail');
        const balance = totalLoan - totalDebt;
        if (balanceAmtEl) {
            balanceAmtEl.textContent = `$${Math.abs(balance).toLocaleString()}`;
            balanceAmtEl.style.color = balance >= 0 ? 'var(--accent)' : 'var(--danger)';
        }
        if (balanceDetEl) {
            balanceDetEl.textContent = balance > 0 ? 'A favor' : (balance < 0 ? 'En contra' : 'Equilibrado');
        }

        const list = document.getElementById('compromisos-list');

        if (!list) return;
        list.innerHTML = '';
        data.forEach(c => {
            const item = document.createElement('div');
            item.className = `commitment-item ${c.status === 'PAID' ? 'paid-item' : ''}`;
            const isPaid = c.status === 'PAID';
            item.innerHTML = `
                <div class="commitment-icon">${c.type === 'DEBT' ? '🔴' : '🟢'}</div>
                <div class="commitment-details">
                    <div class="commitment-title" style="${isPaid ? 'text-decoration: line-through;' : ''}">${c.title}</div>
                    <div class="commitment-amount">$${c.total_amount.toLocaleString()}</div>
                </div>
                <div class="commitment-action">
                    <button class="btn-check" data-id="${c.id}">${isPaid ? '✅' : '⬜'}</button>
                </div>
            `;
            item.querySelector('.btn-check').addEventListener('click', () => this.toggleCommitmentStatus(c));
            list.appendChild(item);
        });
    }

    async toggleCommitmentStatus(commitment) {
        const newStatus = commitment.status === 'PENDING' ? 'PAID' : 'PENDING';
        try {
            const response = await fetch(`${CONFIG.API_BASE}/commitments/${commitment.id}`, {
                method: 'PATCH',
                headers: { ...this.getHeaders(), 'Content-Type': 'application/json' },
                body: JSON.stringify({ status: newStatus, paid_amount: newStatus === 'PAID' ? commitment.total_amount : 0 })
            });
            if (response.ok) await this.loadCompromisos();
        } catch (e) { console.error(e); }
    }

    async handleCommitmentSubmit() {
        const titleVal = document.getElementById('comm-title').value;
        const amountVal = document.getElementById('comm-amount').value;

        if (!titleVal || !amountVal) {
            alert('⚠️ Por favor completa el título y el monto.');
            return;
        }

        const payload = {
            title: titleVal,
            type: document.querySelector('input[name="comm-type"]:checked').value,
            total_amount: parseInt(amountVal),
            due_date: document.getElementById('comm-date').value || null,
            status: "PENDING"
        };

        try {
            const response = await fetch(`${CONFIG.API_BASE}/commitments/`, {
                method: 'POST',
                headers: { ...this.getHeaders(), 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            if (response.ok) {
                const resData = await response.json();
                // Alert with debug info
                alert(`✅ Compromiso guardado!\nID: ${resData.id}\nUserID: ${resData.user_id}`);

                document.getElementById('modal-add-commitment').classList.remove('active');
                this.toggleBodyModal(false);
                document.getElementById('commitment-form').reset(); // Clear form

                // Force reload of compromisos
                await this.loadCompromisos();
            } else {
                const err = await response.json();
                console.error("Server Error:", err); // Extra debug
                alert(`❌ Error al guardar: ${err.detail || 'Intenta de nuevo'}`);
            }
        } catch (error) {
            console.error(error);
            alert('⚠️ Error de conexión al guardar el compromiso.');
        }
    }

    async handleAddCategory(section) {
        const name = prompt(`Nueva categoría para ${section}:`);
        if (!name) return;
        const budget = parseInt(prompt(`Presupuesto:`, "0")) || 0;
        try {
            const response = await fetch(`${CONFIG.API_BASE}/expenses/categories/`, {
                method: 'POST',
                headers: { ...this.getHeaders(), 'Content-Type': 'application/json' },
                body: JSON.stringify({ section, category: name, budget })
            });
            if (response.ok) {
                document.getElementById('modal-detail').classList.remove('active');
                this.toggleBodyModal(false);
                await this.refreshData();
            }
        } catch (e) { console.error(e); }
    }

    openEditModal(section, category, currentBudget) {
        this.editTarget = { section, category };
        const modal = document.getElementById('modal-edit-budget');
        const nameEl = document.getElementById('edit-cat-name');
        const input = document.getElementById('edit-cat-amount');

        nameEl.textContent = `${category} (${section})`;
        input.value = currentBudget;

        modal.classList.add('active');
        this.toggleBodyModal(true);
        setTimeout(() => input.focus(), 100);
    }

    async submitEditCategory() {
        if (!this.editTarget) return;

        const input = document.getElementById('edit-cat-amount');
        const newBudget = parseInt(input.value);

        if (isNaN(newBudget) || newBudget < 0) {
            alert('⚠️ Ingresa un monto válido');
            return;
        }

        const btn = document.getElementById('btn-save-edit-cat');
        btn.textContent = 'Guardando...';
        btn.disabled = true;

        try {
            const { section, category } = this.editTarget;
            const response = await fetch(`${CONFIG.API_BASE}/expenses/categories/`, {
                method: 'PATCH',
                headers: { ...this.getHeaders(), 'Content-Type': 'application/json' },
                body: JSON.stringify({ section, category, new_budget: newBudget })
            });

            if (response.ok) {
                document.getElementById('modal-edit-budget').classList.remove('active');
                this.toggleBodyModal(false);
                await this.refreshData(); // This refreshes the detail modal too if logic supports it, or we need to close detail?
                // Actually refreshData refreshes dashboardData.
                // We should also close the detail modal to force user to re-open and see new data, or re-render detail.
                // For simplicity, let's close all modals or just refresh.
                // But wait, if Detail Modal is open, we need to update it.
                // Simplest: Close Edit Modal, and call showCategoryDetail again?
                // refreshData() updates this.sectionsData.
                // Then we need to re-render the detail view if it's open.
                if (document.getElementById('modal-detail').classList.contains('active')) {
                    this.showCategoryDetail(section);
                }
            } else {
                alert('❌ Error al actualizar');
            }
        } catch (e) {
            console.error(e);
            alert('Error de conexión');
        } finally {
            btn.textContent = 'Guardar Cambios';
            btn.disabled = false;
        }
    }

    // Old handleUpdateCategory replaced by openEditModal call
    handleUpdateCategory(section, category, currentBudget) {
        this.openEditModal(section, category, currentBudget);
    }

    async handleDeleteCategory(section, category) {
        if (!confirm(`¿Estás seguro de ELIMINAR "${category}"?`)) return;
        console.log(`[ACTION] Delete Category: ${section}/${category}`);

        try {
            const response = await fetch(`${CONFIG.API_BASE}/expenses/categories/`, {
                method: 'DELETE',
                headers: { ...this.getHeaders(), 'Content-Type': 'application/json' },
                body: JSON.stringify({ section, category })
            });
            if (response.ok) {
                alert('🗑️ Categoría eliminada');
                document.getElementById('modal-detail').classList.remove('active');
                this.toggleBodyModal(false);
                await this.refreshData();
            } else {
                const err = await response.json();
                alert(`❌ Error: ${err.detail || 'No se pudo borrar'}`);
            }
        } catch (e) {
            console.error(e);
            alert('⚠️ Error de conexión');
        }
    }

    async handleAddSection() {
        const name = prompt("Nombre Nueva Sección (ej: HOGAR):");
        // Prompt blocks execution, but technically doesn't open a DOM modal unless we used a custom one.
        // If using custom modal later, call toggleBodyModal(true).
        if (!name) return;
        const subCat = prompt("Nombre Primera Subcategoría (ej: Arriendo):");
        if (!subCat) return;
        const budget = parseInt(prompt("Monto Presupuesto para esta subcategoría:", "0")) || 0;
        try {
            const response = await fetch(`${CONFIG.API_BASE}/expenses/categories/`, {
                method: 'POST',
                headers: { ...this.getHeaders(), 'Content-Type': 'application/json' },
                body: JSON.stringify({ section: name.trim().toUpperCase(), category: subCat.trim(), budget })
            });
            if (response.ok) {
                await this.refreshData();
                alert('Sección creada con éxito');
            } else {
                alert('Fallo al crear sección');
            }
        } catch (e) { console.error(e); }
    }

    async handleDeleteSection(sectionName) {
        if (!confirm(`¿Eliminar Sección "${sectionName}"?`)) return;
        const subCats = Object.keys(this.sectionsData[sectionName].categories);
        for (const cat of subCats) {
            await fetch(`${CONFIG.API_BASE}/expenses/categories/`, {
                method: 'DELETE',
                headers: { ...this.getHeaders(), 'Content-Type': 'application/json' },
                body: JSON.stringify({ section: sectionName, category: cat })
            });
        }
        document.getElementById('modal-detail').classList.remove('active');
        await this.refreshData();
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.app = new FinanceApp();
});
