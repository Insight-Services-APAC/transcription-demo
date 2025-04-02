/**
 * API service for making HTTP requests
 */

/**
 * Default error handler for API requests
 * @param {Error} error - The error object
 * @returns {Object} Standardized error object
 */
const defaultErrorHandler = (error) => {
    console.error('API request failed:', error);
    return {
        success: false,
        error: error.message || 'An unknown error occurred',
        status: error.status || 500
    };
};

/**
 * Make a GET request to the specified URL
 * @param {string} url - API endpoint URL
 * @param {Object} options - Additional fetch options
 * @returns {Promise<any>} Response data as JSON
 */
export async function fetchData(url, options = {}) {
    try {
        const response = await fetch(url, {
            method: 'GET',
            headers: {
                'Accept': 'application/json',
                ...options.headers
            },
            ...options
        });
        
        if (!response.ok) {
            throw {
                message: `HTTP error! Status: ${response.status}`,
                status: response.status
            };
        }
        
        return await response.json();
    } catch (error) {
        return options.errorHandler ? 
            options.errorHandler(error) : 
            defaultErrorHandler(error);
    }
}

/**
 * Make a POST request to the specified URL with JSON data
 * @param {string} url - API endpoint URL
 * @param {Object} data - Request body data
 * @param {Object} options - Additional fetch options
 * @returns {Promise<any>} Response data as JSON
 */
export async function postData(url, data, options = {}) {
    try {
        const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
        
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                ...(csrfToken ? { 'X-CSRFToken': csrfToken } : {}),
                ...options.headers
            },
            body: JSON.stringify(data),
            ...options
        });
        
        if (!response.ok) {
            throw {
                message: `HTTP error! Status: ${response.status}`,
                status: response.status
            };
        }
        
        return await response.json();
    } catch (error) {
        return options.errorHandler ? 
            options.errorHandler(error) : 
            defaultErrorHandler(error);
    }
}

/**
 * Make a POST request with FormData
 * @param {string} url - API endpoint URL
 * @param {FormData} formData - Form data
 * @param {Object} options - Additional fetch options
 * @returns {Promise<any>} Response data as JSON
 */
export async function postFormData(url, formData, options = {}) {
    try {
        const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
        
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Accept': 'application/json',
                ...(csrfToken ? { 'X-CSRFToken': csrfToken } : {}),
                ...options.headers
            },
            body: formData,
            ...options
        });
        
        if (!response.ok) {
            throw {
                message: `HTTP error! Status: ${response.status}`,
                status: response.status
            };
        }
        
        return await response.json();
    } catch (error) {
        return options.errorHandler ? 
            options.errorHandler(error) : 
            defaultErrorHandler(error);
    }
}

/**
 * CSRF-safe wrapper for fetch
 * @param {string} url - URL to fetch
 * @param {Object} options - Fetch options
 * @returns {Promise<Response>} Fetch response
 */
export function fetchWithCsrf(url, options = {}) {
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
    
    // Only add CSRF token for non-GET requests
    if (!options.method || options.method.toUpperCase() !== 'GET') {
        options.headers = {
            ...options.headers,
            'X-CSRFToken': csrfToken
        };
    }
    
    return fetch(url, options);
}