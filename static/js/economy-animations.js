/**
 * Economy Animations for Discord Economy Bot
 * Provides interactive animations for economic interactions
 */
(function() {
    // Animation settings that can be easily configured
    const ANIMATION_SETTINGS = {
        coinFallCount: 15,           // Number of coins in coin fall animation
        confettiDuration: 2000,      // Duration of confetti animation in ms
        floatingTextDuration: 2000,  // Duration of floating text in ms
        floatingTextDistance: 100,   // Distance floating text moves upward
        coinSize: 40,                // Size of coin images in pixels
        purchaseShakeIntensity: 3,   // Intensity of purchase shake animation
        coinFlipSpeed: 1000,         // Speed of coin flip in ms
        tooltipDuration: 3000        // Duration of tooltips in ms
    };
    
    // Store elements that need animation
    let animatedElements = {
        coins: [],
        confetti: [],
        floatingTexts: []
    };
    
    /**
     * Initialize animations
     */
    function initEconomyAnimations() {
        // Add animation styles dynamically if needed
        addAnimationStyles();
        
        // Set up event listeners
        setupAnimationListeners();
        
        // Initialize confetti
        initConfetti();
        
        // Expose public methods
        window.economyAnimations = {
            playCoinFallAnimation,
            playConfettiAnimation,
            playPurchaseAnimation,
            playItemUseAnimation,
            createFloatingText,
            createShieldEffect
        };
    }
    
    /**
     * Setup event listeners for economic actions
     */
    function setupAnimationListeners() {
        // Purchase buttons
        document.addEventListener('click', function(e) {
            // Purchase buttons
            if (e.target.matches('.purchase-btn') || e.target.closest('.purchase-btn')) {
                playPurchaseAnimation();
            }
            
            // Transaction buttons
            if (e.target.matches('.transaction-btn') || e.target.closest('.transaction-btn')) {
                const x = e.clientX;
                const y = e.clientY;
                playCoinFallAnimation(x, y);
            }
            
            // Item use buttons
            if (e.target.matches('.use-item-btn') || e.target.closest('.use-item-btn')) {
                const itemElem = e.target.closest('.inventory-item');
                if (itemElem) {
                    const itemName = itemElem.dataset.itemName || 'Item';
                    playItemUseAnimation(itemName);
                }
            }
        });
        
        // Animate transaction history on page load
        window.addEventListener('DOMContentLoaded', () => {
            animateTransactionHistory();
        });
    }
    
    /**
     * Play coin fall animation
     * @param {number} x - X coordinate to center animation
     * @param {number} y - Y coordinate to center animation
     * @param {number} count - Number of coins to animate
     */
    function playCoinFallAnimation(x, y, count = ANIMATION_SETTINGS.coinFallCount) {
        // Create container if it doesn't exist
        let container = document.getElementById('coin-animation-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'coin-animation-container';
            container.style.position = 'fixed';
            container.style.top = '0';
            container.style.left = '0';
            container.style.width = '100%';
            container.style.height = '100%';
            container.style.pointerEvents = 'none';
            container.style.zIndex = '9999';
            document.body.appendChild(container);
        }
        
        // Create and animate coins
        for (let i = 0; i < count; i++) {
            setTimeout(() => {
                const coin = document.createElement('img');
                coin.src = '/static/img/coin.svg';
                coin.style.position = 'absolute';
                coin.style.width = `${ANIMATION_SETTINGS.coinSize}px`;
                coin.style.height = `${ANIMATION_SETTINGS.coinSize}px`;
                
                // Random position around the click
                const randomX = x + (Math.random() - 0.5) * 100;
                const startY = y - 50;
                
                coin.style.left = `${randomX}px`;
                coin.style.top = `${startY}px`;
                coin.style.transform = 'translateY(-50px)';
                coin.style.opacity = '0';
                coin.style.transition = 'all 0.5s ease-out, opacity 0.5s ease-in-out';
                
                container.appendChild(coin);
                animatedElements.coins.push(coin);
                
                // Start animation after a small delay
                setTimeout(() => {
                    coin.style.opacity = '1';
                    coin.style.transform = 'translateY(0)';
                    
                    // Fall animation
                    setTimeout(() => {
                        const finalY = window.innerHeight + 100;
                        coin.style.top = `${finalY}px`;
                        coin.style.transition = 'all 1s cubic-bezier(0.4, 0, 1, 1)';
                        
                        // Remove after animation completes
                        setTimeout(() => {
                            container.removeChild(coin);
                            animatedElements.coins = animatedElements.coins.filter(c => c !== coin);
                        }, 1000);
                    }, 300 + Math.random() * 300);
                }, 10);
            }, i * 50); // Stagger the coin creation
        }
    }
    
    /**
     * Play confetti animation for celebrations
     * @param {string} type - Type of confetti animation
     */
    function playConfettiAnimation(type = 'success') {
        // Create container if needed
        let container = document.getElementById('confetti-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'confetti-container';
            container.style.position = 'fixed';
            container.style.top = '0';
            container.style.left = '0';
            container.style.width = '100%';
            container.style.height = '100%';
            container.style.pointerEvents = 'none';
            container.style.zIndex = '9998';
            document.body.appendChild(container);
        }
        
        // Color schemes based on type
        let colors;
        switch (type) {
            case 'success':
                colors = ['#4CAF50', '#8BC34A', '#CDDC39', '#FFEB3B'];
                break;
            case 'rare':
                colors = ['#9C27B0', '#673AB7', '#3F51B5', '#FFEB3B', '#FF9800'];
                break;
            case 'epic':
                colors = ['#FF5722', '#F44336', '#9C27B0', '#E91E63', '#FFEB3B'];
                break;
            case 'neutral':
                colors = ['#2196F3', '#03A9F4', '#00BCD4', '#B3E5FC', '#E1F5FE'];
                break;
            default:
                colors = ['#4CAF50', '#8BC34A', '#CDDC39', '#FFEB3B'];
        }
        
        // Create confetti pieces
        const particleCount = type === 'epic' ? 150 : type === 'rare' ? 100 : 80;
        
        for (let i = 0; i < particleCount; i++) {
            const particle = document.createElement('div');
            particle.className = 'confetti-particle';
            particle.style.position = 'absolute';
            
            // Random properties
            const size = Math.floor(Math.random() * 10) + 5;
            const color = colors[Math.floor(Math.random() * colors.length)];
            const shape = Math.random() > 0.5 ? 'circle' : 'rect';
            const startX = Math.random() * window.innerWidth;
            const startY = -20;
            
            // Set styles
            particle.style.width = `${size}px`;
            particle.style.height = `${size}px`;
            particle.style.backgroundColor = color;
            particle.style.borderRadius = shape === 'circle' ? '50%' : '2px';
            particle.style.left = `${startX}px`;
            particle.style.top = `${startY}px`;
            particle.style.opacity = '1';
            
            // Animation properties
            const duration = Math.random() * 3 + 2; // 2-5 seconds
            const delay = Math.random() * 0.5;
            
            // Apply animation
            particle.style.animation = `fall ${duration}s ease-in ${delay}s forwards, spin ${duration/2}s linear ${delay}s infinite`;
            
            // Add to container
            container.appendChild(particle);
            animatedElements.confetti.push(particle);
            
            // Clean up after animation
            setTimeout(() => {
                if (container.contains(particle)) {
                    container.removeChild(particle);
                    animatedElements.confetti = animatedElements.confetti.filter(p => p !== particle);
                }
            }, (duration + delay) * 1000);
        }
        
        // Define the fall and spin animations
        const styleSheet = document.styleSheets[0];
        if (!document.getElementById('confetti-animations')) {
            const style = document.createElement('style');
            style.id = 'confetti-animations';
            style.innerHTML = `
                @keyframes fall {
                    to {
                        top: 100vh;
                        opacity: 0;
                    }
                }
                @keyframes spin {
                    from {
                        transform: rotate(0deg);
                    }
                    to {
                        transform: rotate(360deg);
                    }
                }
            `;
            document.head.appendChild(style);
        }
    }
    
    /**
     * Play purchase animation
     */
    function playPurchaseAnimation() {
        // Find the shop container or item being purchased
        const container = document.querySelector('.shop-items') || document.querySelector('.shop-container');
        if (!container) return;
        
        // Apply shake animation
        container.classList.add('animate-shake');
        
        // Play coin sound effect if available
        const coinSound = document.getElementById('coin-sound');
        if (coinSound) {
            coinSound.currentTime = 0;
            coinSound.play().catch(e => console.log('Sound play prevented by browser'));
        }
        
        // Remove the animation class after it completes
        setTimeout(() => {
            container.classList.remove('animate-shake');
        }, 500);
    }
    
    /**
     * Play item use animation based on item type
     * @param {string} itemName - Name of the item being used
     */
    function playItemUseAnimation(itemName) {
        // Determine animation type based on item name or type
        const itemType = getItemTypeFromName(itemName);
        const container = document.querySelector('.inventory-container') || document.body;
        
        switch (itemType) {
            case 'potion':
                createFloatingText(
                    window.innerWidth / 2,
                    window.innerHeight / 2,
                    'Potion Used!',
                    '#9C27B0'
                );
                break;
            case 'shield':
                createShieldEffect();
                break;
            case 'boost':
                playConfettiAnimation('success');
                break;
            case 'reward':
                playCoinFallAnimation(window.innerWidth / 2, window.innerHeight / 2);
                break;
            default:
                // Default animation for any item
                createFloatingText(
                    window.innerWidth / 2,
                    window.innerHeight / 2,
                    `${itemName} Used!`,
                    '#2196F3'
                );
        }
    }
    
    /**
     * Create a shield effect animation
     */
    function createShieldEffect() {
        // Create shield element
        const shield = document.createElement('div');
        shield.className = 'shield-effect';
        shield.style.position = 'fixed';
        shield.style.top = '0';
        shield.style.left = '0';
        shield.style.width = '100%';
        shield.style.height = '100%';
        shield.style.borderRadius = '50%';
        shield.style.backgroundColor = 'rgba(33, 150, 243, 0.2)';
        shield.style.border = '4px solid rgba(33, 150, 243, 0.6)';
        shield.style.boxShadow = '0 0 20px rgba(33, 150, 243, 0.8)';
        shield.style.zIndex = '1000';
        shield.style.pointerEvents = 'none';
        shield.style.opacity = '0';
        shield.style.transform = 'scale(0)';
        shield.style.transition = 'all 0.5s ease-out';
        
        document.body.appendChild(shield);
        
        // Animate shield
        setTimeout(() => {
            shield.style.opacity = '1';
            shield.style.transform = 'scale(1.2)';
            
            setTimeout(() => {
                shield.style.opacity = '0';
                shield.style.transform = 'scale(1.5)';
                
                setTimeout(() => {
                    document.body.removeChild(shield);
                }, 500);
            }, 1000);
        }, 10);
    }
    
    /**
     * Create floating text animation
     * @param {number} x - X coordinate
     * @param {number} y - Y coordinate
     * @param {string} text - Text to display
     * @param {string} color - Text color
     */
    function createFloatingText(x, y, text, color) {
        // Create floating text element
        const textElement = document.createElement('div');
        textElement.className = 'floating-text';
        textElement.innerText = text;
        textElement.style.position = 'fixed';
        textElement.style.left = `${x}px`;
        textElement.style.top = `${y}px`;
        textElement.style.transform = 'translate(-50%, -50%)';
        textElement.style.color = color || '#FFFFFF';
        textElement.style.textShadow = '0 0 5px rgba(0,0,0,0.5)';
        textElement.style.fontSize = '24px';
        textElement.style.fontWeight = 'bold';
        textElement.style.zIndex = '1001';
        textElement.style.pointerEvents = 'none';
        textElement.style.opacity = '0';
        textElement.style.transition = `all ${ANIMATION_SETTINGS.floatingTextDuration / 1000}s ease-out`;
        
        document.body.appendChild(textElement);
        animatedElements.floatingTexts.push(textElement);
        
        // Start animation after a small delay
        setTimeout(() => {
            textElement.style.opacity = '1';
            textElement.style.top = `${y - ANIMATION_SETTINGS.floatingTextDistance}px`;
            
            // Remove after animation
            setTimeout(() => {
                textElement.style.opacity = '0';
                
                setTimeout(() => {
                    if (document.body.contains(textElement)) {
                        document.body.removeChild(textElement);
                        animatedElements.floatingTexts = animatedElements.floatingTexts.filter(t => t !== textElement);
                    }
                }, 500);
            }, ANIMATION_SETTINGS.floatingTextDuration - 500);
        }, 10);
    }
    
    /**
     * Add transaction animations to transaction history list
     */
    function animateTransactionHistory() {
        const transactions = document.querySelectorAll('.transaction-item');
        if (transactions.length === 0) return;
        
        // Animate transactions with delay
        transactions.forEach((transaction, index) => {
            transaction.style.opacity = '0';
            transaction.style.transform = 'translateY(20px)';
            transaction.style.transition = 'all 0.3s ease-out';
            
            setTimeout(() => {
                transaction.style.opacity = '1';
                transaction.style.transform = 'translateY(0)';
                
                // Highlight new transactions
                if (transaction.classList.contains('new-transaction')) {
                    setTimeout(() => {
                        transaction.style.backgroundColor = 'rgba(255, 193, 7, 0.2)';
                        transaction.style.transition = 'background-color 1s ease-out';
                        
                        setTimeout(() => {
                            transaction.style.backgroundColor = '';
                        }, 1000);
                    }, 300);
                }
            }, 100 + index * 50);
        });
    }
    
    /**
     * Add necessary animation styles to the document
     */
    function addAnimationStyles() {
        // Check if styles already exist
        if (document.getElementById('economy-animation-styles')) return;
        
        // Create style element
        const style = document.createElement('style');
        style.id = 'economy-animation-styles';
        style.textContent = `
            @keyframes coinFlip {
                0% { transform: rotateY(0deg); }
                50% { transform: rotateY(180deg); }
                100% { transform: rotateY(360deg); }
            }
            
            @keyframes shake {
                0%, 100% { transform: translateX(0); }
                25% { transform: translateX(-${ANIMATION_SETTINGS.purchaseShakeIntensity}px); }
                75% { transform: translateX(${ANIMATION_SETTINGS.purchaseShakeIntensity}px); }
            }
            
            @keyframes pulse {
                0% { transform: scale(1); }
                50% { transform: scale(1.05); }
                100% { transform: scale(1); }
            }
            
            @keyframes glow {
                0% { box-shadow: 0 0 5px rgba(255, 215, 0, 0.5); }
                50% { box-shadow: 0 0 20px rgba(255, 215, 0, 0.8); }
                100% { box-shadow: 0 0 5px rgba(255, 215, 0, 0.5); }
            }
            
            .animate-coin-flip {
                animation: coinFlip ${ANIMATION_SETTINGS.coinFlipSpeed / 1000}s ease-in-out infinite;
            }
            
            .animate-shake {
                animation: shake 0.5s ease-in-out;
            }
            
            .animate-pulse {
                animation: pulse 1.5s ease-in-out infinite;
            }
            
            .animate-glow {
                animation: glow 1.5s ease-in-out infinite;
            }
        `;
        
        document.head.appendChild(style);
    }
    
    /**
     * Initialize confetti library (simplified version)
     */
    function initConfetti() {
        // This is a minimal setup, you can use a library like canvas-confetti for more complex effects
    }
    
    /**
     * Helper to get item type from name
     * @param {string} itemName - Name of the item
     * @returns {string} - Item type category
     */
    function getItemTypeFromName(itemName) {
        itemName = itemName.toLowerCase();
        
        if (itemName.includes('potion') || itemName.includes('elixir')) {
            return 'potion';
        }
        if (itemName.includes('shield') || itemName.includes('protection')) {
            return 'shield';
        }
        if (itemName.includes('boost') || itemName.includes('multiplier')) {
            return 'boost';
        }
        if (itemName.includes('chest') || itemName.includes('box') || itemName.includes('reward')) {
            return 'reward';
        }
        
        return 'generic';
    }
    
    // Initialize animations when DOM is ready
    document.addEventListener('DOMContentLoaded', initEconomyAnimations);
})();