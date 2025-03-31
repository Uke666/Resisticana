/**
 * Main JavaScript file for Discord Economy Bot Dashboard
 */

// Initialize Feather icons when the DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    feather.replace();
    
    // Initialization for tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Initialization for popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
});

/**
 * Format currency values consistently
 * @param {number} amount - The amount to format
 * @returns {string} Formatted currency string
 */
function formatCurrency(amount) {
    return '$' + amount.toLocaleString();
}

/**
 * Format dates in a consistent way
 * @param {Date|string} date - The date to format
 * @returns {string} Formatted date string
 */
function formatDate(date) {
    if (typeof date === 'string') {
        date = new Date(date);
    }
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
}

/**
 * Calculate time difference in a human-readable format
 * @param {Date|string} date - The date to calculate difference from
 * @returns {string} Human readable time difference
 */
function timeAgo(date) {
    if (typeof date === 'string') {
        date = new Date(date);
    }
    
    const seconds = Math.floor((new Date() - date) / 1000);
    
    let interval = Math.floor(seconds / 31536000);
    if (interval > 1) {
        return interval + ' years ago';
    }
    
    interval = Math.floor(seconds / 2592000);
    if (interval > 1) {
        return interval + ' months ago';
    }
    
    interval = Math.floor(seconds / 86400);
    if (interval > 1) {
        return interval + ' days ago';
    }
    
    interval = Math.floor(seconds / 3600);
    if (interval > 1) {
        return interval + ' hours ago';
    }
    
    interval = Math.floor(seconds / 60);
    if (interval > 1) {
        return interval + ' minutes ago';
    }
    
    if (seconds < 10) {
        return 'just now';
    }
    
    return Math.floor(seconds) + ' seconds ago';
}