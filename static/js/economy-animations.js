/**
 * Economy Animations System
 * 
 * This script provides visual feedback and animations for economic activities
 * in the Discord Economy Bot dashboard.
 */

class EconomyAnimations {
    constructor() {
        // Initialize the animation system
        this.init();
        
        // Track active animations
        this.activeConfetti = null;
        this.floatingTexts = [];
    }
    
    init() {
        // Add CSS animations if not already present
        this.addAnimationStyles();
        
        // Set up event listeners for economic actions
        this.setupEventListeners();
    }
    
    addAnimationStyles() {
        // Check if styles are already added
        if (document.getElementById('economy-animation-styles')) {
            return;
        }
        
        // Create style element
        const style = document.createElement('style');
        style.id = 'economy-animation-styles';
        
        // Define animation styles
        style.textContent = `
            /* Coin animations */
            @keyframes coin-bounce {
                0%, 20%, 50%, 80%, 100% {
                    transform: translateY(0);
                }
                40% {
                    transform: translateY(-20px);
                }
                60% {
                    transform: translateY(-10px);
                }
            }
            
            @keyframes coin-spin {
                0% {
                    transform: rotateY(0deg);
                }
                100% {
                    transform: rotateY(360deg);
                }
            }
            
            @keyframes coin-rain {
                0% {
                    opacity: 0;
                    transform: translateY(-20px);
                }
                50% {
                    opacity: 1;
                }
                100% {
                    opacity: 0;
                    transform: translateY(100px);
                }
            }
            
            @keyframes coin-pulse {
                0% {
                    box-shadow: 0 0 0 0 rgba(255, 215, 0, 0.7);
                    transform: scale(1);
                }
                70% {
                    box-shadow: 0 0 0 10px rgba(255, 215, 0, 0);
                    transform: scale(1.05);
                }
                100% {
                    box-shadow: 0 0 0 0 rgba(255, 215, 0, 0);
                    transform: scale(1);
                }
            }
            
            /* Number animation */
            @keyframes number-increase {
                0% {
                    transform: scale(1);
                    color: inherit;
                }
                50% {
                    transform: scale(1.2);
                    color: #ffd700;
                }
                100% {
                    transform: scale(1);
                    color: inherit;
                }
            }
            
            @keyframes number-decrease {
                0% {
                    transform: scale(1);
                    color: inherit;
                }
                50% {
                    transform: scale(1.2);
                    color: #ff4444;
                }
                100% {
                    transform: scale(1);
                    color: inherit;
                }
            }
            
            /* Transaction animation */
            .transaction-animation {
                position: fixed;
                pointer-events: none;
                z-index: 9999;
            }
            
            .coin {
                width: 30px;
                height: 30px;
                background-image: url('/static/img/coin.svg');
                background-size: contain;
                background-repeat: no-repeat;
                position: absolute;
            }
            
            .transaction-amount {
                position: absolute;
                font-weight: bold;
                font-size: 1.2rem;
                white-space: nowrap;
            }
            
            /* Investment animation */
            .investment-glow {
                animation: coin-pulse 2s infinite;
            }
            
            /* Event animations */
            .event-enter {
                animation: slideInRight 0.5s forwards;
            }
            
            @keyframes slideInRight {
                from {
                    transform: translateX(100%);
                    opacity: 0;
                }
                to {
                    transform: translateX(0);
                    opacity: 1;
                }
            }
            
            .event-exit {
                animation: fadeOut 0.5s forwards;
            }
            
            @keyframes fadeOut {
                from {
                    opacity: 1;
                }
                to {
                    opacity: 0;
                }
            }
            
            /* Purchase animation */
            @keyframes purchase-success {
                0% {
                    transform: scale(1);
                    box-shadow: 0 0 0 0 rgba(40, 167, 69, 0.7);
                }
                50% {
                    transform: scale(1.05);
                    box-shadow: 0 0 0 10px rgba(40, 167, 69, 0);
                }
                100% {
                    transform: scale(1);
                    box-shadow: 0 0 0 0 rgba(40, 167, 69, 0);
                }
            }
            
            .purchase-success {
                animation: purchase-success 1s;
            }
            
            /* Daily reward animation */
            .daily-reward-animation {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                display: flex;
                justify-content: center;
                align-items: center;
                z-index: 9999;
                pointer-events: none;
            }
            
            .daily-reward-container {
                background-color: rgba(0, 0, 0, 0.7);
                border-radius: 10px;
                padding: 20px;
                text-align: center;
                color: white;
                transform: scale(0);
                animation: pop-in 0.5s forwards, pop-out 0.5s forwards 2s;
            }
            
            @keyframes pop-in {
                0% {
                    transform: scale(0);
                }
                70% {
                    transform: scale(1.1);
                }
                100% {
                    transform: scale(1);
                }
            }
            
            @keyframes pop-out {
                0% {
                    transform: scale(1);
                    opacity: 1;
                }
                100% {
                    transform: scale(0);
                    opacity: 0;
                }
            }
            
            .daily-reward-amount {
                font-size: 2rem;
                font-weight: bold;
                color: #ffd700;
                margin: 10px 0;
            }
            
            /* Activity multiplier animation */
            .multiplier-badge {
                display: inline-block;
                padding: 3px 8px;
                border-radius: 12px;
                background-color: #7289da;
                color: white;
                font-size: 0.8rem;
                margin-left: 5px;
                animation: pulse-multiplier 2s infinite;
            }
            
            @keyframes pulse-multiplier {
                0% {
                    box-shadow: 0 0 0 0 rgba(114, 137, 218, 0.7);
                }
                70% {
                    box-shadow: 0 0 0 5px rgba(114, 137, 218, 0);
                }
                100% {
                    box-shadow: 0 0 0 0 rgba(114, 137, 218, 0);
                }
            }
        `;
        
        // Add style to document head
        document.head.appendChild(style);
    }
    
    setupEventListeners() {
        // Listen for economic activities
        this.setupPurchaseListeners();
        this.setupInvestmentListeners();
        this.setupTransactionListeners();
        this.setupDailyRewardListener();
        this.setupEventListeners();
    }
    
    setupPurchaseListeners() {
        // Add purchase animation to purchase buttons
        const purchaseButtons = document.querySelectorAll('.purchase-btn, .btn-purchase');
        purchaseButtons.forEach(button => {
            button.addEventListener('click', (event) => {
                // Prevent multiple clicks
                if (button.dataset.processing === 'true') {
                    event.preventDefault();
                    return;
                }
                
                button.dataset.processing = 'true';
                
                // Get item card
                const itemCard = button.closest('.item-card, .shop-item');
                if (itemCard) {
                    // Add pending state
                    itemCard.classList.add('processing');
                    
                    // Simulate transaction processing
                    setTimeout(() => {
                        // Reset processing state
                        button.dataset.processing = 'false';
                        itemCard.classList.remove('processing');
                        
                        // If this is just a visual demo (not a real purchase)
                        if (button.classList.contains('demo')) {
                            event.preventDefault();
                            itemCard.classList.add('purchase-success');
                            
                            // Create coin animation
                            this.animateCoinTransaction(button, '-100', 5);
                            
                            // Remove animation class after it completes
                            setTimeout(() => {
                                itemCard.classList.remove('purchase-success');
                            }, 1000);
                        }
                    }, 500);
                }
            });
        });
    }
    
    setupInvestmentListeners() {
        // Add pulsing effect to profitable investments
        const investmentReturns = document.querySelectorAll('.investment-card .stat-value');
        investmentReturns.forEach(returnElem => {
            // Check if this shows a positive return
            if (returnElem.textContent.includes('~') && 
                parseFloat(returnElem.textContent.replace('~', '')) > 0) {
                returnElem.classList.add('investment-glow');
            }
        });
    }
    
    setupTransactionListeners() {
        // Add animations to transaction buttons
        const transactionButtons = document.querySelectorAll('.transfer-btn, .deposit-btn, .withdraw-btn');
        transactionButtons.forEach(button => {
            button.addEventListener('click', () => {
                // Get transaction type and amount
                const isDeposit = button.classList.contains('deposit-btn');
                const isWithdraw = button.classList.contains('withdraw-btn');
                const isTransfer = button.classList.contains('transfer-btn');
                
                // Get amount from nearby input if available
                let amount = 100; // Default amount
                const amountInput = button.parentElement.querySelector('input[type="number"]');
                if (amountInput) {
                    amount = parseInt(amountInput.value) || amount;
                }
                
                // Create appropriate animation
                if (isDeposit) {
                    this.animateCoinTransaction(button, `+${amount}`, 8, '#28a745');
                } else if (isWithdraw) {
                    this.animateCoinTransaction(button, `+${amount}`, 8, '#ffc107');
                } else if (isTransfer) {
                    this.animateCoinTransaction(button, `-${amount}`, 5, '#dc3545');
                }
            });
        });
    }
    
    setupDailyRewardListener() {
        // Check if the current page might show daily rewards
        if (['dashboard', 'home'].includes(this.getCurrentPage())) {
            // Look for daily claim button
            const dailyClaimBtn = document.querySelector('.daily-claim-btn');
            if (dailyClaimBtn) {
                dailyClaimBtn.addEventListener('click', () => {
                    this.showDailyRewardAnimation(100); // Default amount
                });
            }
            
            // Alternatively, check URL for daily claim parameter
            if (window.location.search.includes('daily=claimed')) {
                // Extract amount from URL if available
                const urlParams = new URLSearchParams(window.location.search);
                const amount = urlParams.get('amount') || 100;
                
                // Show reward animation
                this.showDailyRewardAnimation(amount);
                
                // Clean URL to prevent animation on refresh
                const newUrl = window.location.pathname + 
                    window.location.search.replace(/[?&]daily=claimed/, '')
                        .replace(/[?&]amount=\d+/, '');
                window.history.replaceState({}, document.title, newUrl);
            }
        }
    }
    
    setupEventListeners() {
        // Add animations to economic event cards
        const eventCards = document.querySelectorAll('.event-card');
        eventCards.forEach((card, index) => {
            // Add staggered entrance animation
            setTimeout(() => {
                card.classList.add('event-enter');
            }, index * 200);
            
            // Add hover animation
            card.addEventListener('mouseenter', () => {
                // Add multiplier badge if not present
                if (!card.querySelector('.multiplier-badge') && card.textContent.includes('x')) {
                    const multiplierMatch = card.textContent.match(/(\d+(\.\d+)?)x/);
                    if (multiplierMatch) {
                        const multiplier = multiplierMatch[0];
                        const description = card.querySelector('.event-description');
                        if (description) {
                            const badge = document.createElement('span');
                            badge.className = 'multiplier-badge';
                            badge.textContent = multiplier;
                            description.appendChild(badge);
                        }
                    }
                }
            });
        });
    }
    
    /* Animation methods */
    
    animateCoinTransaction(element, amount, numCoins = 5, color = null) {
        // Create container for the transaction animation
        const container = document.createElement('div');
        container.className = 'transaction-animation';
        document.body.appendChild(container);
        
        // Get element position
        const rect = element.getBoundingClientRect();
        container.style.left = `${rect.left + rect.width / 2}px`;
        container.style.top = `${rect.top + rect.height / 2}px`;
        
        // Create coins
        for (let i = 0; i < numCoins; i++) {
            const coin = document.createElement('div');
            coin.className = 'coin';
            
            // Random position offset
            const angle = (Math.random() * Math.PI * 2);
            const distance = 50 + Math.random() * 50;
            const x = Math.cos(angle) * distance;
            const y = Math.sin(angle) * distance;
            
            // Set initial position
            coin.style.left = `${x}px`;
            coin.style.top = `${y}px`;
            
            // Add animations
            coin.style.animation = `
                coin-spin ${0.5 + Math.random() * 1}s linear infinite,
                coin-bounce ${1 + Math.random()}s ease-in-out infinite
            `;
            
            // Random delay
            coin.style.animationDelay = `${Math.random() * 0.5}s`;
            
            // Add to container
            container.appendChild(coin);
        }
        
        // Create amount indicator
        if (amount) {
            const amountElem = document.createElement('div');
            amountElem.className = 'transaction-amount';
            amountElem.textContent = amount;
            
            // Set color based on transaction type
            if (!color) {
                color = amount.startsWith('+') ? '#28a745' : '#dc3545';
            }
            amountElem.style.color = color;
            
            // Add animation
            amountElem.style.animation = `
                ${amount.startsWith('+') ? 'number-increase' : 'number-decrease'} 2s ease-out forwards
            `;
            
            // Position in center
            amountElem.style.left = '0';
            amountElem.style.top = '-20px';
            amountElem.style.transform = 'translateX(-50%)';
            
            // Add to container
            container.appendChild(amountElem);
        }
        
        // Remove animation after it completes
        setTimeout(() => {
            container.parentNode.removeChild(container);
        }, 2000);
    }
    
    showDailyRewardAnimation(amount) {
        // Create animation container
        const container = document.createElement('div');
        container.className = 'daily-reward-animation';
        
        // Create animation content
        container.innerHTML = `
            <div class="daily-reward-container">
                <h2>Daily Reward Claimed!</h2>
                <div class="daily-reward-amount">+${amount} coins</div>
                <p>Come back tomorrow for another reward!</p>
            </div>
        `;
        
        // Add to document
        document.body.appendChild(container);
        
        // Create coin rain effect
        for (let i = 0; i < 20; i++) {
            const coin = document.createElement('div');
            coin.className = 'coin';
            
            // Random position
            coin.style.left = `${Math.random() * 100}%`;
            coin.style.top = '-30px';
            
            // Add animation
            coin.style.animation = 'coin-rain 3s linear forwards';
            coin.style.animationDelay = `${Math.random() * 2}s`;
            
            // Add to container
            container.appendChild(coin);
        }
        
        // Remove animation after it completes
        setTimeout(() => {
            container.parentNode.removeChild(container);
        }, 5000);
    }
    
    // Additional animation methods for item interactions
    
    playCoinFallAnimation(x, y, numCoins = 10) {
        // Create container for the coin fall animation
        const container = document.createElement('div');
        container.className = 'transaction-animation';
        container.style.position = 'fixed';
        container.style.left = `${x}px`;
        container.style.top = `${y}px`;
        container.style.pointerEvents = 'none';
        container.style.zIndex = '9999';
        document.body.appendChild(container);
        
        // Create coins
        for (let i = 0; i < numCoins; i++) {
            setTimeout(() => {
                const coin = document.createElement('div');
                coin.className = 'coin';
                
                // Random position
                const angle = Math.random() * Math.PI;
                const distance = 10 + Math.random() * 30;
                const startX = Math.cos(angle) * distance;
                const startY = Math.sin(angle) * distance - 20;
                
                // Set style
                coin.style.position = 'absolute';
                coin.style.left = `${startX}px`;
                coin.style.top = `${startY}px`;
                coin.style.opacity = '0';
                
                // Add to container
                container.appendChild(coin);
                
                // Initialize falling animation
                setTimeout(() => {
                    coin.style.transition = 'all 1s cubic-bezier(0.4, 0.0, 0.2, 1)';
                    coin.style.opacity = '1';
                    
                    // Final position (falling down)
                    const finalY = 100 + Math.random() * 50;
                    const finalX = startX + (Math.random() * 60 - 30);
                    
                    coin.style.transform = `translate(${finalX}px, ${finalY}px) rotate(${Math.random() * 360}deg)`;
                    
                    // Remove after animation
                    setTimeout(() => {
                        coin.style.opacity = '0';
                        setTimeout(() => {
                            if (coin.parentNode) {
                                coin.parentNode.removeChild(coin);
                            }
                        }, 500);
                    }, 800);
                }, 10);
            }, i * 100); // Stagger the coin drops
        }
        
        // Clean up the container after all animations complete
        setTimeout(() => {
            if (container.parentNode) {
                container.parentNode.removeChild(container);
            }
        }, numCoins * 100 + 2000);
    }
    
    createFloatingText(x, y, text, color = '#ffffff') {
        // Create floating text element
        const floatingText = document.createElement('div');
        floatingText.textContent = text;
        floatingText.style.position = 'fixed';
        floatingText.style.left = `${x}px`;
        floatingText.style.top = `${y}px`;
        floatingText.style.transform = 'translate(-50%, -50%)';
        floatingText.style.color = color;
        floatingText.style.fontWeight = 'bold';
        floatingText.style.fontSize = '1.5rem';
        floatingText.style.textShadow = '0 2px 4px rgba(0, 0, 0, 0.5)';
        floatingText.style.pointerEvents = 'none';
        floatingText.style.zIndex = '10000';
        floatingText.style.whiteSpace = 'nowrap';
        
        // Add to document
        document.body.appendChild(floatingText);
        
        // Track this text
        this.floatingTexts.push(floatingText);
        
        // Animate
        floatingText.style.transition = 'all 2s ease-out';
        setTimeout(() => {
            floatingText.style.opacity = '0';
            floatingText.style.transform = 'translate(-50%, calc(-50% - 50px))';
            
            // Remove after animation
            setTimeout(() => {
                if (floatingText.parentNode) {
                    floatingText.parentNode.removeChild(floatingText);
                    
                    // Remove from tracking array
                    const index = this.floatingTexts.indexOf(floatingText);
                    if (index !== -1) {
                        this.floatingTexts.splice(index, 1);
                    }
                }
            }, 2000);
        }, 10);
    }
    
    playConfettiAnimation(type = 'normal') {
        // If we have an active confetti animation, clear it first
        if (this.activeConfetti) {
            clearTimeout(this.activeConfetti.timeout);
            if (this.activeConfetti.container && this.activeConfetti.container.parentNode) {
                this.activeConfetti.container.parentNode.removeChild(this.activeConfetti.container);
            }
        }
        
        // Create container for confetti
        const container = document.createElement('div');
        container.style.position = 'fixed';
        container.style.top = '0';
        container.style.left = '0';
        container.style.width = '100%';
        container.style.height = '100%';
        container.style.pointerEvents = 'none';
        container.style.zIndex = '9998';
        document.body.appendChild(container);
        
        // Determine confetti settings based on type
        let numParticles = 50;
        let colors = ['#f44336', '#e91e63', '#9c27b0', '#673ab7', '#3f51b5', '#2196f3', '#03a9f4'];
        let duration = 3000;
        
        switch (type) {
            case 'epic':
                numParticles = 200;
                colors = ['#FFD700', '#FFA500', '#FF4500', '#FF1493', '#9400D3', '#4B0082'];
                duration = 5000;
                break;
            case 'rare':
                numParticles = 100;
                colors = ['#48C9B0', '#F4D03F', '#5DADE2', '#CD6155', '#AF7AC5'];
                duration = 4000;
                break;
        }
        
        // Create confetti particles
        for (let i = 0; i < numParticles; i++) {
            setTimeout(() => {
                const particle = document.createElement('div');
                
                // Randomize appearance
                const size = 5 + Math.random() * 15;
                const isSquare = Math.random() > 0.5;
                const color = colors[Math.floor(Math.random() * colors.length)];
                
                // Set style
                particle.style.position = 'absolute';
                particle.style.width = `${size}px`;
                particle.style.height = `${size}px`;
                particle.style.backgroundColor = color;
                particle.style.borderRadius = isSquare ? '2px' : '50%';
                particle.style.opacity = '0';
                
                // Initial position (top of screen)
                particle.style.left = `${Math.random() * 100}%`;
                particle.style.top = '-20px';
                
                // Add to container
                container.appendChild(particle);
                
                // Animate the confetti
                setTimeout(() => {
                    particle.style.transition = `all ${2 + Math.random() * 2}s ease-out`;
                    particle.style.opacity = '0.8';
                    
                    // Final position (random across screen)
                    const finalY = 50 + Math.random() * 100;
                    const finalX = parseInt(particle.style.left) + (Math.random() * 40 - 20);
                    const rotation = Math.random() * 360;
                    
                    particle.style.transform = `translate(${finalX}%, ${finalY}vh) rotate(${rotation}deg)`;
                    
                    // Fade out at end of animation
                    setTimeout(() => {
                        particle.style.opacity = '0';
                        
                        // Remove particle after fade
                        setTimeout(() => {
                            if (particle.parentNode) {
                                particle.parentNode.removeChild(particle);
                            }
                        }, 1000);
                    }, 1500);
                }, 10);
            }, i * 20); // Stagger the confetti
        }
        
        // Track the active confetti animation
        this.activeConfetti = {
            container,
            timeout: setTimeout(() => {
                if (container.parentNode) {
                    container.parentNode.removeChild(container);
                }
                this.activeConfetti = null;
            }, duration + 1000)
        };
    }
    
    playItemUseAnimation(itemName) {
        // Default effect if item name doesn't match any special cases
        const container = document.createElement('div');
        container.style.position = 'fixed';
        container.style.top = '50%';
        container.style.left = '50%';
        container.style.transform = 'translate(-50%, -50%)';
        container.style.width = '100px';
        container.style.height = '100px';
        container.style.background = 'radial-gradient(circle, rgba(115,135,219,0.8) 0%, rgba(115,135,219,0) 70%)';
        container.style.borderRadius = '50%';
        container.style.zIndex = '9997';
        container.style.pointerEvents = 'none';
        
        // Add to document
        document.body.appendChild(container);
        
        // Animate
        container.style.transition = 'all 1s ease-out';
        setTimeout(() => {
            container.style.transform = 'translate(-50%, -50%) scale(3)';
            container.style.opacity = '0';
            
            // Remove after animation
            setTimeout(() => {
                if (container.parentNode) {
                    container.parentNode.removeChild(container);
                }
            }, 1000);
        }, 10);
        
        // Play sound if available
        if (window.Audio) {
            let soundUrl = '/static/sounds/item-use.mp3';
            
            // Choose sound based on item name
            if (itemName.toLowerCase().includes('potion')) {
                soundUrl = '/static/sounds/potion.mp3';
            } else if (itemName.toLowerCase().includes('shield')) {
                soundUrl = '/static/sounds/shield.mp3';
            } else if (itemName.toLowerCase().includes('scroll')) {
                soundUrl = '/static/sounds/scroll.mp3';
            }
            
            try {
                const sound = new Audio(soundUrl);
                sound.volume = 0.5;
                sound.play().catch(e => console.log('Sound play error:', e));
            } catch (e) {
                console.log('Audio error:', e);
            }
        }
    }
    
    getCurrentPage() {
        const path = window.location.pathname;
        if (path.includes('/dashboard')) return 'dashboard';
        if (path.includes('/inventory')) return 'inventory';
        if (path.includes('/shop')) return 'shop';
        if (path.includes('/investments')) return 'investments';
        if (path.includes('/events')) return 'events';
        if (path.includes('/guilds')) return 'guilds';
        return 'home';
    }
}

// Initialize the animation system when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.economyAnimations = new EconomyAnimations();
});