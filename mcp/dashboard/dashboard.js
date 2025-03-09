// Dashboard JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const statusValue = document.getElementById('status-value');
    const statusDetails = document.getElementById('status-details');
    const activityIndicator = document.getElementById('activity-indicator');
    const activityBar = document.getElementById('activity-bar');
    const urlsCrawled = document.getElementById('urls-crawled');
    const urlsFullyProcessed = document.getElementById('urls-fully-processed');
    const urlsDiscovered = document.getElementById('urls-discovered');
    const chunksProcessed = document.getElementById('chunks-processed');
    const chunksTotal = document.getElementById('chunks-total');
    const elapsedTime = document.getElementById('elapsed-time');
    const currentUrl = document.getElementById('current-url');
    const urlList = document.getElementById('url-list');
    const currentTime = document.getElementById('current-time');
    
    // Elapsed time tracking
    let startTime = null;
    let elapsedTimeInterval = null;

    // WebSocket connection
    let socket;
    let reconnectAttempts = 0;
    const maxReconnectAttempts = 5;
    const reconnectDelay = 3000;
    
    // Update current time
    function updateCurrentTime() {
        const now = new Date();
        currentTime.textContent = now.toLocaleString();
    }
    
    // Format date
    function formatDate(dateString) {
        if (!dateString) return '-';
        const date = new Date(dateString);
        return date.toLocaleString();
    }
    
    // Connect to WebSocket server
    function connectWebSocket() {
        if (socket) {
            socket.close();
        }
        
        socket = new WebSocket('ws://127.0.0.1:8765');
        
        socket.addEventListener('open', function(event) {
            console.log('Connected to WebSocket server');
            reconnectAttempts = 0;
            socket.send(JSON.stringify({ type: 'get_progress' }));
        });
        
        socket.addEventListener('close', function(event) {
            console.log('Disconnected from WebSocket server');
            if (reconnectAttempts < maxReconnectAttempts) {
                reconnectAttempts++;
                setTimeout(connectWebSocket, reconnectDelay);
                console.log(`Reconnecting (${reconnectAttempts}/${maxReconnectAttempts})...`);
            }
        });
        
        socket.addEventListener('error', function(event) {
            console.error('WebSocket error:', event);
        });
        
        socket.addEventListener('message', function(event) {
            try {
                const data = JSON.parse(event.data);
                updateDashboard(data);
            } catch (error) {
                console.error('Error parsing message:', error);
            }
        });
    }
    
    // Format elapsed time
    function formatElapsedTime(milliseconds) {
        if (!milliseconds) return '00:00:00';
        const totalSeconds = Math.floor(milliseconds / 1000);
        const hours = Math.floor(totalSeconds / 3600);
        const minutes = Math.floor((totalSeconds % 3600) / 60);
        const seconds = totalSeconds % 60;
        return [
            hours.toString().padStart(2, '0'),
            minutes.toString().padStart(2, '0'),
            seconds.toString().padStart(2, '0')
        ].join(':');
    }
    
    // Start elapsed time counter
    function startElapsedTimeCounter() {
        if (elapsedTimeInterval) {
            clearInterval(elapsedTimeInterval);
        }
        if (!startTime) {
            startTime = new Date();
        }
        function updateElapsedTime() {
            const now = new Date();
            const elapsed = now - startTime;
            elapsedTime.textContent = formatElapsedTime(elapsed);
        }
        updateElapsedTime();
        elapsedTimeInterval = setInterval(updateElapsedTime, 1000);
    }
    
    // Stop elapsed time counter
    function stopElapsedTimeCounter() {
        if (elapsedTimeInterval) {
            clearInterval(elapsedTimeInterval);
            elapsedTimeInterval = null;
        }
    }
    
    // Update dashboard with progress data
    function updateDashboard(data) {
        if (data.status) {
            statusValue.textContent = data.status.charAt(0).toUpperCase() + data.status.slice(1);
            statusValue.className = `status-${data.status}`;
            activityIndicator.textContent = data.status.charAt(0).toUpperCase() + data.status.slice(1);
            
            // Update batch size information
            const scrapeBatchSize = document.getElementById('scrape-batch-size');
            const embedBatchSize = document.getElementById('embed-batch-size');
            if (scrapeBatchSize && data.scrape_batch_size) {
                scrapeBatchSize.textContent = data.scrape_batch_size;
            }
            if (embedBatchSize && data.embed_batch_size) {
                embedBatchSize.textContent = data.embed_batch_size;
            }
            
            // Update status details based on phase
            if (data.status === 'crawling') {
                statusDetails.textContent = `Discovering URLs (${data.urls_crawled || 0}/${data.urls_discovered || 0})`;
                startElapsedTimeCounter();
                activityBar.style.display = 'block';
            } else if (data.status === 'scraping') {
                statusDetails.textContent = `Scraping content in batches of ${data.scrape_batch_size || 30} (${data.urls_fully_processed || 0}/${data.urls_discovered || 0})`;
                startElapsedTimeCounter();
                activityBar.style.display = 'block';
            } else if (data.status === 'embedding') {
                statusDetails.textContent = `Generating embeddings in batches of ${data.embed_batch_size || 20} (${data.chunks_processed || 0}/${data.chunks_total || 0})`;
                startElapsedTimeCounter();
                activityBar.style.display = 'block';
            } else if (data.status === 'complete' || data.status === 'idle') {
                statusDetails.textContent = data.status === 'complete' ? 'All URLs processed' : 'Waiting to start';
                stopElapsedTimeCounter();
                if (data.status === 'idle') {
                    startTime = null;
                    elapsedTime.textContent = '00:00:00';
                }
                activityBar.style.display = 'none';
            }
        }
        
        // Update metrics with new crawled/fully processed distinction
        urlsCrawled.textContent = data.urls_crawled || 0;
        urlsFullyProcessed.textContent = data.urls_fully_processed || 0;
        urlsDiscovered.textContent = data.urls_discovered || 0;
        chunksProcessed.textContent = data.chunks_processed || 0;
        chunksTotal.textContent = data.chunks_total || 0;
        
        if (data.current_url) {
            currentUrl.textContent = data.current_url;
        } else {
            currentUrl.textContent = '-';
        }
        
        if (data.urls_list && Array.isArray(data.urls_list)) {
            urlList.innerHTML = '';
            data.urls_list.forEach(url => {
                const li = document.createElement('li');
                li.textContent = url;
                urlList.appendChild(li);
            });
            if (data.urls_list.length === 0) {
                const li = document.createElement('li');
                li.textContent = 'No URLs processed yet';
                urlList.appendChild(li);
            }
        }
    }
    
    // Auto-refresh data periodically
    function autoRefreshData() {
        if (socket && socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify({ type: 'get_progress' }));
        } else {
            connectWebSocket();
        }
    }
    
    setInterval(autoRefreshData, 30000);
    updateCurrentTime();
    setInterval(updateCurrentTime, 1000);
    connectWebSocket();
});
