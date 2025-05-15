async function uploadLargeFile(file) {
    const chunkSize = 10 * 1024 * 1024; // 10MB chunks
    const totalChunks = Math.ceil(file.size / chunkSize);

    // Start the upload
    const startResponse = await fetch('/api/presentations/start-upload', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename: file.name })
    });
    const { upload_id } = await startResponse.json();

    // Upload each chunk
    for (let i = 0; i < totalChunks; i++) {
        const chunk = file.slice(i * chunkSize, (i + 1) * chunkSize);
        const chunkFile = new File([chunk], 'chunk', { type: file.type });

        const formData = new FormData();
        formData.append('chunk', chunkFile);
        formData.append('upload_id', upload_id);
        formData.append('chunk_index', i.toString());

        await fetch('/api/presentations/upload-chunk', {
            method: 'POST',
            body: formData
        });

        // Progress tracking here
        const progress = Math.round(((i +1) / totalChunks) * 100);
        console.log(`Upload progress: ${progress}%`);
    }

    // Finalize the upload
    const finalizeResponse = await fetch('/api/presentations/finalize-upload', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ upload_id })
    });

    const result = await finalizeResponse.json();
    console.log('Upload complete!');
    return result;
}

// Example usage
document.getElementById('fileInput').addEventListener('change', async (event) => {
    const file = event.target.files[0];
    if (file) {
        try {
        const result = await uploadLargeFile(file);
    } catch (error) {
        console.error('Upload failed:', error);
        }
    }
});