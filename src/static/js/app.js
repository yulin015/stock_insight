document.addEventListener('DOMContentLoaded', () => {
    const grid = document.getElementById('ticker-grid');
    const template = document.getElementById('ticker-card-template');
    const lastUpdatedEl = document.getElementById('last-updated');
    
    // Store data locally so we can swap tabs without re-fetching
    let currentMetrics = {};
    
    async function fetchMetrics() {
        try {
            const className = window.APP_CONFIG && window.APP_CONFIG.className ? window.APP_CONFIG.className : '';
            const url = className ? `/api/metrics?class=${encodeURIComponent(className)}` : '/api/metrics';
            const response = await fetch(url);
            const data = await response.json();
            
            if (data.error) {
                console.error("API Error:", data.error);
                return;
            }
            
            lastUpdatedEl.textContent = `Last Updated: ${data.timestamp}`;
            
            // Map array to object keyed by ticker for easy access
            const metricsObj = {};
            data.metrics.forEach(item => {
                metricsObj[item.ticker] = item.terms;
            });
            
            currentMetrics = metricsObj;
            
            // If grid has the loading state, clear it and create cards
            if (grid.querySelector('.loading-state')) {
                grid.innerHTML = '';
                data.metrics.forEach(item => {
                    createTickerCard(item.ticker);
                });
            }
            
            // Update all cards with new data based on their currently active tab
            updateAllCards();
            
        } catch (error) {
            console.error("Failed to fetch metrics:", error);
            lastUpdatedEl.textContent = "Error fetching data. Retrying...";
            lastUpdatedEl.style.color = "var(--accent-red)";
        }
    }
    
    function createTickerCard(ticker) {
        const clone = template.content.cloneNode(true);
        const card = clone.querySelector('.ticker-card');
        card.dataset.ticker = ticker;
        
        const tickerLink = card.querySelector('.ticker-symbol');
        tickerLink.textContent = ticker;
        tickerLink.href = `https://finance.yahoo.com/quote/${encodeURIComponent(ticker)}`;
        
        // Add event listeners to tabs
        const tabs = card.querySelectorAll('.term-tab');
        tabs.forEach(tab => {
            tab.addEventListener('click', (e) => {
                // Remove active from all tabs in this card
                tabs.forEach(t => t.classList.remove('active'));
                // Add active to clicked
                e.target.classList.add('active');
                
                // Update just this card
                updateCardData(card);
            });
        });
        
        grid.appendChild(card);
    }
    
    function updateAllCards() {
        const cards = grid.querySelectorAll('.ticker-card');
        cards.forEach(card => updateCardData(card));
    }
    
    function updateCardData(card) {
        const ticker = card.dataset.ticker;
        const activeTab = card.querySelector('.term-tab.active');
        const term = activeTab.dataset.term; // 'short', 'mid', 'long'
        
        const data = currentMetrics[ticker][term];
        if (!data) return;
        
        // Close Index
        const closeIndexEl = card.querySelector('.close-index-val');
        closeIndexEl.textContent = data.close_index.toFixed(4);
        
        // Buy Chance
        const chanceEl = card.querySelector('.chance-val');
        const chanceBar = card.querySelector('.chance-bar');
        chanceEl.textContent = `${data.buy_chance.toFixed(2)}%`;
        chanceBar.style.width = `${Math.min(data.buy_chance, 100)}%`;
        
        // Color code Buy Chance (High chance = Green, Low = Red)
        if (data.buy_chance >= 50) {
            chanceBar.style.backgroundColor = 'var(--accent-green)';
            chanceEl.className = 'metric-value chance-val color-green';
        } else if (data.buy_chance >= 20) {
            chanceBar.style.backgroundColor = 'var(--accent-blue)';
            chanceEl.className = 'metric-value chance-val color-blue';
        } else {
            chanceBar.style.backgroundColor = 'var(--accent-red)';
            chanceEl.className = 'metric-value chance-val color-red';
        }
        
        const curDropEl = card.querySelector('.current-drop-val');
        curDropEl.textContent = `${data.cur_drop.toFixed(2)}%`;
        if (data.cur_drop < -20) curDropEl.className = 'metric-value current-drop-val color-red';
        else curDropEl.className = 'metric-value current-drop-val color-white';
        
        const changeTodayEl = card.querySelector('.change-today-val');
        if (changeTodayEl) {
            changeTodayEl.textContent = `${data.change_today.toFixed(2)}%`;
            if (data.change_today > 0) changeTodayEl.className = 'metric-value change-today-val color-green';
            else if (data.change_today < 0) changeTodayEl.className = 'metric-value change-today-val color-red';
            else changeTodayEl.className = 'metric-value change-today-val color-white';
        }

        const worstDropEl = card.querySelector('.worst-drop-val');
        worstDropEl.textContent = `${data.worst_drop.toFixed(2)}%`;

        const currentPriceEl = card.querySelector('.current-price-val');
        if(currentPriceEl) currentPriceEl.textContent = `$${data.current_price.toFixed(2)}`;

        const worstDropDateEl = card.querySelector('.worst-drop-date-val');
        if(worstDropDateEl) worstDropDateEl.textContent = data.worst_drop_date;
    }
    
    // Initial fetch
    fetchMetrics();
    
    // Auto-refresh every 60 seconds
    setInterval(fetchMetrics, 60000);
});
