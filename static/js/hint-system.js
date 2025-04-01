/**
 * Contextual Hint and Tip Overlay System
 * 
 * This script provides a user-friendly hint system that displays contextual tips
 * and guidance based on user interactions and page content.
 */

class HintSystem {
    constructor() {
        // Will be populated from API
        this.hints = {};
        
        this.shownHints = [];
        this.currentPage = this.getCurrentPage();
        this.hintOverlay = null;
        this.hintContainer = null;
        this.hintInterval = null;
        this.hintsLoaded = false;
        
        // Initialize
        this.init();
    }
    
    init() {
        // Create hint overlay elements
        this.createHintOverlay();
        
        // Load hints from API
        this.loadHintsFromAPI();
        
        // Load shown hints from local storage
        this.loadShownHints();
        
        // Setup event listeners
        this.setupEventListeners();
    }
    
    loadHintsFromAPI() {
        // Fetch hints for current page from API
        fetch(`/api/hints?page=${this.currentPage}`)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Format hints into our internal structure
                    this.hints = {
                        page: []
                    };
                    
                    // Add hints from API and format them for our system
                    data.hints.forEach(hint => {
                        this.hints.page.push({
                            id: hint.id,
                            text: hint.content,
                            title: hint.title,
                            pages: [this.currentPage, 'global'] // Make them available on current page and global
                        });
                    });
                    
                    this.hintsLoaded = true;
                    
                    // Start hint rotation once hints are loaded
                    this.startHintRotation();
                }
            })
            .catch(error => {
                console.error('Error loading hints:', error);
                // Fallback to empty hints
                this.hints = { page: [] };
                this.hintsLoaded = true;
            });
    }
    
    getCurrentPage() {
        // Determine current page based on URL
        const path = window.location.pathname;
        
        if (path.includes('/dashboard')) return 'dashboard';
        if (path.includes('/guilds')) return 'guilds';
        if (path.includes('/inventory')) return 'inventory';
        if (path.includes('/shop')) return 'shop';
        if (path.includes('/investments')) return 'investments';
        if (path.includes('/events')) return 'events';
        
        return 'home';
    }
    
    createHintOverlay() {
        // Create hint overlay container
        this.hintOverlay = document.createElement('div');
        this.hintOverlay.className = 'hint-overlay';
        this.hintOverlay.innerHTML = `
            <div class="hint-container">
                <div class="hint-header">
                    <span class="hint-title">💡 Helpful Tip</span>
                    <button class="hint-close">&times;</button>
                </div>
                <div class="hint-content"></div>
                <div class="hint-footer">
                    <label class="hint-dont-show">
                        <input type="checkbox" class="hint-dont-show-checkbox">
                        Don't show this tip again
                    </label>
                </div>
            </div>
        `;
        
        document.body.appendChild(this.hintOverlay);
        
        // Store references to hint elements
        this.hintContainer = this.hintOverlay.querySelector('.hint-container');
        this.hintContent = this.hintOverlay.querySelector('.hint-content');
        this.hintCloseBtn = this.hintOverlay.querySelector('.hint-close');
        this.hintDontShowCheckbox = this.hintOverlay.querySelector('.hint-dont-show-checkbox');
        
        // Add CSS if not already in document
        if (!document.getElementById('hint-system-styles')) {
            const styleElement = document.createElement('style');
            styleElement.id = 'hint-system-styles';
            styleElement.textContent = `
                .hint-overlay {
                    position: fixed;
                    bottom: 20px;
                    right: 20px;
                    z-index: 1000;
                    transition: transform 0.3s ease, opacity 0.3s ease;
                    transform: translateY(20px);
                    opacity: 0;
                    pointer-events: none;
                }
                
                .hint-overlay.visible {
                    transform: translateY(0);
                    opacity: 1;
                    pointer-events: all;
                }
                
                .hint-container {
                    background-color: #36393f;
                    border-radius: 8px;
                    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
                    width: 320px;
                    overflow: hidden;
                    border-left: 4px solid #7289da;
                }
                
                .hint-header {
                    padding: 12px 15px;
                    background-color: #2f3136;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }
                
                .hint-title {
                    font-weight: bold;
                    color: #fff;
                }
                
                .hint-close {
                    background: none;
                    border: none;
                    color: #b9bbbe;
                    font-size: 20px;
                    cursor: pointer;
                    padding: 0;
                    width: 24px;
                    height: 24px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    border-radius: 50%;
                    transition: background-color 0.2s;
                }
                
                .hint-close:hover {
                    background-color: rgba(255, 255, 255, 0.1);
                    color: #fff;
                }
                
                .hint-content {
                    padding: 15px;
                    color: #dcddde;
                    line-height: 1.5;
                }
                
                .hint-footer {
                    padding: 10px 15px;
                    background-color: #2f3136;
                    font-size: 0.85rem;
                }
                
                .hint-dont-show {
                    display: flex;
                    align-items: center;
                    gap: 5px;
                    color: #b9bbbe;
                    cursor: pointer;
                }
                
                .hint-dont-show-checkbox {
                    cursor: pointer;
                }
                
                /* Animation for hint appearance */
                @keyframes hint-pulse {
                    0% {
                        box-shadow: 0 0 0 0 rgba(114, 137, 218, 0.4);
                    }
                    70% {
                        box-shadow: 0 0 0 10px rgba(114, 137, 218, 0);
                    }
                    100% {
                        box-shadow: 0 0 0 0 rgba(114, 137, 218, 0);
                    }
                }
                
                .hint-container.pulse {
                    animation: hint-pulse 2s infinite;
                }
            `;
            
            document.head.appendChild(styleElement);
        }
    }
    
    setupEventListeners() {
        // Close hint on button click
        this.hintCloseBtn.addEventListener('click', () => {
            this.hideHint();
            
            // If checkbox is checked, add to hidden hints
            if (this.hintDontShowCheckbox.checked && this.currentHintId) {
                this.addToShownHints(this.currentHintId);
            }
        });
        
        // Page-specific interaction triggers
        this.setupPageInteractionTriggers();
    }
    
    setupPageInteractionTriggers() {
        // Different triggers based on current page
        switch (this.currentPage) {
            case 'shop':
                // Show hint when hovering over shop categories
                const shopCategories = document.querySelectorAll('.category-nav a');
                if (shopCategories.length > 0) {
                    shopCategories.forEach(category => {
                        category.addEventListener('mouseenter', () => {
                            this.showHintById('shop-categories', true);
                        });
                    });
                }
                
                // Show hint when hovering over limited items
                const limitedItems = document.querySelectorAll('.tag.limited');
                if (limitedItems.length > 0) {
                    limitedItems.forEach(item => {
                        item.closest('.shop-item').addEventListener('mouseenter', () => {
                            this.showHintById('limited-items', true);
                        });
                    });
                }
                break;
                
            case 'inventory':
                // Show hints when hovering over consumable items
                const consumableItems = document.querySelectorAll('.tag.consumable');
                if (consumableItems.length > 0) {
                    consumableItems.forEach(item => {
                        item.closest('.item-card').addEventListener('mouseenter', () => {
                            this.showHintById('consumable-items', true);
                        });
                    });
                }
                break;
                
            case 'investments':
                // Show hint when hovering over investment cards
                const investmentCards = document.querySelectorAll('.investment-card');
                if (investmentCards.length > 0) {
                    investmentCards.forEach(card => {
                        card.addEventListener('mouseenter', () => {
                            this.showHintById('investment-duration', true);
                        });
                    });
                }
                break;
                
            case 'events':
                // Show hint when hovering over event cards
                const eventCards = document.querySelectorAll('.event-card');
                if (eventCards.length > 0) {
                    eventCards.forEach(card => {
                        card.addEventListener('mouseenter', () => {
                            this.showHintById('event-effects', true);
                        });
                    });
                }
                break;
                
            default:
                // General navigation hint for other pages
                setTimeout(() => {
                    this.showHintById('navigation-help');
                }, 10000); // Show after 10 seconds of page load
                break;
        }
    }
    
    showHint(hint, isUserTriggered = false) {
        // Don't show if this hint has been dismissed
        if (this.shownHints.includes(hint.id)) {
            return;
        }
        
        // Store current hint ID
        this.currentHintId = hint.id;
        
        // Set hint content
        this.hintContent.textContent = hint.text;
        
        // Set hint title if available
        if (hint.title) {
            this.hintOverlay.querySelector('.hint-title').textContent = `💡 ${hint.title}`;
        } else {
            this.hintOverlay.querySelector('.hint-title').textContent = '💡 Helpful Tip';
        }
        
        // Add pulse animation if user-triggered
        if (isUserTriggered) {
            this.hintContainer.classList.add('pulse');
        } else {
            this.hintContainer.classList.remove('pulse');
        }
        
        // Reset checkbox
        this.hintDontShowCheckbox.checked = false;
        
        // Show the hint
        this.hintOverlay.classList.add('visible');
        
        // If this is an automatic hint, hide after a delay
        if (!isUserTriggered) {
            setTimeout(() => {
                this.hideHint();
            }, 10000); // Hide after 10 seconds
        }
    }
    
    hideHint() {
        this.hintOverlay.classList.remove('visible');
    }
    
    showHintById(hintId, isUserTriggered = false) {
        // Search for hint with this ID in all categories
        for (const category in this.hints) {
            const hint = this.hints[category].find(h => h.id === hintId);
            if (hint && hint.pages.includes(this.currentPage)) {
                this.showHint(hint, isUserTriggered);
                return;
            }
        }
    }
    
    getRandomHintForCurrentPage() {
        // Collect all hints applicable to current page
        const applicableHints = [];
        
        for (const category in this.hints) {
            for (const hint of this.hints[category]) {
                if (hint.pages.includes(this.currentPage) && !this.shownHints.includes(hint.id)) {
                    applicableHints.push(hint);
                }
            }
        }
        
        // Return random hint if any available
        if (applicableHints.length > 0) {
            const randomIndex = Math.floor(Math.random() * applicableHints.length);
            return applicableHints[randomIndex];
        }
        
        return null;
    }
    
    startHintRotation() {
        // Make sure not to start rotation if we haven't loaded hints yet
        if (!this.hintsLoaded || Object.keys(this.hints).length === 0) {
            return;
        }
        
        // Show a random hint on page load after a delay
        setTimeout(() => {
            const randomHint = this.getRandomHintForCurrentPage();
            if (randomHint) {
                this.showHint(randomHint);
            }
        }, 5000); // Show after 5 seconds
        
        // Clear existing interval if any
        if (this.hintInterval) {
            clearInterval(this.hintInterval);
        }
        
        // Setup interval for periodic hints
        this.hintInterval = setInterval(() => {
            // Don't show new hint if current one is visible
            if (this.hintOverlay.classList.contains('visible')) {
                return;
            }
            
            const randomHint = this.getRandomHintForCurrentPage();
            if (randomHint) {
                this.showHint(randomHint);
            }
        }, 120000); // Show new hint every 2 minutes
    }
    
    loadShownHints() {
        // Load from localStorage
        const savedHints = localStorage.getItem('dismissedHints');
        if (savedHints) {
            try {
                this.shownHints = JSON.parse(savedHints);
            } catch (e) {
                console.error('Error loading dismissed hints', e);
                this.shownHints = [];
            }
        }
    }
    
    addToShownHints(hintId) {
        // Add to shown hints list
        if (!this.shownHints.includes(hintId)) {
            this.shownHints.push(hintId);
            
            // Save to localStorage
            localStorage.setItem('dismissedHints', JSON.stringify(this.shownHints));
        }
    }
    
    // Cleanup method (call when navigating away)
    destroy() {
        clearInterval(this.hintInterval);
        if (this.hintOverlay && this.hintOverlay.parentNode) {
            this.hintOverlay.parentNode.removeChild(this.hintOverlay);
        }
    }
}

// Initialize the hint system when the DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.hintSystem = new HintSystem();
});