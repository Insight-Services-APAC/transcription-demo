/**
 * Delete Modal Handler
 * Handles deletion confirmation modals throughout the application
 */
import { ModalHandler } from './modal-handler.js';

export class DeleteModalHandler extends ModalHandler {
    constructor(options = {}) {
        const defaultOptions = {
            formId: 'deleteForm',
            contentSelectors: {
                '#fileToDelete': 'file-name'
            },
            idAttribute: 'file-id',
            targetIdPlaceholder: 'FILE_ID_PLACEHOLDER'
        };
        
        super('deleteModal', { ...defaultOptions, ...options });
    }
}

// Initialize on document ready if not imported as a module
if (typeof window !== 'undefined' && !window.isModule) {
    document.addEventListener('DOMContentLoaded', function() {
        new DeleteModalHandler();
    });
}