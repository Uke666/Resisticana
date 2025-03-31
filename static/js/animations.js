/**
 * Economy Animations and Effects
 * Adds playful animations and visual effects to the discord economy bot interface
 */

// Coin animation system
class CoinAnimation {
    constructor() {
        this.container = document.createElement('div');
        this.container.className = 'coin-animation-container';
        document.body.appendChild(this.container);
        
        // Preload coin image
        this.coinImage = new Image();
        this.coinImage.src = '/static/img/coin.svg';
        this.coinImage.style.display = 'none';
        document.body.appendChild(this.coinImage);
    }
    
    // Create a single animated coin
    createCoin(x, y, targetX, targetY) {
        const coin = document.createElement('div');
        coin.className = 'animated-coin';
        coin.style.left = x + 'px';
        coin.style.top = y + 'px';
        
        // Add coin image
        const img = document.createElement('img');
        img.src = this.coinImage.src;
        img.alt = 'coin';
        coin.appendChild(img);
        
        this.container.appendChild(coin);
        
        // Animate to target
        setTimeout(() => {
            coin.style.transform = 'translate(0, 0) rotate(0deg)';
            coin.style.left = targetX + 'px';
            coin.style.top = targetY + 'px';
            
            // Remove after animation completes
            setTimeout(() => {
                coin.remove();
            }, 800);
        }, 50);
        
        return coin;
    }
    
    // Burst coins from a point
    burstCoins(x, y, count, targetX, targetY) {
        for (let i = 0; i < count; i++) {
            // Create random starting positions around x,y
            const startX = x + (Math.random() * 40 - 20);
            const startY = y + (Math.random() * 40 - 20);
            
            // Add slight delay for each coin
            setTimeout(() => {
                this.createCoin(startX, startY, targetX, targetY);
            }, i * 50);
        }
    }
    
    // Show coins moving from source to target element
    coinTransfer(sourceElement, targetElement, amount = 5) {
        if (!sourceElement || !targetElement) return;
        
        const sourceBounds = sourceElement.getBoundingClientRect();
        const targetBounds = targetElement.getBoundingClientRect();
        
        const startX = sourceBounds.left + sourceBounds.width / 2;
        const startY = sourceBounds.top + sourceBounds.height / 2;
        
        const endX = targetBounds.left + targetBounds.width / 2;
        const endY = targetBounds.top + targetBounds.height / 2;
        
        this.burstCoins(startX, startY, amount, endX, endY);
    }
    
    // Show coins appearing at a purchase
    purchaseCoins(element, amount = 10) {
        if (!element) return;
        
        const bounds = element.getBoundingClientRect();
        const centerX = bounds.left + bounds.width / 2;
        const centerY = bounds.top + bounds.height / 2;
        
        // Create coins all around the element
        for (let i = 0; i < amount; i++) {
            const angle = (i / amount) * Math.PI * 2;
            const distance = 50 + Math.random() * 30;
            
            const startX = centerX + Math.cos(angle) * distance;
            const startY = centerY + Math.sin(angle) * distance;
            
            setTimeout(() => {
                this.createCoin(startX, startY, centerX, centerY);
            }, i * 40);
        }
    }
}

// Notification system for economic events
class EconomyNotifications {
    constructor() {
        this.container = document.createElement('div');
        this.container.className = 'economy-notifications';
        document.body.appendChild(this.container);
        
        this.notifications = [];
        this.maxNotifications = 3; // Maximum visible notifications
    }
    
    // Add a new notification
    addNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `economy-notification ${type}`;
        
        // Add content
        const icon = document.createElement('span');
        icon.className = 'notification-icon';
        
        const text = document.createElement('span');
        text.className = 'notification-text';
        text.textContent = message;
        
        notification.appendChild(icon);
        notification.appendChild(text);
        
        // Add to container
        this.container.appendChild(notification);
        this.notifications.push(notification);
        
        // Animate in
        setTimeout(() => {
            notification.classList.add('show');
        }, 10);
        
        // Remove oldest if too many
        if (this.notifications.length > this.maxNotifications) {
            const oldest = this.notifications.shift();
            oldest.classList.remove('show');
            setTimeout(() => {
                oldest.remove();
            }, 500);
        }
        
        // Auto-remove after delay
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => {
                notification.remove();
                const index = this.notifications.indexOf(notification);
                if (index > -1) {
                    this.notifications.splice(index, 1);
                }
            }, 500);
        }, 5000);
        
        return notification;
    }
    
    // Add different types of notifications
    success(message) {
        return this.addNotification(message, 'success');
    }
    
    error(message) {
        return this.addNotification(message, 'error');
    }
    
    info(message) {
        return this.addNotification(message, 'info');
    }
}

// Economic Events Generator
class EconomicEventsGenerator {
    constructor(notifications) {
        this.notifications = notifications;
        this.events = [
            { type: 'market_shift', message: 'Market prices are fluctuating! Investments may yield higher returns today.', probability: 0.3 },
            { type: 'tax_day', message: 'Tax Day! All transactions have a 5% fee today.', probability: 0.1 },
            { type: 'bonus_day', message: 'Economic Boom! All earnings are increased by 10% today.', probability: 0.2 },
            { type: 'sale_day', message: 'Flash Sale! Some items in the shop are discounted today.', probability: 0.25 },
            { type: 'investment_opportunity', message: 'Special investment opportunity available! Check the investments page.', probability: 0.15 },
            { type: 'lottery_announcement', message: 'Guild Lottery is open! Buy tickets for a chance to win big.', probability: 0.2 },
            { type: 'bonus_quest', message: 'Bonus quest available with extra rewards! Check your quest log.', probability: 0.3 }
        ];
        
        this.activeEvents = [];
    }
    
    // Check if an event should trigger based on probability
    shouldTriggerEvent(event) {
        return Math.random() < event.probability;
    }
    
    // Generate random events
    generateRandomEvent() {
        // Filter out events that shouldn't trigger based on probability
        const possibleEvents = this.events.filter(event => this.shouldTriggerEvent(event));
        
        if (possibleEvents.length === 0) return null;
        
        // Choose a random event from possible ones
        const randomIndex = Math.floor(Math.random() * possibleEvents.length);
        return possibleEvents[randomIndex];
    }
    
    // Announce an event
    announceEvent(event) {
        if (!event) return;
        
        // Add to active events
        this.activeEvents.push(event);
        
        // Notify the user
        this.notifications.addNotification(event.message, 'event');
        
        // Add event to local storage to persist between page loads
        this.saveActiveEvents();
        
        return event;
    }
    
    // Check for new events (called on page load)
    checkForEvents() {
        // Load any saved events
        this.loadActiveEvents();
        
        // Only generate a new event if we don't have any active ones
        if (this.activeEvents.length === 0) {
            const newEvent = this.generateRandomEvent();
            if (newEvent) {
                this.announceEvent(newEvent);
            }
        } else {
            // Announce existing events
            this.activeEvents.forEach(event => {
                this.notifications.addNotification(event.message, 'event');
            });
        }
    }
    
    // Save active events to localStorage
    saveActiveEvents() {
        localStorage.setItem('economyActiveEvents', JSON.stringify(this.activeEvents));
    }
    
    // Load active events from localStorage
    loadActiveEvents() {
        const saved = localStorage.getItem('economyActiveEvents');
        if (saved) {
            try {
                this.activeEvents = JSON.parse(saved);
            } catch (e) {
                console.error('Error loading saved events:', e);
                this.activeEvents = [];
            }
        }
    }
    
    // Clear all active events
    clearEvents() {
        this.activeEvents = [];
        localStorage.removeItem('economyActiveEvents');
    }
}

// Initialize everything when document is ready
document.addEventListener('DOMContentLoaded', function() {
    // Set up coin animation system
    const coinAnimation = new CoinAnimation();
    window.coinAnimation = coinAnimation; // Make it globally accessible
    
    // Set up notifications
    const notifications = new EconomyNotifications();
    window.economyNotifications = notifications;
    
    // Set up economic events
    const eventsGenerator = new EconomicEventsGenerator(notifications);
    window.economicEvents = eventsGenerator;
    
    // Check for events on page load
    eventsGenerator.checkForEvents();
    
    // Set up event handlers for shop
    setupShopAnimations(coinAnimation, notifications);
    
    // Set up event handlers for inventory
    setupInventoryAnimations(coinAnimation, notifications);
    
    // Set up event handlers for investments
    setupInvestmentAnimations(coinAnimation, notifications);
});

// Set up shop animations and interactions
function setupShopAnimations(coinAnimation, notifications) {
    // Find the purchase buttons
    const purchaseButtons = document.querySelectorAll('.btn-buy');
    const confirmPurchaseBtn = document.getElementById('confirmPurchase');
    
    if (confirmPurchaseBtn) {
        // Add click handler for purchase confirmation
        confirmPurchaseBtn.addEventListener('click', function() {
            // The actual purchase is handled by the existing code
            // We just add the animation effect
            const balanceElement = document.querySelector('.balance-amount');
            if (balanceElement) {
                setTimeout(() => {
                    coinAnimation.purchaseCoins(balanceElement, 10);
                    notifications.success('Item purchased successfully!');
                }, 300);
            }
        });
    }
}

// Set up inventory animations and interactions
function setupInventoryAnimations(coinAnimation, notifications) {
    // Find the use buttons
    const useButtons = document.querySelectorAll('.btn-use');
    
    useButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            // Original click handler remains, we just add visual effects
            const itemCard = this.closest('.item-card');
            if (itemCard) {
                coinAnimation.burstCoins(
                    e.clientX, 
                    e.clientY, 
                    7, 
                    e.clientX, 
                    e.clientY - 100
                );
            }
        });
    });
}

// Set up investment animations and interactions
function setupInvestmentAnimations(coinAnimation, notifications) {
    // Find investment cards
    const investmentCards = document.querySelectorAll('.investment-card');
    
    investmentCards.forEach(card => {
        // Add hover effect to show potential coins
        card.addEventListener('mouseenter', function() {
            const incomeElement = this.querySelector('.investment-stat .value:nth-child(2)');
            if (incomeElement) {
                const bounds = incomeElement.getBoundingClientRect();
                coinAnimation.createCoin(
                    bounds.left, 
                    bounds.top,
                    bounds.left + 20,
                    bounds.top - 20
                );
            }
        });
    });
}