let currentUpload = null;

async function uploadLargeFile(file, options = {}) {
    // Configuration with defaults that can be overridden
    const config = {
        chunkSize: 5 * 1024 * 1024, // 5MB chunks (more manageable size)
        maxConcurrentChunks: 3,     // Number of chunks to upload in parallel
        retryAttempts: 3,           // Number of retry attempts per chunk
        retryDelay: 2000,           // Delay between retries in ms
        onProgress: (percent) => {}, // Progress callback
        onError: (error) => {},
        allowedTypes: null,     // Error callback
        ...options
    };

    // Create an AbortController for cancellation
    const abortController = new AbortController();
    currentUpload = {
        file: file.name,
        abort: () => abortController.abort()
    };
    
    // Validate file type if allowedTypes is specified
    if (config.allowedTypes && !config.allowedTypes.includes(file.type)) {
        const error = new Error(`File type ${file.type} not allowed. Allowed types: ${config.allowedTypes.join(', ')}`);
        config.onError(error);
        throw error;
    }

    // Calculate total chunks
    const totalChunks = Math.ceil(file.size / config.chunkSize);
    
    try {
        // Check if this is a resume from a previous attempt
        let uploadInfo = localStorage.getItem(`upload_${file.name}`);
        let upload_id;
        let uploadedChunks = [];
        
        if (uploadInfo) {
            const savedInfo = JSON.parse(uploadInfo);
            // Only use saved info if it's recent (less than 24 hours old)
            const isRecent = (Date.now() - savedInfo.timestamp) < 24 * 60 * 60 * 1000;
            
            if (isRecent && savedInfo.fileSize === file.size) {
                upload_id = savedInfo.upload_id;
                uploadedChunks = savedInfo.uploadedChunks || [];
                console.log(`Resuming upload with ID: ${upload_id}, ${uploadedChunks.length} chunks already uploaded`);
                
                // Verify the upload session still exists on the server
                try {
                    const checkResponse = await fetch(`/api/presentations/check-upload?upload_id=${upload_id}`, {
                        signal: abortController.signal
                    });
                    if (!checkResponse.ok) {
                        // If session doesn't exist, start a new one
                        throw new Error('Upload session expired');
                    }
                } catch (error) {
                    // Start new upload if check fails
                    localStorage.removeItem(`upload_${file.name}`);
                    upload_id = null;
                    uploadedChunks = [];
                }
            } else {
                // Start fresh if saved info is stale
                localStorage.removeItem(`upload_${file.name}`);
            }
        }
        
        // Start a new upload if not resuming
        if (!upload_id) {
            // Start the upload session
            const startResponse = await fetch('/api/presentations/start-upload', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    filename: file.name,
                    fileSize: file.size,
                    totalChunks: totalChunks
                }),
                signal: abortController.signal
            });
            
            if (!startResponse.ok) {
                throw new Error(`Failed to start upload: ${startResponse.statusText}`);
            }
            
            const result = await startResponse.json();
            upload_id = result.upload_id;
            
            // Save upload information for potential resume
            localStorage.setItem(`upload_${file.name}`, JSON.stringify({
                upload_id,
                fileSize: file.size,
                totalChunks: totalChunks,
                uploadedChunks: [],
                timestamp: Date.now()
            }));
        }
        
        // Create an array of chunk indices that need to be uploaded
        const remainingChunks = Array.from(
            { length: totalChunks }, 
            (_, i) => i
        ).filter(i => !uploadedChunks.includes(i));
        
        // Total chunks to track progress properly
        const totalRemainingChunks = remainingChunks.length;
        let completedChunks = uploadedChunks.length;
        
        // Update progress based on already uploaded chunks
        if (completedChunks > 0) {
            const currentProgress = Math.round((completedChunks / totalChunks) * 100);
            config.onProgress(currentProgress);
        }
        
        // Function to upload a single chunk with retries
        const uploadChunk = async (chunkIndex) => {
            const start = chunkIndex * config.chunkSize;
            const end = Math.min(start + config.chunkSize, file.size);
            const chunk = file.slice(start, end);
            const chunkFile = new File([chunk], 'chunk', { type: file.type });
            
            let attempts = 0;
            while (attempts < config.retryAttempts) {
                try {
                    const formData = new FormData();
                    formData.append('chunk', chunkFile);
                    formData.append('upload_id', upload_id);
                    formData.append('chunk_index', chunkIndex.toString());
                    formData.append('total_chunks', totalChunks.toString());
                    
                    const response = await fetch('/api/presentations/upload-chunk', {
                        method: 'POST',
                        body: formData,
                        signal: abortController.signal
                    });
                    
                    if (!response.ok) {
                        throw new Error(`Chunk ${chunkIndex} upload failed: ${response.statusText}`);
                    }
                    
                    // Update local storage with newly uploaded chunk
                    const uploadInfo = JSON.parse(localStorage.getItem(`upload_${file.name}`));
                    uploadInfo.uploadedChunks.push(chunkIndex);
                    localStorage.setItem(`upload_${file.name}`, JSON.stringify(uploadInfo));
                    
                    // Update progress
                    completedChunks++;
                    const progress = Math.round((completedChunks / totalChunks) * 100);
                    config.onProgress(progress);
                    
                    return true;
                } catch (error) {
                    // Check if this is an abort error
                    if (error.name === 'AbortError') {
                        throw error; // Rethrow abort errors
                    }

                    attempts++;
                    if (attempts >= config.retryAttempts) {
                        throw error;
                    }
                    // Wait before retry
                    await new Promise(resolve => setTimeout(resolve, config.retryDelay));
                }
            }
        };
        
        // Upload chunks with controlled concurrency
        const uploadAllChunks = async () => {
            const results = [];
            for (let i = 0; i < remainingChunks.length; i += config.maxConcurrentChunks) {
                const chunkBatch = remainingChunks.slice(i, i + config.maxConcurrentChunks);
                const batchPromises = chunkBatch.map(chunkIndex => uploadChunk(chunkIndex));
                
                // Wait for the current batch to complete before starting the next batch
                const batchResults = await Promise.allSettled(batchPromises);
                
                // Check for failures
                const failures = batchResults.filter(r => r.status === 'rejected');
                if (failures.length > 0) {
                    throw new Error(`Failed to upload some chunks: ${failures[0].reason}`);
                }
                
                results.push(...batchResults);
            }
            return results;
        };
        
        // Start uploading chunks
        await uploadAllChunks();
        
        // Finalize the upload
        const finalizeResponse = await fetch('/api/presentations/finalize-upload', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ upload_id }),
            signal: abortController.signal
        });
        
        if (!finalizeResponse.ok) {
            throw new Error(`Failed to finalize upload: ${finalizeResponse.statusText}`);
        }
        
        // Clean up local storage after successful upload
        localStorage.removeItem(`upload_${file.name}`);
        
        const result = await finalizeResponse.json();
        console.log('Upload complete!', result);
        return result;
        
    } catch (error) {
        // Handle abort errors specifically
        if (error.name === 'AbortError') {
            const cancelError = new Error ('Upload was concelled');
            config.onError(cancelError);
            throw cancelError;
        } else {
            console.error("Upload failed:", error);
            config.onError(error);
            throw error;
        }
    } finally {
        // Clear currentUpload when done
        if (currentUpload && currentUpload.file === file.name) {
            currentUpload = null;
        }
    }
}

// Add cancel button functionality
function cancelCurrentUpload() {
    if (currentUpload) {
        currentUpload.abort();
        return true;
    }
    return false;
}

// Example usage with progress tracking
document.getElementById('fileInput').addEventListener('change', async (event) => {
    const file = event.target.files[0];
    if (!file) return;
    
    // Create progress elements
    const progressContainer = document.createElement('div');
    progressContainer.className = 'progress-container';
    
    const progressBar = document.createElement('div');
    progressBar.className = 'progress-bar';
    progressBar.style.width = '0%';
    
    const progressText = document.createElement('span');
    progressText.className = 'progress-text';
    progressText.textContent = '0%';
    
    // Add cancel button
    const cancelButton = document.createElement('button');
    cancelButton.className = 'cancel-button';
    cancelButton.textContent = 'Cancel';
    cancelButton.addEventListener('click', () => {
        if (cancelCurrentUpload()) {
            progressText.textContent = 'Upload cancelled';
            progressContainer.style.backgroundColor = '#ffdddd';
            setTimeout(() => {
                progressContainer.remove();
            }, 3000);
        }
    });

    progressContainer.appendChild(progressBar);
    progressContainer.appendChild(progressText);
    progressContainer.appendChild(cancelButton);
    document.body.appendChild(progressContainer);
    
    try {
        const result = await uploadLargeFile(file, {
            onProgress: (percent) => {
                progressBar.style.width = `${percent}%`;
                progressText.textContent = `${percent}%`;
            },
            onError: (error) => {
                progressText.textContent = `Error: ${error.message}`;
                progressContainer.style.backgroundColor = '#ffdddd';
                // Make cancel button text change to "Close"
                cancelButton.textContent = 'Close';
            }
        });
        
        // Show success and presentation details
        progressContainer.style.backgroundColor = '#ddffdd';
        progressText.textContent = 'Upload complete!';
        cancelButton.textContent = 'Close';
        
        // Create details element to show presentation info
        const detailsElement = document.createElement('div');
        detailsElement.className = 'upload-details';
        detailsElement.innerHTML = `
            <p>Presentation ID: ${result.id}</p>
            <p>Filename: ${result.filename}</p>
        `;
        progressContainer.appendChild(detailsElement);
        
        // Close button behavior changes to just remove the container
        cancelButton.removeEventListener('click', cancelCurrentUpload);
        cancelButton.addEventListener('click', () => {
            progressContainer.remove();
        });

        // You can update the UI with presentation details here
        setTimeout(() => {
            progressContainer.remove();
        }, 3000);
        
    } catch (error) {
        if (error.message === 'Upload was cancelled') {
            return;
        }
        console.error('Upload failed:', error);
    }
});