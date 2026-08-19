/**
 * Main application JavaScript
 */
document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Handle form submissions with file inputs
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            // Find file inputs
            const fileInputs = form.querySelectorAll('input[type="file"]');
            fileInputs.forEach(fileInput => {
                if (fileInput.required && fileInput.files.length === 0) {
                    e.preventDefault();
                    showToast('Please select a file to upload', 'error');
                }
            });
        });
    });
    
    // Show toast notification
    window.showToast = function(message, type = 'info') {
        // Create toast container if it doesn't exist
        let toastContainer = document.querySelector('.toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
            document.body.appendChild(toastContainer);
        }
        
        // Create toast element
        const toastEl = document.createElement('div');
        toastEl.className = `toast align-items-center ${type === 'error' ? 'text-bg-danger' : 'text-bg-primary'}`;
        toastEl.setAttribute('role', 'alert');
        toastEl.setAttribute('aria-live', 'assertive');
        toastEl.setAttribute('aria-atomic', 'true');
        
        // Toast content
        toastEl.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">${message}</div>
                <button type="button" class="btn-close me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        `;
        
        // Add toast to container
        toastContainer.appendChild(toastEl);
        
        // Initialize and show the toast
        const toast = new bootstrap.Toast(toastEl, {
            autohide: true,
            delay: 5000
        });
        toast.show();
        
        // Remove toast element after it's hidden
        toastEl.addEventListener('hidden.bs.toast', function() {
            toastEl.remove();
        });
    };
    
    // ---------------------------------------------------------------------
    // Podcast job management integration (list + cancel)
    // ---------------------------------------------------------------------

    const jobsTable = document.getElementById('jobs-table');
    if (jobsTable) {
        // Fetch jobs initially
        fetchJobs();

        // Delegate click handler for cancel buttons
        jobsTable.addEventListener('click', function (e) {
            if (e.target && e.target.matches('.cancel-job-btn')) {
                const jobId = e.target.dataset.jobId;
                if (confirm('Cancel this job?')) {
                    cancelJob(jobId).then(fetchJobs);
                }
            }
        });
    }

    // ---------------- Helper functions ----------------------------------

    function getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
    }

    async function fetchJobs(page = 1) {
        try {
            const resp = await fetch(`/podcast/jobs/?page=${page}`);
            if (!resp.ok) throw new Error('Failed to fetch jobs list');
            const data = await resp.json();
            renderJobs(data.results);
        } catch (err) {
            console.error(err);
            showToast(err.message || 'Could not load jobs', 'error');
        }
    }

    async function cancelJob(jobId) {
        try {
            const resp = await fetch(`/podcast/jobs/${jobId}/cancel/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken') || ''
                }
            });
            if (!resp.ok) {
                const err = await resp.json();
                throw new Error(err.detail || 'Cancellation failed');
            }
            showToast('Job cancellation requested');
        } catch (err) {
            console.error(err);
            showToast(err.message || 'Could not cancel job', 'error');
        }
    }

    function renderJobs(jobs) {
        const tbody = jobsTable.querySelector('tbody');
        if (!tbody) return;
        tbody.innerHTML = jobs.map(jobRowHTML).join('');
    }

    function jobRowHTML(job) {
        return `
            <tr>
                <td>${job.id}</td>
                <td>${job.podcast_topic || ''}</td>
                <td>${job.status}</td>
                <td>${job.audio_percent || 0}%</td>
                <td>${job.lipsync_percent || 0}%</td>
                <td>
                    ${ job.status === 'pending' || job.status === 'processing' ? `<button class="btn btn-sm btn-danger cancel-job-btn" data-job-id="${job.id}">Cancel</button>` : ''}
                </td>
            </tr>
        `;
    }
});
