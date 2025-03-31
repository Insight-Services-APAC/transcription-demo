/**
 * API service for making HTTP requests
 */

/**
 * Make a GET request to the specified URL
 * @param {string} url - API endpoint URL
 * @returns {Promise<any>} Response data as JSON
 */
export async function fetchData(url) {
    try {
        const response = await fetch(url);
        
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('Fetch error:', error);
        throw error;
    }
}

/**
 * Make a POST request to the specified URL with JSON data
 * @param {string} url - API endpoint URL
 * @param {Object} data - Request body data
 * @returns {Promise<any>} Response data as JSON
 */
export async function postData(url, data) {
    try {
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data),
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('Fetch error:', error);
        throw error;
    }
}

/**
 * Make a POST request with FormData
 * @param {string} url - API endpoint URL
 * @param {FormData} formData - Form data
 * @returns {Promise<any>} Response data as JSON
 */
export async function postFormData(url, formData) {
    try {
        const response = await fetch(url, {
            method: 'POST',
            body: formData,
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('Fetch error:', error);
        throw error;
    }
}
