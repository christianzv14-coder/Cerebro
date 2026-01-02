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
        this.currentView = 'stats';
        this.commitments = [];
        this.init();
    }

    init() {
        this.setupNavigation();
        this.setupModal();
        this.setupCamera();
        this.setupForms();
        this.refreshData();
    }

    async refreshData() {
        await this.loadDashboard();
        await this.loadExpenses();
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
            this.currentView = viewId; // Update state

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

        fab.addEventListener('click', () => {
            if (this.currentView === 'compromisos') {
                commModal.classList.add('active');
            } else {
                modal.classList.add('active');
            }
        });

        close.addEventListener('click', () => modal.classList.remove('active'));

        if (detailClose) detailClose.addEventListener('click', () => detailModal.classList.remove('active'));
        if (statsClose) statsClose.addEventListener('click', () => statsModal.classList.remove('active'));
        if (commClose) commClose.addEventListener('click', () => commModal.classList.remove('active'));

        // Close on click outside
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
        btnCamera.addEventListener('click', () => inputUpload.click());
        inputUpload.addEventListener('change', (e) => {
            if (e.target.files.length > 0) btnCamera.textContent = '✅ Boleta Adjunta';
        });
    }

    setupForms() {
        const form = document.getElementById('expense-form');
        const sectionSelect = document.getElementById('section-select');

        sectionSelect.addEventListener('change', () => this.updateSubcategories());

        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            await this.handleExpenseSubmit();
        });

        const commForm = document.getElementById('commitment-form');
        if (commForm) {
            commForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                await this.handleCommitmentSubmit();
            });
        }
    }

    async loadDashboard() {
        try {
            const response = await fetch(`${CONFIG.API_BASE}/expenses/dashboard`);
            console.log('Dashboard Response Status:', response.status);
            if (response.ok) {
                const data = await response.json();
                this.dashboardData = data; // Store globally for stats
                this.renderDashboard(data);
            } else {
                const errorText = await response.text();
                console.error('Dashboard Fetch Failed:', response.status, errorText);
                document.getElementById('sync-time').textContent = `Err ${response.status}`;
            }
        } catch (error) {
            console.error('Error loading dashboard:', error);
            document.getElementById('sync-time').textContent = "Err Conexión";
        }
    }

    renderDashboard(data) {
        const user = data.user_name || "Carlos";
        document.getElementById('greeting-text').textContent = `Hola, ${user} 👋`;
        document.getElementById('available-balance').textContent = `$${data.available_balance.toLocaleString()}`;
        document.getElementById('total-budget').textContent = `$${data.monthly_budget.toLocaleString()}`;

        const now = new Date();
        document.getElementById('sync-time').textContent = now.toLocaleTimeString();

        const container = document.getElementById('categories-container');
        container.innerHTML = '';

        const icons = {
            'GASTOS FIJOS': '🏠',
            'COMIDAS': '🍕',
            'TRANSPORTE': '🚗',
            'VICIOS': '🎉',
            'STREAM/APP': '📺',
            'COMISIONES - SEGUROS': '🛡️',
            'OTROS': '📦'
        };

        // Cache categories for the modal
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

        // Add "New Section" Card
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
        return '📦'; // Default
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
                    <h4>${catName}</h4>
                     <button class="btn-delete-cat" data-sec="${sectionName}" data-cat="${catName}" style="background:none; border:none; color:#ef4444; cursor:pointer;" title="Borrar Categoría">
                        🗑️
                    </button>
                </div>
                 <div class="subcat-header-row">
                    <span class="subcat-values">
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

            // Delete Listener
            const delBtn = item.querySelector('.btn-delete-cat');
            delBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.handleDeleteCategory(sectionName, catName);
            });

            subList.appendChild(item);
        });

        // Add Category Button
        const addBtn = document.createElement('button');
        addBtn.className = 'btn-add-cat';
        addBtn.textContent = '+ Agregar Subcategoría';
        addBtn.style.cssText = 'width: 100%; padding: 12px; margin-top: 15px; background: #f1f5f9; border: 1px dashed #cbd5e1; border-radius: 8px; color: var(--text-main); font-weight: 500; cursor: pointer;';
        addBtn.addEventListener('click', () => this.handleAddCategory(sectionName));
        subList.appendChild(addBtn);

        // Delete Section Button (DANGER ZONE)
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
                content.innerHTML = '<p class="placeholder-text">Sin datos disponibles. Carga el inicio primero.</p>';
                modal.classList.add('active');
                return;
            }

            // --- INDICATOR 1: % Budget Used ---
            const totalBudget = this.dashboardData.monthly_budget;
            const available = this.dashboardData.available_balance;
            const totalSpent = totalBudget - available;

            const percent = totalBudget > 0 ? (totalSpent / totalBudget) * 100 : 0;

            let colorClass = 'green';
            let statusText = 'Vas dentro del plan.';

            if (percent >= 90) {
                colorClass = '#ef4444'; // Red
                statusText = 'Riesgo alto de sobrepaso.';
            } else if (percent >= 70) {
                colorClass = '#f59e0b'; // Orange
                statusText = 'El mes empieza a apretarse.';
            } else {
                colorClass = '#10b981'; // Green
            }

            const canvasContainer = document.createElement('div');
            canvasContainer.style.height = '200px';
            canvasContainer.style.width = '100%';
            canvasContainer.innerHTML = '<canvas id="kpiChart"></canvas>';

            const infoText = document.createElement('div');
            infoText.className = 'subcat-footer-row';
            infoText.style.cssText = 'color: var(--text-muted); text-align: center; margin-top: 15px; font-size: 0.9rem;';
            infoText.textContent = statusText;

            content.appendChild(canvasContainer);
            content.appendChild(infoText);

            // Initialize Chart
            const ctx = document.getElementById('kpiChart').getContext('2d');

            // Destroy existing chart if any (to prevent canvas reuse errors)
            if (this.currentChart) {
                this.currentChart.destroy();
            }

            this.currentChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: ['Gastado', 'Total Disponible'],
                    datasets: [{
                        label: 'Monto (CLP)',
                        data: [totalSpent, available], // Show Spent vs What is left? Or Spent vs Total Budget?
                        // Let's do a stacked single bar or just two bars.
                        // User wanted "% budget used".
                        // Best viz: Single bar with max val?
                        // Let's do a simple comparison: Spent vs Budget.
                        backgroundColor: [colorClass, '#e2e8f0'],
                        borderRadius: 10,
                        borderSkipped: false
                    }]
                },
                options: {
                    indexAxis: 'y', // Horizontal bar
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            callbacks: {
                                label: function (context) {
                                    return `$${context.raw.toLocaleString()}`;
                                }
                            }
                        }
                    },
                    scales: {
                        x: {
                            max: totalBudget * 1.1, // Gives some breathing room
                            grid: { display: false },
                            ticks: { display: false }
                        },
                        y: {
                            grid: { display: false }
                        }
                    }
                }
            });
            this.currentChart.data.labels = ['Gastado', 'Presupuesto'];
            this.currentChart.data.datasets[0].data = [totalSpent, totalBudget];
            this.currentChart.update();

            // --- INDICATOR 2: Spending Pace (Ritmo de Gasto) ---
            const now = new Date();
            const currentDay = now.getDate();
            const daysInMonth = new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate();
            const daysRemaining = daysInMonth - currentDay;

            // Avoid division by zero
            const dailyAverage = currentDay > 0 ? totalSpent / currentDay : 0;
            const dailyAllowed = daysRemaining > 0 ? available / daysRemaining : 0; // Available for remaining days

            let paceColor = '#10b981'; // Green
            let paceText = 'Ritmo de gasto saludable.';

            if (dailyAverage > dailyAllowed) {
                paceColor = '#ef4444'; // Red
                paceText = 'Estás gastando más rápido de lo recomendable.';
            }

            const paceCard = document.createElement('div');
            paceCard.className = 'subcat-item';
            paceCard.style.marginTop = '20px';
            paceCard.innerHTML = `
                <div class="subcat-header-row">
                    <h4>Ritmo de Gasto Diario</h4>
                    <span class="subcat-values">$${Math.round(dailyAverage).toLocaleString()} / $${Math.round(dailyAllowed).toLocaleString()} (max)</span>
                </div>
                <div style="height: 150px; width: 100%;">
                    <canvas id="paceChart"></canvas>
                </div>
                <div class="subcat-footer-row" style="color: var(--text-muted); text-align: left; margin-top: 10px;">
                     ${paceText}
                </div>
            `;
            content.appendChild(paceCard);

            const ctxPace = document.getElementById('paceChart').getContext('2d');

            if (this.paceChart) {
                this.paceChart.destroy();
            }

            this.paceChart = new Chart(ctxPace, {
                type: 'bar',
                data: {
                    labels: ['Promedio Real', 'Máximo Permitido'],
                    datasets: [{
                        label: 'Gasto Diario (CLP)',
                        data: [dailyAverage, dailyAllowed],
                        backgroundColor: [paceColor, '#e2e8f0'],
                        borderRadius: 8,
                        borderSkipped: false
                    }]
                },
                options: {
                    indexAxis: 'y',
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                        tooltip: { callbacks: { label: (c) => `$${Math.round(c.raw).toLocaleString()}` } }
                    },
                    scales: {
                        x: { grid: { display: false }, ticks: { display: false } },
                        y: { grid: { display: false } }
                    }
                }
            });

            // --- INDICATOR 3: Incidents (Incumplimientos) ---
            let incidents = 0;
            let totalSubCats = 0;
            let exceededNames = [];

            Object.values(this.dashboardData.categories).forEach(section => {
                if (section.categories) {
                    Object.entries(section.categories).forEach(([subName, subCat]) => {
                        totalSubCats++;
                        if (subCat.spent > subCat.budget) {
                            incidents++;
                            exceededNames.push(subName);
                        }
                    });
                }
            });

            let incColor = '#10b981'; // Green
            let incText = 'Buen control financiero.';

            if (incidents >= 2) {
                incColor = '#ef4444'; // Red
                incText = 'Patrón de desorden a revisar.';
            } else if (incidents === 1) {
                incColor = '#f59e0b'; // Orange
                incText = 'Desviación puntual.';
            }

            const incCard = document.createElement('div');
            incCard.className = 'subcat-item';
            incCard.style.marginTop = '20px';
            incCard.innerHTML = `
                <div class="subcat-header-row">
                    <h4>Incumplimientos del Mes</h4>
                    <span class="subcat-values" style="color: ${incColor}; font-weight: bold;">${incidents} incidente${incidents !== 1 ? 's' : ''}</span>
                </div>
                <div style="height: 200px; width: 100%; display: flex; justify-content: center;">
                    <canvas id="incidentsChart"></canvas>
                </div>
                <div class="subcat-footer-row" style="color: var(--text-muted); text-align: center; margin-top: 10px;">
                     ${incText}
                </div>
            `;
            content.appendChild(incCard);

            const ctxInc = document.getElementById('incidentsChart').getContext('2d');

            if (this.incChart) {
                this.incChart.destroy();
            }

            this.incChart = new Chart(ctxInc, {
                type: 'doughnut',
                data: {
                    labels: ['En Regla', 'Excedidas'],
                    datasets: [{
                        data: [totalSubCats - incidents, incidents],
                        backgroundColor: ['#10b981', incColor],
                        borderWidth: 0,
                        hoverOffset: 4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: '70%',
                    plugins: {
                        legend: { position: 'bottom' },
                        tooltip: {
                            callbacks: {
                                label: function (context) {
                                    const label = context.label || '';
                                    const value = context.raw || 0;
                                    if (label === 'Excedidas' && exceededNames.length > 0) {
                                        return [` ${value} Subcategorías:`, ...exceededNames.map(n => ` • ${n}`)];
                                    }
                                    return ` ${label}: ${value}`;
                                }
                            }
                        }
                    }
                }
            });



        } else if (type === 'prediction') {
            if (!this.dashboardData) {
                content.innerHTML = '<p class="placeholder-text">Sin datos disponibles.</p>';
                modal.classList.add('active');
                return;
            }

            const totalBudget = this.dashboardData.monthly_budget;
            const available = this.dashboardData.available_balance;
            const totalSpent = totalBudget - available;

            const now = new Date();
            const currentDay = now.getDate();
            const daysInMonth = new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate();
            const daysRemaining = daysInMonth - currentDay;

            // Math
            const dailyAvg = currentDay > 0 ? totalSpent / currentDay : 0;
            const projectedTotal = totalSpent + (dailyAvg * daysRemaining);
            const deviation = projectedTotal - totalBudget;

            // Survival Days
            const survivalDays = dailyAvg > 0 ? available / dailyAvg : 999;

            let statusColor = '#10b981';
            let statusMsg = 'Tu proyección cierra dentro del presupuesto.';

            if (projectedTotal > totalBudget) {
                statusColor = '#ef4444';
                statusMsg = `Al ritmo actual, excederás el presupuesto por $${Math.round(deviation).toLocaleString()}.`;
            } else if (projectedTotal > totalBudget * 0.9) {
                statusColor = '#f59e0b';
                statusMsg = 'Proyección ajustada. Cuidado con gastos extra.';
            }

            const card = document.createElement('div');
            card.className = 'subcat-item';
            card.innerHTML = `
                <div class="subcat-header-row">
                    <h4>Proyección Fin de Mes</h4>
                    <span class="subcat-values" style="color: ${statusColor}; font-weight: bold;">$${Math.round(projectedTotal).toLocaleString()}</span>
                </div>
                <div class="subcat-header-row" style="margin-top:5px;">
                     <span class="subcat-values" style="font-size: 0.9rem; color: var(--text-muted);">Meta: $${totalBudget.toLocaleString()}</span>
                </div>
                <div style="height: 200px; width: 100%; margin-top: 15px;">
                    <canvas id="predChart"></canvas>
                </div>
                <div class="subcat-footer-row" style="color: var(--text-muted); text-align: center; margin-top: 10px;">
                     ${statusMsg}
                </div>
            `;
            content.appendChild(card);

            // Survival Alert
            if (available > 0 && survivalDays < daysRemaining) {
                const survivalCard = document.createElement('div');
                survivalCard.className = 'subcat-item';
                survivalCard.style.marginTop = '15px';
                survivalCard.style.borderLeft = '4px solid #ef4444';
                survivalCard.innerHTML = `
                    <div class="subcat-header-row">
                        <h4>☠️ Días de Supervivencia</h4>
                        <span class="subcat-values" style="color: #ef4444; font-weight: bold;">${Math.floor(survivalDays)} días</span>
                    </div>
                    <div class="subcat-footer-row" style="margin-top: 5px;">
                        Tu saldo se acabará antes de fin de mes (quedan ${daysRemaining} días). ¡Frena el gasto!
                    </div>
                 `;
                content.appendChild(survivalCard);
            }

            // Chart
            const ctx = document.getElementById('predChart').getContext('2d');
            if (this.predChart) this.predChart.destroy();

            // Generate simple data points for Line Chart
            // Point 1: Start (0,0) - simplified
            // Point 2: Today (Day, Spent)
            // Point 3: End (LastDay, Projected)

            this.predChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: ['Inicio', `Hoy (Día ${currentDay})`, `Fin (Día ${daysInMonth})`],
                    datasets: [
                        {
                            label: 'Proyección',
                            data: [0, totalSpent, projectedTotal],
                            borderColor: statusColor,
                            borderDash: [5, 5],
                            pointRadius: 4,
                            fill: false,
                            tension: 0
                        },
                        {
                            label: 'Presupuesto Línea Roja',
                            data: [totalBudget, totalBudget, totalBudget],
                            borderColor: '#94a3b8',
                            borderWidth: 1,
                            pointRadius: 0,
                            fill: false
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { position: 'bottom' },
                        tooltip: {
                            callbacks: { label: (c) => `$${Math.round(c.raw).toLocaleString()}` }
                        }
                    },
                    scales: {
                        y: { beginAtZero: true }
                    }
                }
            });

        } else {
            content.innerHTML = `<p class="placeholder-text">Cargando datos de ${config.title}...</p>`;
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
            const response = await fetch(`${CONFIG.API_BASE}/expenses/`);
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
        list.innerHTML = '';

        const icons = {
            'GASTOS FIJOS': '🏠',
            'COMIDAS': '🍕',
            'TRANSPORTE': '🚗',
            'VICIOS': '🎉',
            'STREAM/APP': '📺',
            'COMISIONES - SEGUROS': '🛡️',
            'OTROS': '📦'
        };

        expenses.slice(0, 5).forEach(exp => {
            const item = document.createElement('div');
            item.className = 'expense-item';

            // Try to find icon by category (sub) or section, or default to generic
            const icon = icons[exp.category] || icons[exp.section] || icons['OTROS'] || '💰';

            item.innerHTML = `
                <div class="exp-icon-box">${icon}</div>
                <div class="exp-details">
                    <h4>${exp.concept}</h4>
                    <p>${new Date(exp.date).toLocaleDateString()} • ${exp.category} • ${exp.payment_method || 'N/A'}</p>
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

        const amountInput = document.getElementById('amount');
        const conceptInput = document.getElementById('concept');
        const sectionInput = document.getElementById('section-select');
        const categoryInput = document.getElementById('category');
        const paymentMethodInput = document.getElementById('payment-method');

        const formData = new FormData();
        formData.append('amount', amountInput.value);
        formData.append('concept', conceptInput.value || '');
        formData.append('section', sectionInput.value || '');
        formData.append('category', categoryInput.value || '');
        formData.append('payment_method', paymentMethodInput.value);

        const photo = document.getElementById('image-upload').files[0];
        if (photo) formData.append('image', photo);

        // Normalize URL to avoid double slashes and ensure correctness
        const url = `${CONFIG.API_BASE}/expenses/`.replace(/([^:]\/)\/+/g, "$1");
        console.log('Posting to:', url);

        try {
            const response = await fetch(url, {
                method: 'POST',
                body: formData
            });

            if (response.ok) {
                document.getElementById('modal-add').classList.remove('active');
                document.getElementById('expense-form').reset();
                document.getElementById('btn-camera').textContent = '📸 Adjuntar Boleta';
                await this.refreshData();
            } else {
                const errorData = await response.json().catch(() => ({}));
                console.error('Submission failed:', response.status, errorData);
                alert(`Error ${response.status}: ${errorData.detail || 'Fallo al guardar'}`);
            }
        } catch (error) {
            console.error('Fetch Error:', error);
            alert(`Error de conexión real: ${error.message}\nURL: ${url}`);
        } finally {
            btn.disabled = false;
            btn.textContent = 'Guardar';
        }
    }

    // --- Compromisos Logic ---

    async loadCompromisos() {
        const list = document.getElementById('compromisos-list');
        list.innerHTML = '<p class="placeholder-text">Cargando compromisos...</p>';

        try {
            const response = await fetch(`${CONFIG.API_BASE}/commitments/`);
            if (response.ok) {
                const data = await response.json();
                this.commitments = data;
                this.renderCompromisos(data);
            } else {
                list.innerHTML = `<p class="placeholder-text">Error ${response.status}</p>`;
            }
        } catch (error) {
            console.error('Error loading commitments:', error);
            list.innerHTML = '<p class="placeholder-text">Error de conexión</p>';
        }
    }

    renderCompromisos(data) {
        // --- 1. Calculate and Render KPIs ---
        // Filter out PAID for active counts if desired, or keep all?
        // User asked for "Total de me deben con monto total y cantidad... y otro igual [Debo]".
        // Usually "Total" implies including paid? No, usually outstanding.
        // Let's stick to Outstanding (Active).

        let totalDebt = 0;
        let countDebt = 0;
        let totalLoan = 0;
        let countLoan = 0;

        data.forEach(c => {
            if (c.status !== 'PAID') {
                const remaining = c.total_amount - c.paid_amount;
                if (c.type === 'DEBT') {
                    totalDebt += remaining;
                    countDebt++;
                }
                if (c.type === 'LOAN') {
                    totalLoan += remaining;
                    countLoan++;
                }
            }
        });

        // KPI 1: Debo (Red)
        const debtAmountEl = document.getElementById('kpi-debt-amount');
        const debtCountEl = document.getElementById('kpi-debt-count');
        debtAmountEl.textContent = `$${totalDebt.toLocaleString()}`;
        debtAmountEl.style.color = '#ef4444';
        debtCountEl.textContent = `${countDebt} transacción${countDebt !== 1 ? 'es' : ''}`;

        // KPI 2: Me Deben (Green)
        const loanAmountEl = document.getElementById('kpi-loan-amount');
        const loanCountEl = document.getElementById('kpi-loan-count');
        loanAmountEl.textContent = `$${totalLoan.toLocaleString()}`;
        loanAmountEl.style.color = '#10b981';
        loanCountEl.textContent = `${countLoan} transacción${countLoan !== 1 ? 'es' : ''}`;

        // KPI 3: Balance (Same as before)
        const balance = totalLoan - totalDebt;
        const balanceEl = document.getElementById('kpi-total-balance');
        const balanceDetail = document.getElementById('kpi-balance-detail');

        balanceEl.textContent = `$${Math.abs(balance).toLocaleString()}`;
        if (balance > 0) {
            balanceEl.style.color = '#10b981'; // Green
            balanceEl.textContent = `+$${balance.toLocaleString()}`;
            balanceDetail.textContent = 'A favor';
        } else if (balance < 0) {
            balanceEl.style.color = '#ef4444'; // Red
            balanceEl.textContent = `-$${Math.abs(balance).toLocaleString()}`;
            balanceDetail.textContent = 'En contra';
        } else {
            balanceEl.style.color = 'var(--text-main)';
            balanceDetail.textContent = 'Neutro';
        }

        // --- 2. Render List ---
        const list = document.getElementById('compromisos-list');
        list.innerHTML = '';

        if (data.length === 0) {
            list.innerHTML = '<p class="placeholder-text">No tienes compromisos activos. ¡Libertad! 🕊️</p>';
            return;
        }

        // Sorting Logic: Overdue (> today) -> Upcoming (<= 3 days) -> Future
        const now = new Date();
        const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());

        const sortedData = [...data].sort((a, b) => {
            // Status Priority: PENDING < PAID? No, user wants Active list mostly?
            // "Lista única con todos los compromisos".
            // Let's hide PAID ones or push to bottom? usually archives are hidden. Plan said "Finalizar (Archivar)".
            // Assuming "GET /commitments" returns all, we might want to filter or show PAID differently.
            // Request said: "Cuántos compromisos tengo activos?".
            // Let's show active first.

            if (a.status !== b.status) return a.status === 'PENDING' ? -1 : 1;

            if (!a.due_date) return 1;
            if (!b.due_date) return -1;
            return new Date(a.due_date) - new Date(b.due_date);
        });

        sortedData.forEach(c => {
            // Show all, including PAID (for visual feedback)

            const item = document.createElement('div');
            // Add 'paid-item' class for styling transparency/strikethrough
            item.className = `commitment-item ${c.status === 'PAID' ? 'paid-item' : ''}`;

            const isDebt = c.type === 'DEBT';
            const remaining = c.total_amount - c.paid_amount;
            const isPaid = c.status === 'PAID';

            // Status Dot Logic
            let dotColor = 'status-green'; // Future
            let statusText = 'Al día';

            if (c.due_date && !isPaid) {
                const due = new Date(c.due_date);
                const dueDay = new Date(due.getFullYear(), due.getMonth(), due.getDate());
                const diffTime = dueDay - today;
                const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

                if (diffDays < 0) {
                    dotColor = 'status-red';
                    statusText = 'Atrasado';
                } else if (diffDays <= 3) {
                    dotColor = 'status-yellow';
                    statusText = 'Próximo';
                }
            } else if (isPaid) {
                statusText = 'Pagado';
            }

            item.innerHTML = `
                <div class="commitment-icon">
                    ${isDebt ? '🔴' : '🟢'}
                </div>
                <div class="commitment-details">
                    <div class="commitment-title" style="${isPaid ? 'text-decoration: line-through; color: var(--text-muted);' : ''}">${c.title}</div>
                    <div class="commitment-amount ${isDebt ? 'amount-debt' : 'amount-loan'}" style="${isPaid ? 'opacity: 0.5;' : ''}">
                        ${isDebt ? 'Debo' : 'Me deben'} $${c.total_amount.toLocaleString()}
                    </div>
                    <div style="font-size: 0.8rem; color: var(--text-muted); margin-top: 2px;">
                        ${c.due_date ? new Date(c.due_date).toLocaleDateString() : 'Sin fecha'} • ${statusText}
                    </div>
                </div>
                <div class="commitment-action">
                    <button class="btn-check ${isPaid ? 'checked' : ''}" data-id="${c.id}">
                        ${isPaid ? '✅' : '⬜'}
                    </button>
                </div>
            `;

            // Interaction logic
            const checkBtn = item.querySelector('.btn-check');
            checkBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.toggleCommitmentStatus(c);
            });

            list.appendChild(item);
        });
    }

    async toggleCommitmentStatus(commitment) {
        const newStatus = commitment.status === 'PENDING' ? 'PAID' : 'PENDING';
        // If PAID, assume full amount paid. If PENDING, revert paid to 0.
        const newPaidAmount = newStatus === 'PAID' ? commitment.total_amount : 0;

        try {
            const response = await fetch(`${CONFIG.API_BASE}/commitments/${commitment.id}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    status: newStatus,
                    paid_amount: newPaidAmount
                })
            });

            if (response.ok) {
                await this.loadCompromisos();
            } else {
                console.error('Failed to update status');
            }
        } catch (e) {
            console.error('Network error', e);
        }
    }

    async handleCommitmentSubmit() {
        const btn = document.getElementById('btn-submit-commitment');
        btn.disabled = true;
        btn.textContent = 'Guardando...';

        const title = document.getElementById('comm-title').value;
        const amount = document.getElementById('comm-amount').value;
        const date = document.getElementById('comm-date').value;
        const type = document.querySelector('input[name="comm-type"]:checked').value;

        const payload = {
            title: title,
            type: type,
            total_amount: parseInt(amount),
            due_date: date || null,
            status: "PENDING"
        };

        try {
            const response = await fetch(`${CONFIG.API_BASE}/commitments/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (response.ok) {
                document.getElementById('modal-add-commitment').classList.remove('active');
                document.getElementById('commitment-form').reset();
                await this.loadCompromisos();
            } else {
                alert('Error al guardar compromiso');
            }
        } catch (error) {
            console.error(error);
            alert('Error de conexión');
        } finally {
            btn.disabled = false;
            btn.textContent = 'Guardar Compromiso';
        }
    }

    // --- Category Management Logic ---

    async handleAddCategory(section) {
        const name = prompt(`Nueva categoría para ${section}:`);
        if (!name) return;

        const budgetStr = prompt(`Presupuesto mensual para ${name} (déjalo en 0 si no sabes):`, "0");
        const budget = parseInt(budgetStr) || 0;

        try {
            const response = await fetch(`${CONFIG.API_BASE}/expenses/categories/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ section: section, category: name, budget: budget })
            });

            if (response.ok) {
                alert('Categoría agregada exitosamente');
                document.getElementById('modal-detail').classList.remove('active');
                await this.refreshData(); // Refresh to see new category
            } else {
                alert('Error al agregar categoría');
            }
        } catch (e) {
            console.error(e);
            alert('Error de conexión');
        }
    }

    async handleDeleteCategory(section, category) {
        if (!confirm(`¿Seguro que quieres borrar la categoría "${category}"?`)) return;

        try {
            const response = await fetch(`${CONFIG.API_BASE}/expenses/categories/`, {
                method: 'DELETE',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ section: section, category: category })
            });

            if (response.ok) {
                alert('Categoría eliminada');
                document.getElementById('modal-detail').classList.remove('active');
                await this.refreshData();
            } else {
                alert('Error al eliminar categoría');
            }
        } catch (e) {
            console.error(e);
            alert('Error de conexión');
        }
    }

    async handleAddSection() {
        const name = prompt("Nombre de la Nueva Sección (ej. EDUCACIÓN):");
        if (!name) return;
        const subCat = prompt(`Agrega la primera subcategoría para ${name} (ej. Mensualidad):`);
        if (!subCat) return;

        const budgetStr = prompt(`Presupuesto mensual para ${subCat}:`, "0");
        const budget = parseInt(budgetStr) || 0;

        // Backend expects same structure: appends row with Section, Category, Budget
        try {
            const response = await fetch(`${CONFIG.API_BASE}/expenses/categories/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ section: name.toUpperCase(), category: subCat, budget: budget })
            });

            if (response.ok) {
                alert('Sección creada exitosamente');
                await this.refreshData();
            } else {
                alert('Error al crear sección');
            }
        } catch (e) {
            console.error(e);
        }
    }

    async handleDeleteSection(sectionName) {
        if (!confirm(`⚠️ ¿ESTÁS SEGURO? \n\nEsto eliminará TODAS las subcategorías de "${sectionName}". \n\nEsta acción no se puede deshacer.`)) return;

        const secData = this.sectionsData[sectionName];
        if (!secData) return;

        const subCats = Object.keys(secData.categories);
        let successCount = 0;

        alert(`Eliminando ${subCats.length} elementos... por favor espera.`);

        for (const cat of subCats) {
            try {
                await fetch(`${CONFIG.API_BASE}/expenses/categories/`, {
                    method: 'DELETE',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ section: sectionName, category: cat })
                });
                successCount++;
            } catch (e) {
                console.error(e);
            }
        }

        alert(`Sección eliminada (${successCount}/${subCats.length} items).`);
        document.getElementById('modal-detail').classList.remove('active');
        await this.refreshData();
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.app = new FinanceApp();
});
