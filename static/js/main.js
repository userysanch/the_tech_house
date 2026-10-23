// The Tech House — Global JS

// Format currency
function formatearMoneda(valor) {
    return new Intl.NumberFormat('es-ES', {
        style: 'currency',
        currency: 'GTQ'
    }).format(valor);
}

// Flash message auto-dismiss
document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.alert-dp').forEach(function(alert) {
        setTimeout(function() {
            alert.style.transition = 'opacity .3s';
            alert.style.opacity = '0';
            setTimeout(function() { alert.remove(); }, 300);
        }, 5000);
    });
});
