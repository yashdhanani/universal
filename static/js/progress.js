/**
 * COLORFUL REAL-TIME PROGRESS SYSTEM
 * Advanced progress bars with animations and real-time updates
 */

class ProgressManager {
    constructor() {
        this.progressBars = new Map();
        this.intervals = new Map();
        this.colors = {
            analyzing: '#3b82f6',    // Blue
            downloading: '#10b981',  // Green
            processing: '#f59e0b',   // Orange
            merging: '#8b5cf6',      // Purple
            completed: '#059669',    // Dark Green
            error: '#ef4444',        // Red
            warning: '#f59e0b'       // Orange
        };
        this.init();
    }

    init() {
        // Create progress container if it doesn't exist
        if (!document.getElementById('progress-container')) {
            this.createProgressContainer();
        }
        
        // Add CSS styles
        this.addProgressStyles();
    }

    createProgressContainer() {
        const container = document.createElement('div');
        container.id = 'progress-container';
        container.className = 'progress-container';
        
        // Insert after the main form
        const form = document.querySelector('form');
        if (form && form.parentNode) {
            form.parentNode.insertBefore(container, form.nextSibling);
        } else {
            document.body.appendChild(container);
        }
    }

    addProgressStyles() {
        if (document.getElementById('progress-styles')) return;
        
        const styles = document.createElement('style');
        styles.id = 'progress-styles';
        styles.textContent = `
            .progress-container {
                margin: 20px 0;
                padding: 0;
            }

            .progress-item {
                margin-bottom: 15px;
                padding: 15px;
                background: linear-gradient(135deg, #1f2937 0%, #374151 100%);
                border-radius: 12px;
                border: 1px solid #4b5563;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
                transition: all 0.3s ease;
                animation: slideIn 0.3s ease-out;
            }

            @keyframes slideIn {
                from {
                    opacity: 0;
                    transform: translateY(-10px);
                }
                to {
                    opacity: 1;
                    transform: translateY(0);
                }
            }

            .progress-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 10px;
            }

            .progress-title {
                font-weight: 600;
                color: #f9fafb;
                font-size: 14px;
                display: flex;
                align-items: center;
                gap: 8px;
            }

            .progress-percentage {
                font-weight: 700;
                font-size: 16px;
                color: #10b981;
                text-shadow: 0 0 10px rgba(16, 185, 129, 0.3);
                animation: pulse 2s infinite;
            }

            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.7; }
            }

            .progress-bar-container {
                position: relative;
                height: 8px;
                background: #374151;
                border-radius: 4px;
                overflow: hidden;
                box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.1);
            }

            .progress-bar {
                height: 100%;
                border-radius: 4px;
                transition: width 0.3s ease, background-color 0.3s ease;
                position: relative;
                overflow: hidden;
            }

            .progress-bar::before {
                content: '';
                position: absolute;
                top: 0;
                left: -100%;
                width: 100%;
                height: 100%;
                background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
                animation: shimmer 2s infinite;
            }

            @keyframes shimmer {
                0% { left: -100%; }
                100% { left: 100%; }
            }

            .progress-status {
                margin-top: 8px;
                font-size: 12px;
                color: #9ca3af;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }

            .progress-speed {
                color: #60a5fa;
                font-weight: 500;
            }

            .progress-eta {
                color: #fbbf24;
                font-weight: 500;
            }

            .progress-icon {
                width: 16px;
                height: 16px;
                animation: spin 2s linear infinite;
            }

            @keyframes spin {
                from { transform: rotate(0deg); }
                to { transform: rotate(360deg); }
            }

            .progress-completed .progress-icon {
                animation: none;
                color: #10b981;
            }

            .progress-error .progress-icon {
                animation: none;
                color: #ef4444;
            }

            .progress-details {
                margin-top: 10px;
                padding: 8px 12px;
                background: rgba(0, 0, 0, 0.2);
                border-radius: 6px;
                font-size: 11px;
                color: #d1d5db;
                font-family: 'Courier New', monospace;
                max-height: 60px;
                overflow-y: auto;
            }

            .progress-stages {
                display: flex;
                gap: 4px;
                margin-top: 8px;
            }

            .progress-stage {
                flex: 1;
                height: 3px;
                background: #374151;
                border-radius: 2px;
                transition: background-color 0.3s ease;
            }

            .progress-stage.active {
                background: linear-gradient(90deg, #3b82f6, #10b981);
                animation: stageGlow 1.5s ease-in-out infinite alternate;
            }

            .progress-stage.completed {
                background: #10b981;
            }

            @keyframes stageGlow {
                from { box-shadow: 0 0 5px rgba(59, 130, 246, 0.5); }
                to { box-shadow: 0 0 15px rgba(16, 185, 129, 0.8); }
            }

            /* Color variations */
            .progress-analyzing .progress-bar {
                background: linear-gradient(90deg, #3b82f6, #60a5fa);
            }

            .progress-downloading .progress-bar {
                background: linear-gradient(90deg, #10b981, #34d399);
            }

            .progress-processing .progress-bar {
                background: linear-gradient(90deg, #f59e0b, #fbbf24);
            }

            .progress-merging .progress-bar {
                background: linear-gradient(90deg, #8b5cf6, #a78bfa);
            }

            .progress-completed .progress-bar {
                background: linear-gradient(90deg, #059669, #10b981);
            }

            .progress-error .progress-bar {
                background: linear-gradient(90deg, #ef4444, #f87171);
            }

            /* Mobile responsive */
            @media (max-width: 640px) {
                .progress-item {
                    padding: 12px;
                    margin-bottom: 12px;
                }
                
                .progress-header {
                    flex-direction: column;
                    align-items: flex-start;
                    gap: 5px;
                }
                
                .progress-status {
                    flex-direction: column;
                    align-items: flex-start;
                    gap: 4px;
                }
            }
        `;
        
        document.head.appendChild(styles);
    }

    createProgressBar(id, title, type = 'analyzing') {
        const container = document.getElementById('progress-container');
        if (!container) return null;

        // Remove existing progress bar with same ID
        this.removeProgressBar(id);

        const progressItem = document.createElement('div');
        progressItem.id = `progress-${id}`;
        progressItem.className = `progress-item progress-${type}`;

        const stages = this.getStagesForType(type);
        const stagesHtml = stages.map((stage, index) => 
            `<div class="progress-stage" data-stage="${index}"></div>`
        ).join('');

        progressItem.innerHTML = `
            <div class="progress-header">
                <div class="progress-title">
                    <svg class="progress-icon" fill="currentColor" viewBox="0 0 20 20">
                        <path fill-rule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clip-rule="evenodd" />
                    </svg>
                    ${title}
                </div>
                <div class="progress-percentage">0%</div>
            </div>
            <div class="progress-bar-container">
                <div class="progress-bar" style="width: 0%"></div>
            </div>
            <div class="progress-stages">${stagesHtml}</div>
            <div class="progress-status">
                <span class="progress-current-stage">Initializing...</span>
                <div>
                    <span class="progress-speed"></span>
                    <span class="progress-eta"></span>
                </div>
            </div>
            <div class="progress-details" style="display: none;"></div>
        `;

        container.appendChild(progressItem);
        this.progressBars.set(id, {
            element: progressItem,
            type: type,
            stages: stages,
            currentStage: 0,
            startTime: Date.now()
        });

        return progressItem;
    }

    getStagesForType(type) {
        const stageMap = {
            analyzing: ['Connecting', 'Fetching Info', 'Processing Formats', 'Finalizing'],
            downloading: ['Preparing', 'Downloading', 'Processing', 'Completing'],
            processing: ['Initializing', 'Converting', 'Optimizing', 'Finalizing'],
            merging: ['Preparing', 'Merging Audio', 'Merging Video', 'Completing']
        };
        return stageMap[type] || stageMap.analyzing;
    }

    updateProgress(id, percentage, status = '', details = '', speed = '', eta = '') {
        const progressData = this.progressBars.get(id);
        if (!progressData) return;

        const element = progressData.element;
        const progressBar = element.querySelector('.progress-bar');
        const progressPercentage = element.querySelector('.progress-percentage');
        const progressStatus = element.querySelector('.progress-current-stage');
        const progressDetails = element.querySelector('.progress-details');
        const progressSpeed = element.querySelector('.progress-speed');
        const progressEta = element.querySelector('.progress-eta');

        // Update percentage
        percentage = Math.max(0, Math.min(100, percentage));
        progressBar.style.width = `${percentage}%`;
        progressPercentage.textContent = `${Math.round(percentage)}%`;

        // Update status
        if (status) {
            progressStatus.textContent = status;
        }

        // Update details
        if (details) {
            progressDetails.style.display = 'block';
            progressDetails.textContent = details;
        }

        // Update speed and ETA
        if (speed) {
            progressSpeed.textContent = `${speed}`;
        }
        if (eta) {
            progressEta.textContent = `ETA: ${eta}`;
        }

        // Update stages
        this.updateStages(id, percentage);

        // Add completion effects
        if (percentage >= 100) {
            this.completeProgress(id);
        }
    }

    updateStages(id, percentage) {
        const progressData = this.progressBars.get(id);
        if (!progressData) return;

        const stages = progressData.element.querySelectorAll('.progress-stage');
        const stageCount = stages.length;
        const currentStageIndex = Math.floor((percentage / 100) * stageCount);

        stages.forEach((stage, index) => {
            stage.classList.remove('active', 'completed');
            if (index < currentStageIndex) {
                stage.classList.add('completed');
            } else if (index === currentStageIndex && percentage < 100) {
                stage.classList.add('active');
            }
        });

        // Update current stage text
        if (currentStageIndex < progressData.stages.length) {
            const statusElement = progressData.element.querySelector('.progress-current-stage');
            statusElement.textContent = progressData.stages[currentStageIndex];
        }
    }

    completeProgress(id, message = 'Completed successfully!') {
        const progressData = this.progressBars.get(id);
        if (!progressData) return;

        const element = progressData.element;
        element.classList.remove(`progress-${progressData.type}`);
        element.classList.add('progress-completed');

        const icon = element.querySelector('.progress-icon');
        icon.innerHTML = `
            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
        `;

        const statusElement = element.querySelector('.progress-current-stage');
        statusElement.textContent = message;

        // Auto-remove after 5 seconds
        setTimeout(() => {
            this.removeProgressBar(id);
        }, 5000);
    }

    errorProgress(id, message = 'An error occurred') {
        const progressData = this.progressBars.get(id);
        if (!progressData) return;

        const element = progressData.element;
        element.classList.remove(`progress-${progressData.type}`);
        element.classList.add('progress-error');

        const icon = element.querySelector('.progress-icon');
        icon.innerHTML = `
            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
        `;

        const statusElement = element.querySelector('.progress-current-stage');
        statusElement.textContent = message;

        // Auto-remove after 10 seconds
        setTimeout(() => {
            this.removeProgressBar(id);
        }, 10000);
    }

    removeProgressBar(id) {
        const progressData = this.progressBars.get(id);
        if (progressData && progressData.element) {
            progressData.element.style.animation = 'slideOut 0.3s ease-in';
            setTimeout(() => {
                if (progressData.element.parentNode) {
                    progressData.element.parentNode.removeChild(progressData.element);
                }
            }, 300);
        }
        
        this.progressBars.delete(id);
        
        if (this.intervals.has(id)) {
            clearInterval(this.intervals.get(id));
            this.intervals.delete(id);
        }
    }

    startAnalysisProgress(url) {
        const id = 'analysis-' + Date.now();
        this.createProgressBar(id, '🔍 Analyzing Video', 'analyzing');
        
        let progress = 0;
        const interval = setInterval(() => {
            progress += Math.random() * 15;
            if (progress > 95) progress = 95;
            
            const stages = ['Connecting to server...', 'Fetching video information...', 'Processing available formats...', 'Finalizing analysis...'];
            const currentStage = Math.floor((progress / 100) * stages.length);
            const status = stages[currentStage] || stages[stages.length - 1];
            
            this.updateProgress(id, progress, status);
        }, 500);
        
        this.intervals.set(id, interval);
        return id;
    }

    completeAnalysisProgress(id, formatCount) {
        if (this.intervals.has(id)) {
            clearInterval(this.intervals.get(id));
            this.intervals.delete(id);
        }
        
        this.updateProgress(id, 100, 'Analysis completed!', `Found ${formatCount} formats`);
        this.completeProgress(id, `✅ Found ${formatCount} formats available`);
    }

    startDownloadProgress(filename) {
        const id = 'download-' + Date.now();
        this.createProgressBar(id, `📥 Downloading: ${filename}`, 'downloading');
        return id;
    }

    updateDownloadProgress(id, percentage, speed = '', eta = '', details = '') {
        const status = percentage < 100 ? 'Downloading...' : 'Download completed!';
        this.updateProgress(id, percentage, status, details, speed, eta);
        
        if (percentage >= 100) {
            this.completeProgress(id, '✅ Download completed successfully!');
        }
    }
}

// Initialize progress manager when DOM is ready
function initializeProgressManager() {
    if (!window.progressManager) {
        window.progressManager = new ProgressManager();
        
        // Add slideOut animation
        const slideOutStyle = document.createElement('style');
        slideOutStyle.textContent = `
            @keyframes slideOut {
                from {
                    opacity: 1;
                    transform: translateY(0);
                }
                to {
                    opacity: 0;
                    transform: translateY(-10px);
                }
            }
        `;
        document.head.appendChild(slideOutStyle);
    }
}

// Initialize immediately if DOM is ready, otherwise wait
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeProgressManager);
} else {
    initializeProgressManager();
}

// Also ensure it's available globally
window.initializeProgressManager = initializeProgressManager;