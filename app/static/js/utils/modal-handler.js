/**
 * Generic Modal Handler
 * Provides base functionality for handling modals across the application
 */
export class ModalHandler {
    constructor(modalId, options = {}) {
        this.modal = document.getElementById(modalId);
        this.options = {
            formId: options.formId || null,
            formUrlAttribute: options.formUrlAttribute || 'data-url-template',
            targetIdPlaceholder: options.targetIdPlaceholder || 'ID_PLACEHOLDER',
            contentSelectors: options.contentSelectors || {},
            ...options
        };
        
        this.init();
    }
    
    init() {
        if (!this.modal) return;
        
        // Set up event listener for modal showing
        this.modal.addEventListener('show.bs.modal', this.handleModalShow.bind(this));
    }
    
    handleModalShow(event) {
        // Button that triggered the modal
        const button = event.relatedTarget;
        if (!button) return;
        
        // Extract data attributes
        const dataAttributes = this.extractDataAttributes(button);
        
        // Update modal content based on data attributes
        this.updateModalContent(dataAttributes);
        
        // Update form action if needed
        this.updateFormAction(dataAttributes);
        
        // Call custom handler if provided
        if (typeof this.options.onShow === 'function') {
            this.options.onShow(this.modal, button, dataAttributes);
        }
    }
    
    extractDataAttributes(button) {
        const dataAttributes = {};
        Array.from(button.attributes)
            .filter(attr => attr.name.startsWith('data-'))
            .forEach(attr => {
                const key = attr.name.replace('data-', '');
                dataAttributes[key] = attr.value;
            });
        
        return dataAttributes;
    }
    
    updateModalContent(dataAttributes) {
        const contentSelectors = this.options.contentSelectors;
        
        // Update each content element with the corresponding data attribute
        Object.keys(contentSelectors).forEach(selector => {
            const element = this.modal.querySelector(selector);
            const attributeName = contentSelectors[selector];
            
            if (element && dataAttributes[attributeName]) {
                element.textContent = dataAttributes[attributeName];
            }
        });
    }
    
    updateFormAction(dataAttributes) {
        if (!this.options.formId) return;
        
        const form = this.modal.querySelector(`#${this.options.formId}`);
        if (!form) return;
        
        const urlTemplate = form.getAttribute(this.options.formUrlAttribute);
        if (!urlTemplate) return;
        
        const idKey = this.options.idAttribute || 'id';
        if (dataAttributes[idKey]) {
            form.action = urlTemplate.replace(
                this.options.targetIdPlaceholder,
                dataAttributes[idKey]
            );
        }
    }
}