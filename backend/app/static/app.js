const CACHE_NAME = 'cerebro-v4';
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
        this.setupAuth();

        if (this.token) {
            this.hideLogin();
            this.refreshData();
        } else {
            this.switchView('inicio'); // Default view when login is active but background is hidden
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
        }
    }

    loadStatistics() {
        console.log('Loading statistics...');
        // Placeholder for future logic
    }

    setupModal() {
        const fab = document.getElementById('fab-add');
        const modal = document.getElementById('modal-add');
        const close = document.getElementById('btn-close-modal');
        const detailModal = document.getElementById('modal-detail');
        const detailClose = document.getElementById('btn-close-detail');
        const statsModal = document.getElementById('modal-stats-detail');
        const statsClose = document.getElementById('btn-close-stats');
        const commModal = document.getElementById('modal-add-commitment');
        const commClose = document.getElementById('btn-close-commitment');

        if (fab) {
            fab.addEventListener('click', () => {
                if (this.currentView === 'compromisos') {
                    commModal.classList.add('active');
                } else {
                    modal.classList.add('active');
                }
            });
        }

        if (close) close.addEventListener('click', () => modal.classList.remove('active'));
        if (detailClose) detailClose.addEventListener('click', () => detailModal.classList.remove('active'));
        if (statsClose) statsClose.addEventListener('click', () => statsModal.classList.remove('active'));
        if (commClose) commClose.addEventListener('click', () => commModal.classList.remove('active'));

        window.addEventListener('click', (e) => {
            if (e.target === modal) modal.classList.remove('active');
            if (e.target === detailModal) detailModal.classList.remove('active');
            if (e.target === statsModal) statsModal.classList.remove('active');
            if (e.target === commModal) commModal.classList.remove('active');
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
        if (overlay) overlay.classList.add('active');
    }

    hideLogin() {
        const overlay = document.getElementById('login-overlay');
        if (overlay) overlay.classList.remove('active');
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
        const user = data.user_name || "Christian";
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
                    <div class="subcat-actions" style="display: flex; gap: 6px;">
                        <button class="btn-edit-cat" data-sec="${sectionName}" data-cat="${catName}" 
                            style="background:#f1f5f9; border:1px solid #cbd5e1; padding: 6px 8px; border-radius: 6px; color:var(--primary); cursor:pointer; font-size:0.75rem; font-weight: 700; display: flex; align-items:center; gap:3px;">
                            ✏️ VER
                        </button>
                        <button class="btn-delete-cat" data-sec="${sectionName}" data-cat="${catName}" 
                            style="background:#fee2e2; border:1px solid #fecaca; padding: 6px; border-radius: 6px; color:#ef4444; cursor:pointer; font-size:0.9rem;">
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
                return;
            }

            const totalBudget = this.dashboardData.monthly_budget;
            const available = this.dashboardData.available_balance;
            const totalSpent = totalBudget - available;
            const percent = totalBudget > 0 ? (totalSpent / totalBudget) * 100 : 0;

            const canvasContainer = document.createElement('div');
            canvasContainer.style.height = '150px';
            canvasContainer.style.width = '100%';
            canvasContainer.innerHTML = '<canvas id="statsChart"></canvas>';
            content.appendChild(canvasContainer);

            modal.classList.add('active');

            setTimeout(() => {
                const ctx = document.getElementById('statsChart').getContext('2d');
                new Chart(ctx, {
                    type: 'bar',
                    data: {
                        labels: ['Gastado', 'Disponible'],
                        datasets: [{
                            label: 'Salud Financiera',
                            data: [totalSpent, available],
                            backgroundColor: ['#ef4444', '#10b981'],
                            borderRadius: 10
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
            }, 100);
            return;
        } else if (type === 'prediction') {
            if (!this.dashboardData) {
                content.innerHTML = '<p class="placeholder-text">Sin datos disponibles.</p>';
            } else {
                const totalBudget = this.dashboardData.monthly_budget;
                const totalSpent = totalBudget - this.dashboardData.available_balance;
                const dailyAvg = new Date().getDate() > 0 ? totalSpent / new Date().getDate() : 0;
                content.innerHTML = `<p class="placeholder-text">Proyección: $${Math.round(dailyAvg * 30).toLocaleString()}</p>`;
            }
        }
        modal.classList.add('active');
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
        const payload = {
            title: document.getElementById('comm-title').value,
            type: document.querySelector('input[name="comm-type"]:checked').value,
            total_amount: parseInt(document.getElementById('comm-amount').value),
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
                document.getElementById('modal-add-commitment').classList.remove('active');
                await this.loadCompromisos();
            }
        } catch (error) { console.error(error); }
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
                await this.refreshData();
            }
        } catch (e) { console.error(e); }
    }

    async handleUpdateCategory(section, category, currentBudget) {
        console.log(`[ACTION] Update Category: ${section}/${category}`);
        // Small delay to ensure browser focus
        setTimeout(async () => {
            const newBudgetStr = prompt(`Nuevo presupuesto para "${category}":`, currentBudget);
            if (newBudgetStr === null || newBudgetStr.trim() === "") {
                console.log("[ACTION] Update cancelled or empty");
                return;
            }

            const newBudget = parseInt(newBudgetStr.trim());
            if (isNaN(newBudget)) {
                alert('⚠️ Monto no válido. Ingrese solo números.');
                return;
            }

            try {
                const response = await fetch(`${CONFIG.API_BASE}/expenses/categories/`, {
                    method: 'PATCH',
                    headers: { ...this.getHeaders(), 'Content-Type': 'application/json' },
                    body: JSON.stringify({ section, category, new_budget: newBudget })
                });
                if (response.ok) {
                    alert('✅ Presupuesto actualizado');
                    await this.refreshData();
                    document.getElementById('modal-detail').classList.remove('active');
                } else {
                    const err = await response.json();
                    alert(`❌ Error del servidor: ${err.detail || 'No se pudo actualizar'}`);
                }
            } catch (e) {
                console.error("[ACTION] Update failed:", e);
                alert('⚠️ Error de red. Intenta de nuevo.');
            }
        }, 300);
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
