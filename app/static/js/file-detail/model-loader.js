/**
 * Model Loader for File Detail page
 * Loads transcription models for the model selection modal
 */
document.addEventListener('DOMContentLoaded', function() {
    const modelSelect = document.getElementById('transcription_model');
    const modelNameInput = document.getElementById('model_name');
    const modelLocaleInput = document.getElementById('model_locale');
    const fileApiUrl = document.body.dataset.fileApiUrl;
    const modelsUrl = document.body.dataset.modelsUrl;
    
    if (modelSelect && modelsUrl) {
        // Show loading option
        const loadingOption = document.createElement('option');
        loadingOption.textContent = 'Loading models...';
        loadingOption.disabled = true;
        modelSelect.appendChild(loadingOption);
        
        // Fetch models
        window.fetchWithCsrf(modelsUrl)
            .then(response => response.json())
            .then(data => {
                // Remove loading option
                modelSelect.removeChild(loadingOption);
                
                // Add models from the API
                if (data.models && data.models.length > 0) {
                    data.models.forEach(model => {
                        const option = document.createElement('option');
                        option.value = model.id;
                        option.dataset.name = model.name;
                        option.dataset.locale = model.locale;  // Store locale in dataset
                        option.textContent = `${model.displayName}`;
                        modelSelect.appendChild(option);
                    });
                }
            })
            .catch(error => {
                console.error('Error loading models:', error);
                const errorOption = document.createElement('option');
                errorOption.textContent = 'Error loading models';
                errorOption.disabled = true;
                modelSelect.innerHTML = '';
                modelSelect.appendChild(document.createElement('option')).textContent = '-- Default Model --';
                modelSelect.appendChild(errorOption);
            });
        
        // Update model name and locale when selection changes
        modelSelect.addEventListener('change', function() {
            const selectedOption = modelSelect.options[modelSelect.selectedIndex];
            if (selectedOption && selectedOption.dataset) {
                // Set model name
                if (selectedOption.dataset.name) {
                    modelNameInput.value = selectedOption.dataset.name;
                } else {
                    modelNameInput.value = '';
                }
                
                // Set model locale
                if (modelLocaleInput) {
                    modelLocaleInput.value = selectedOption.dataset.locale || '';
                }
            }
        });
    }
});