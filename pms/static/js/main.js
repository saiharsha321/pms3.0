// Main JavaScript functionality
$(document).ready(function() {
    // Auto-hide alerts after 5 seconds
    setTimeout(function() {
        $('.alert').alert('close');
    }, 5000);

    // Enable tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Form validation enhancements
    $('form').on('submit', function() {
        const submitBtn = $(this).find('button[type="submit"]');
        submitBtn.prop('disabled', true).html('<i class="fas fa-spinner fa-spin me-1"></i>Processing...');
    });

    // Dynamic event loading for permission forms
    window.loadClubEvents = function(clubId, targetSelect) {
        if (clubId) {
            $.get('/api/events/' + clubId, function(data) {
                $(targetSelect).empty().append('<option value="">Select Event</option>');
                if (data.length > 0) {
                    $.each(data, function(index, event) {
                        $(targetSelect).append('<option value="' + event.id + '">' + event.name + '</option>');
                    });
                }
            }).fail(function() {
                console.error('Failed to load events');
            });
        }
    };

    // File upload preview (for future enhancement)
    window.previewFile = function(input, previewId) {
        const file = input.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = function(e) {
                $('#' + previewId).html(
                    '<div class="alert alert-info mt-2">' +
                    '<i class="fas fa-file me-2"></i>' + file.name +
                    ' (' + (file.size / 1024).toFixed(1) + ' KB)' +
                    '</div>'
                );
            };
            reader.readAsDataURL(file);
        }
    };
});

// Utility functions
window.utils = {
    formatDate: function(dateString) {
        const options = { year: 'numeric', month: 'short', day: 'numeric' };
        return new Date(dateString).toLocaleDateString(undefined, options);
    },
    
    showLoading: function(element) {
        $(element).html('<i class="fas fa-spinner fa-spin me-1"></i>Loading...').prop('disabled', true);
    },
    
    hideLoading: function(element, originalText) {
        $(element).html(originalText).prop('disabled', false);
    },
    
    showToast: function(message, type = 'info') {
        // Simple toast notification
        const toast = $('<div class="alert alert-' + type + ' alert-dismissible fade show position-fixed" style="top: 20px; right: 20px; z-index: 9999;">' +
                       message + 
                       '<button type="button" class="btn-close" data-bs-dismiss="alert"></button></div>');
        $('body').append(toast);
        setTimeout(() => toast.alert('close'), 5000);
    }
};