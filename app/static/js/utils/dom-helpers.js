/**
 * Utility functions for DOM manipulation
 */

/**
 * Get element by ID with type checking
 * @param {string} id - Element ID
 * @returns {HTMLElement|null} DOM element or null if not found
 */
export function getElement(id) {
    return document.getElementById(id);
}

/**
 * Create an element with attributes and content
 * @param {string} tag - HTML tag
 * @param {Object} attributes - Element attributes
 * @param {string|HTMLElement} content - Element content
 * @returns {HTMLElement} Created element
 */
export function createElement(tag, attributes = {}, content = '') {
    const element = document.createElement(tag);
    
    Object.entries(attributes).forEach(([key, value]) => {
        element.setAttribute(key, value);
    });
    
    if (typeof content === 'string') {
        element.innerHTML = content;
    } else if (content instanceof HTMLElement) {
        element.appendChild(content);
    }
    
    return element;
}

/**
 * Prevent default event behavior
 * @param {Event} e - DOM event
 */
export function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
}
