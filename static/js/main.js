/**
 * Main JavaScript functionality for Discord Economy Bot Dashboard
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Initialize popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function(popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
    
    // Page transitions
    document.body.classList.add('page-enter');
    
    // Handle navigation links for smooth page transitions
    document.querySelectorAll('a:not([target="_blank"]):not([href^="#"]):not([href^="javascript"])').forEach(link => {
        link.addEventListener('click', function(e) {
            // Only intercept links to our own domain
            if (this.hostname === window.location.hostname) {
                e.preventDefault();
                
                // Add exit animation
                document.body.classList.remove('page-enter');
                document.body.classList.add('page-exit');
                
                // Navigate after animation completes
                setTimeout(() => {
                    window.location.href = this.href;
                }, 300);
            }
        });
    });
    
    // Add item hover effects
    document.querySelectorAll('.item-card').forEach(card => {
        card.classList.add('item-hover');
    });
    
    // Purchase button animations
    document.querySelectorAll('.purchase-button').forEach(button => {
        button.addEventListener('click', function(e) {
            // Find the parent item card
            const itemCard = this.closest('.item-card');
            if (itemCard) {
                itemCard.classList.add('item-purchase');
                setTimeout(() => {
                    itemCard.classList.remove('item-purchase');
                }, 500);
            }
        });
    });
    
    // Investment progress bars
    document.querySelectorAll('.investment-progress').forEach(progressContainer => {
        const progressBar = progressContainer.querySelector('.progress-fill');
        const progressPercent = parseInt(progressContainer.dataset.progress || 0);
        
        if (progressBar) {
            progressBar.style.width = `${Math.min(100, progressPercent)}%`;
            
            // Color based on progress
            if (progressPercent > 75) {
                progressBar.style.backgroundColor = 'var(--danger-color)';
            } else if (progressPercent > 50) {
                progressBar.style.backgroundColor = 'var(--warning-color)';
            }
        }
    });
    
    // Event countdown timers
    document.querySelectorAll('[data-countdown]').forEach(counter => {
        const targetTime = new Date(counter.dataset.countdown).getTime();
        
        // Update every second
        const timer = setInterval(() => {
            const now = new Date().getTime();
            const distance = targetTime - now;
            
            if (distance < 0) {
                clearInterval(timer);
                counter.innerHTML = "Expired";
                
                // Optional: add expired class for styling
                counter.classList.add('countdown-expired');
                
                // Optional: reload the page to get updated status
                if (counter.dataset.reload === 'true') {
                    location.reload();
                }
                
                return;
            }
            
            // Calculate time components
            const hours = Math.floor(distance / (1000 * 60 * 60));
            const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
            const seconds = Math.floor((distance % (1000 * 60)) / 1000);
            
            // Display countdown
            counter.innerHTML = `${hours}h ${minutes}m ${seconds}s`;
        }, 1000);
    });
    
    // Transaction request handlers
    const transactionForms = document.querySelectorAll('.transaction-form');
    if (transactionForms.length > 0) {
        transactionForms.forEach(form => {
            form.addEventListener('submit', function(e) {
                e.preventDefault();
                
                // Display loading state
                const submitButton = form.querySelector('button[type="submit"]');
                if (submitButton) {
                    submitButton.disabled = true;
                    submitButton.innerHTML = '<div class="loading-spinner"></div> Processing...';
                }
                
                // Get form data
                const formData = new FormData(form);
                
                // Submit the form with fetch API
                fetch(form.action, {
                    method: form.method,
                    body: formData,
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                })
                .then(response => response.json())
                .then(data => {
                    // Reset button state
                    if (submitButton) {
                        submitButton.disabled = false;
                        submitButton.innerHTML = submitButton.dataset.originalText || 'Submit';
                    }
                    
                    // Show success message or error
                    if (data.success) {
                        showNotification('success', data.message || 'Transaction completed successfully!');
                        
                        // Refresh data display if needed
                        if (data.refresh) {
                            location.reload();
                        }
                    } else {
                        showNotification('error', data.message || 'Transaction failed. Please try again.');
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    
                    // Reset button state
                    if (submitButton) {
                        submitButton.disabled = false;
                        submitButton.innerHTML = submitButton.dataset.originalText || 'Submit';
                    }
                    
                    showNotification('error', 'An error occurred. Please try again.');
                });
            });
            
            // Store original button text
            const submitButton = form.querySelector('button[type="submit"]');
            if (submitButton) {
                submitButton.dataset.originalText = submitButton.innerHTML;
            }
        });
    }
    
    // Function to show notifications
    function showNotification(type, message) {
        const notificationContainer = document.getElementById('notification-container');
        
        // Create container if it doesn't exist
        if (!notificationContainer) {
            const container = document.createElement('div');
            container.id = 'notification-container';
            container.style.position = 'fixed';
            container.style.top = '20px';
            container.style.right = '20px';
            container.style.zIndex = '9999';
            document.body.appendChild(container);
        }
        
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <div class="notification-content">
                <div class="notification-message">${message}</div>
                <button class="notification-close">&times;</button>
            </div>
        `;
        
        // Add to container
        (notificationContainer || document.getElementById('notification-container')).appendChild(notification);
        
        // Add entry animation
        setTimeout(() => {
            notification.classList.add('notification-show');
        }, 10);
        
        // Close button handler
        notification.querySelector('.notification-close').addEventListener('click', () => {
            notification.classList.remove('notification-show');
            notification.classList.add('notification-hide');
            
            // Remove from DOM after animation
            setTimeout(() => {
                notification.remove();
            }, 300);
        });
        
        // Auto close after 5 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.classList.remove('notification-show');
                notification.classList.add('notification-hide');
                
                // Remove from DOM after animation
                setTimeout(() => {
                    if (notification.parentNode) {
                        notification.remove();
                    }
                }, 300);
            }
        }, 5000);
    }
});

// Check for bot status periodically
function checkBotStatus() {
    fetch('/status')
        .then(response => response.json())
        .then(data => {
            const statusIndicator = document.getElementById('bot-status-indicator');
            if (statusIndicator) {
                statusIndicator.className = 'status-indicator ' + data.status;
                statusIndicator.textContent = data.status_message;
            }
        })
        .catch(error => {
            console.error('Error checking bot status:', error);
        });
}

// Check status every 30 seconds
if (document.getElementById('bot-status-indicator')) {
    checkBotStatus(); // Check immediately
    setInterval(checkBotStatus, 30000); // Then every 30 seconds
}