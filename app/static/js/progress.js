// Progress Analytics JavaScript

document.addEventListener('DOMContentLoaded', function() {
    initTabs();
    initProgressBar();
    initConfidenceBars();
    renderCharts();
    initConfidenceChangeText();
});

/**
 * Initialize the confidence bars with proper widths based on data-confidence attribute
 */
function initConfidenceBars() {
    const confidenceBars = document.querySelectorAll('.confidence-bar');
    confidenceBars.forEach(bar => {
        const confidence = bar.getAttribute('data-confidence');
        if (confidence) {
            setTimeout(() => {
                bar.style.width = confidence + '%';
            }, 300);
        }
    });
}

/**
 * Initialize confidence change text by populating it dynamically to avoid CSS validation issues
 */
function initConfidenceChangeText() {
    // For the confidence text in the overview section
    const overviewConfidenceText = document.querySelector('#confidence-change-text');
    if (overviewConfidenceText) {
        const direction = overviewConfidenceText.getAttribute('data-change-dir');
        const value = overviewConfidenceText.getAttribute('data-change-val');
        overviewConfidenceText.textContent = `${direction === 'increase' ? 'Improving' : 'Declining'} by ${value}% over last 90 days`;
    }
    
    // For the confidence text in the learning rate section
    const learningConfidenceText = document.querySelector('#confidence-change-text[data-direction]');
    if (learningConfidenceText) {
        const direction = learningConfidenceText.getAttribute('data-direction');
        const value = learningConfidenceText.getAttribute('data-value');
        learningConfidenceText.textContent = `Your confidence has ${direction} by ${value}% over the last 90 days.`;
    }
}

/**
 * Initialize tab navigation
 */
function initTabs() {
    const tabButtons = document.querySelectorAll('.tab-button');
    const tabPanes = document.querySelectorAll('.tab-pane');
    
    tabButtons.forEach(button => {
        button.addEventListener('click', function() {
            // Remove active class from all buttons and panes
            tabButtons.forEach(btn => btn.classList.remove('active'));
            tabPanes.forEach(pane => pane.classList.remove('active'));
            
            // Add active class to current button
            button.classList.add('active');
            
            // Show the corresponding tab pane
            const tabId = button.getAttribute('data-tab');
            document.getElementById(`${tabId}-tab`).classList.add('active');
        });
    });
}

/**
 * Initialize progress bar animation
 */
function initProgressBar() {
    const progressBarFill = document.getElementById('progress-bar-fill');
    if (progressBarFill) {
        setTimeout(() => {
            const percentage = progressBarFill.getAttribute('data-percentage');
            progressBarFill.style.width = percentage + '%';
            progressBarFill.classList.add('animate');
        }, 300);
    }
}

/**
 * Render all charts for the analytics page
 */
function renderCharts() {
    renderSubjectsChart();
    
    // Get chart data from the data attribute
    const chartDataElement = document.getElementById('chart-data');
    if (!chartDataElement) return;
    
    const chartDataJson = chartDataElement.getAttribute('data-chart');
    const chartData = JSON.parse(chartDataJson);
    
    // Render analytics charts if data is available
    if (chartData.confidenceDistribution) {
        renderConfidenceDistributionChart(chartData.confidenceDistribution);
    }
    
    if (chartData.confidenceTrend) {
        renderConfidenceTrendChart(chartData.confidenceTrend);
    }
    
    if (chartData.subjectPerformance) {
        renderSubjectPerformanceChart(chartData.subjectPerformance);
    }
    
    if (chartData.forgettingCurve) {
        renderForgettingCurveChart(chartData.forgettingCurve);
    }
}

/**
 * Render the subjects breakdown chart
 */
function renderSubjectsChart() {
    // Get subject data from the data attribute
    const subjectDataElement = document.getElementById('subject-data');
    if (!subjectDataElement) return;
    
    const subjectDataJson = subjectDataElement.getAttribute('data-subjects');
    const subjectData = JSON.parse(subjectDataJson);
    
    // Prepare data for subjects chart
    const subjects = [];
    const completed = [];
    const total = [];
    const colors = [];
    
    // Process the data
    for (const [subjectId, stats] of Object.entries(subjectData)) {
        subjects.push(stats.name);
        completed.push(stats.completed);
        total.push(stats.total);
        
        // Generate a color based on subject (for consistent colors)
        const hue = (parseInt(subjectId) * 137.5) % 360;
        colors.push(`hsl(${hue}, 70%, 60%)`);
    }
    
    // Create subjects chart
    const subjectsCtx = document.getElementById('subjects-chart').getContext('2d');
    const subjectsChart = new Chart(subjectsCtx, {
        type: 'bar',
        data: {
            labels: subjects,
            datasets: [
                {
                    label: 'Completed',
                    data: completed,
                    backgroundColor: colors
                },
                {
                    label: 'Total',
                    data: total,
                    backgroundColor: colors.map(c => c.replace('60%', '90%')),
                    borderWidth: 1,
                    borderColor: colors
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        precision: 0
                    }
                }
            }
        }
    });
}

/**
 * Render the confidence distribution doughnut chart
 */
function renderConfidenceDistributionChart(data) {
    const confidenceDistCtx = document.getElementById('confidence-distribution-chart').getContext('2d');
    const confidenceDistChart = new Chart(confidenceDistCtx, {
        type: 'doughnut',
        data: data,
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    position: 'right',
                }
            }
        }
    });
}

/**
 * Render the confidence trend line chart
 */
function renderConfidenceTrendChart(data) {
    const confidenceTrendCtx = document.getElementById('confidence-trend-chart').getContext('2d');
    const confidenceTrendChart = new Chart(confidenceTrendCtx, {
        type: 'line',
        data: data,
        options: {
            responsive: true,
            maintainAspectRatio: true,
            scales: {
                y: {
                    beginAtZero: false,
                    min: 1,
                    max: 5,
                    ticks: {
                        stepSize: 1
                    }
                }
            }
        }
    });
}

/**
 * Render the subject performance bar chart
 */
function renderSubjectPerformanceChart(data) {
    const subjectPerfCtx = document.getElementById('subject-performance-chart').getContext('2d');
    const subjectPerfChart = new Chart(subjectPerfCtx, {
        type: 'bar',
        data: data,
        options: {
            responsive: true,
            maintainAspectRatio: true,
            scales: {
                y: {
                    beginAtZero: true,
                    max: 5,
                    ticks: {
                        stepSize: 1
                    }
                }
            }
        }
    });
}

/**
 * Render the forgetting curve line chart
 */
function renderForgettingCurveChart(data) {
    const forgettingCurveCtx = document.getElementById('forgetting-curve-chart').getContext('2d');
    const forgettingCurveChart = new Chart(forgettingCurveCtx, {
        type: 'line',
        data: data,
        options: {
            responsive: true,
            maintainAspectRatio: true,
            scales: {
                y: {
                    title: {
                        display: true,
                        text: 'Confidence Change'
                    }
                }
            }
        }
    });
}
