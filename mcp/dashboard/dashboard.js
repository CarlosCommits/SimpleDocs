// Dashboard JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const statusValue = document.getElementById('status-value');
    const activityIndicator = document.getElementById('activity-indicator');
    const activityBar = document.getElementById('activity-bar');
    const urlsProcessed = document.getElementById('urls-processed');
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
        // Close existing connection if any
        if (socket) {
            socket.close();
        }
        
        // Create new connection
        socket = new WebSocket('ws://127.0.0.1:8765');
        
        // Connection opened
        socket.addEventListener('open', function(event) {
            console.log('Connected to WebSocket server');
            reconnectAttempts = 0;
            
            // Request current progress
            socket.send(JSON.stringify({
                type: 'get_progress'
            }));
        });
        
        // Connection closed
        socket.addEventListener('close', function(event) {
            console.log('Disconnected from WebSocket server');
            
            // Attempt to reconnect
            if (reconnectAttempts < maxReconnectAttempts) {
                reconnectAttempts++;
                setTimeout(connectWebSocket, reconnectDelay);
                console.log(`Reconnecting (${reconnectAttempts}/${maxReconnectAttempts})...`);
            }
        });
        
        // Connection error
        socket.addEventListener('error', function(event) {
            console.error('WebSocket error:', event);
        });
        
        // Message received
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
        // Clear any existing interval
        if (elapsedTimeInterval) {
            clearInterval(elapsedTimeInterval);
        }
        
        // Set start time if not already set
        if (!startTime) {
            startTime = new Date();
        }
        
        // Update elapsed time display
        function updateElapsedTime() {
            const now = new Date();
            const elapsed = now - startTime;
            elapsedTime.textContent = formatElapsedTime(elapsed);
        }
        
        // Update immediately and then every second
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
        // Update status
        if (data.status) {
            statusValue.textContent = data.status.charAt(0).toUpperCase() + data.status.slice(1);
            statusValue.className = `status-${data.status}`;
            
            // Update activity indicator
            activityIndicator.textContent = data.status.charAt(0).toUpperCase() + data.status.slice(1);
            
            // Start or stop elapsed time counter based on status
            if (data.status === 'processing') {
                startElapsedTimeCounter();
                activityBar.style.display = 'block';
            } else if (data.status === 'complete') {
                stopElapsedTimeCounter();
                activityBar.style.display = 'none';
            } else if (data.status === 'idle') {
                stopElapsedTimeCounter();
                startTime = null;
                elapsedTime.textContent = '00:00:00';
                activityBar.style.display = 'none';
            }
        }
        
        // Update statistics
        urlsProcessed.textContent = data.urls_processed || 0;
        urlsDiscovered.textContent = data.urls_discovered || 0;
        chunksProcessed.textContent = data.chunks_processed || 0;
        chunksTotal.textContent = data.chunks_total || 0;
        
        // Update current URL
        if (data.current_url) {
            currentUrl.textContent = data.current_url;
        } else {
            currentUrl.textContent = '-';
        }
        
        // Update URL list
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
            socket.send(JSON.stringify({
                type: 'get_progress'
            }));
        } else {
            connectWebSocket();
        }
    }
    
    // Set up auto-refresh every 30 seconds
    setInterval(autoRefreshData, 30000);
    
    // Initialize
    updateCurrentTime();
    setInterval(updateCurrentTime, 1000);
    connectWebSocket();
});
