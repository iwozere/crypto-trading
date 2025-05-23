// Utility functions
function showToast(message, type = 'success') {
    const container = document.querySelector('.toast-container') || createToastContainer();
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.remove();
    }, 3000);
}

function createToastContainer() {
    const container = document.createElement('div');
    container.className = 'toast-container';
    document.body.appendChild(container);
    return container;
}

function showLoading() {
    const overlay = document.createElement('div');
    overlay.className = 'spinner-overlay';
    overlay.innerHTML = '<div class="spinner-border text-primary" role="status"></div>';
    document.body.appendChild(overlay);
}

function hideLoading() {
    const overlay = document.querySelector('.spinner-overlay');
    if (overlay) {
        overlay.remove();
    }
}

// API functions
async function fetchBots() {
    try {
        const response = await fetch('/api/bots');
        return await response.json();
    } catch (error) {
        showToast('Failed to fetch bots', 'error');
        return { bots: [] };
    }
}

async function startBot(botType, tradingPair, initialBalance) {
    try {
        showLoading();
        const response = await fetch('/api/bots', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                bot_type: botType,
                trading_pair: tradingPair,
                initial_balance: parseFloat(initialBalance)
            })
        });
        const data = await response.json();
        if (data.success) {
            showToast('Bot started successfully');
            return true;
        } else {
            showToast(data.message || 'Failed to start bot', 'error');
            return false;
        }
    } catch (error) {
        showToast('Failed to start bot', 'error');
        return false;
    } finally {
        hideLoading();
    }
}

async function stopBot(botId) {
    try {
        showLoading();
        const response = await fetch(`/api/bots/${botId}`, {
            method: 'DELETE'
        });
        const data = await response.json();
        if (data.success) {
            showToast('Bot stopped successfully');
            return true;
        } else {
            showToast(data.message || 'Failed to stop bot', 'error');
            return false;
        }
    } catch (error) {
        showToast('Failed to stop bot', 'error');
        return false;
    } finally {
        hideLoading();
    }
}

async function fetchTradeHistory() {
    try {
        const response = await fetch('/api/trade-history');
        return await response.json();
    } catch (error) {
        showToast('Failed to fetch trade history', 'error');
        return { trades: [] };
    }
}

async function updateConfig(botType, parameters) {
    try {
        showLoading();
        const response = await fetch('/api/config', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                bot_type: botType,
                parameters: parameters
            })
        });
        const data = await response.json();
        if (data.success) {
            showToast('Configuration saved successfully');
            return true;
        } else {
            showToast(data.message || 'Failed to save configuration', 'error');
            return false;
        }
    } catch (error) {
        showToast('Failed to save configuration', 'error');
        return false;
    } finally {
        hideLoading();
    }
}

// Initialize Bootstrap tooltips and popovers
document.addEventListener('DOMContentLoaded', function() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function(popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
}); 