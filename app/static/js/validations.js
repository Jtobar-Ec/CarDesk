/**
 * Sistema de validaciones para formularios
 * Kardex - Sistema de Inventario
 */

class FormValidator {
    constructor(formId) {
        this.form = document.getElementById(formId);
        this.errors = {};
        this.rules = {};
        
        if (this.form) {
            this.init();
        }
    }
    
    init() {
        // Agregar event listeners
        this.form.addEventListener('submit', (e) => this.handleSubmit(e));
        
        // Validación en tiempo real
        const inputs = this.form.querySelectorAll('input, select, textarea');
        inputs.forEach(input => {
            input.addEventListener('blur', () => this.validateField(input));
            input.addEventListener('input', () => this.clearFieldError(input));
        });
    }
    
    // Agregar reglas de validación
    addRule(fieldName, rules) {
        this.rules[fieldName] = rules;
        return this;
    }
    
    // Validar campo individual
    validateField(field) {
        const fieldName = field.name || field.id;
        const rules = this.rules[fieldName];
        
        if (!rules) return true;
        
        const value = field.value.trim();
        let isValid = true;
        
        // Limpiar errores previos
        this.clearFieldError(field);
        
        // Aplicar reglas
        for (const rule of rules) {
            if (!this.applyRule(value, rule, field)) {
                this.showFieldError(field, rule.message);
                isValid = false;
                break;
            }
        }
        
        return isValid;
    }
    
    // Aplicar regla específica
    applyRule(value, rule, field) {
        switch (rule.type) {
            case 'required':
                return value.length > 0;
                
            case 'minLength':
                return value.length >= rule.value;
                
            case 'maxLength':
                return value.length <= rule.value;
                
            case 'email':
                return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
                
            case 'numeric':
                return /^\d+$/.test(value);
                
            case 'decimal':
                return /^\d+(\.\d{1,2})?$/.test(value);
                
            case 'phone':
                return /^[\d\-\+\(\)\s]+$/.test(value) && value.length >= 7;
                
            case 'ci':
                return /^\d{10}$/.test(value);
                
            case 'ruc':
                return /^\d{13}$/.test(value);
                
            case 'alphanumeric':
                return /^[a-zA-Z0-9\s]+$/.test(value);
                
            case 'min':
                return parseFloat(value) >= rule.value;
                
            case 'max':
                return parseFloat(value) <= rule.value;
                
            case 'custom':
                return rule.validator(value, field);
                
            default:
                return true;
        }
    }
    
    // Mostrar error en campo
    showFieldError(field, message) {
        field.classList.add('is-invalid');
        
        // Buscar o crear div de error
        let errorDiv = field.parentNode.querySelector('.invalid-feedback');
        if (!errorDiv) {
            errorDiv = document.createElement('div');
            errorDiv.className = 'invalid-feedback';
            field.parentNode.appendChild(errorDiv);
        }
        
        errorDiv.textContent = message;
        errorDiv.style.display = 'block';
    }
    
    // Limpiar error de campo
    clearFieldError(field) {
        field.classList.remove('is-invalid');
        const errorDiv = field.parentNode.querySelector('.invalid-feedback');
        if (errorDiv) {
            errorDiv.style.display = 'none';
        }
    }
    
    // Validar todo el formulario
    validate() {
        let isValid = true;
        const fields = this.form.querySelectorAll('input, select, textarea');
        
        fields.forEach(field => {
            if (!this.validateField(field)) {
                isValid = false;
            }
        });
        
        return isValid;
    }
    
    // Manejar envío del formulario
    handleSubmit(e) {
        if (!this.validate()) {
            e.preventDefault();
            this.showGeneralError('Por favor, corrija los errores en el formulario');
            
            // Scroll al primer error
            const firstError = this.form.querySelector('.is-invalid');
            if (firstError) {
                firstError.scrollIntoView({ behavior: 'smooth', block: 'center' });
                firstError.focus();
            }
        }
    }
    
    // Mostrar error general
    showGeneralError(message) {
        let alertDiv = this.form.querySelector('.alert-danger');
        if (!alertDiv) {
            alertDiv = document.createElement('div');
            alertDiv.className = 'alert alert-danger alert-dismissible fade show';
            alertDiv.innerHTML = `
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            `;
            this.form.insertBefore(alertDiv, this.form.firstChild);
        } else {
            alertDiv.querySelector('span, div, text').textContent = message;
            alertDiv.style.display = 'block';
        }
        
        // Auto-ocultar después de 5 segundos
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.remove();
            }
        }, 5000);
    }
}

// Validaciones comunes predefinidas
const CommonValidations = {
    required: (message = 'Este campo es obligatorio') => ({
        type: 'required',
        message
    }),
    
    email: (message = 'Ingrese un email válido') => ({
        type: 'email',
        message
    }),
    
    minLength: (length, message = `Mínimo ${length} caracteres`) => ({
        type: 'minLength',
        value: length,
        message
    }),
    
    maxLength: (length, message = `Máximo ${length} caracteres`) => ({
        type: 'maxLength',
        value: length,
        message
    }),
    
    numeric: (message = 'Solo se permiten números') => ({
        type: 'numeric',
        message
    }),
    
    decimal: (message = 'Ingrese un número válido (ej: 10.50)') => ({
        type: 'decimal',
        message
    }),
    
    phone: (message = 'Ingrese un teléfono válido') => ({
        type: 'phone',
        message
    }),
    
    ci: (message = 'Cédula debe tener 10 dígitos') => ({
        type: 'ci',
        message
    }),
    
    ruc: (message = 'RUC debe tener 13 dígitos') => ({
        type: 'ruc',
        message
    }),
    
    min: (value, message = `Valor mínimo: ${value}`) => ({
        type: 'min',
        value,
        message
    }),
    
    max: (value, message = `Valor máximo: ${value}`) => ({
        type: 'max',
        value,
        message
    }),
    
    alphanumeric: (message = 'Solo letras, números y espacios') => ({
        type: 'alphanumeric',
        message
    })
};

// Utilidades adicionales
const ValidationUtils = {
    // Formatear números
    formatNumber: (input) => {
        input.addEventListener('input', function() {
            let value = this.value.replace(/[^\d.]/g, '');
            if (value.split('.').length > 2) {
                value = value.substring(0, value.lastIndexOf('.'));
            }
            this.value = value;
        });
    },
    
    // Formatear solo números enteros
    formatInteger: (input) => {
        input.addEventListener('input', function() {
            this.value = this.value.replace(/[^\d]/g, '');
        });
    },
    
    // Formatear teléfono
    formatPhone: (input) => {
        input.addEventListener('input', function() {
            this.value = this.value.replace(/[^\d\-\+\(\)\s]/g, '');
        });
    },
    
    // Capitalizar primera letra
    capitalize: (input) => {
        input.addEventListener('blur', function() {
            this.value = this.value.charAt(0).toUpperCase() + this.value.slice(1).toLowerCase();
        });
    },
    
    // Convertir a mayúsculas
    uppercase: (input) => {
        input.addEventListener('input', function() {
            this.value = this.value.toUpperCase();
        });
    }
};

// Exportar para uso global
window.FormValidator = FormValidator;
window.CommonValidations = CommonValidations;
window.ValidationUtils = ValidationUtils;