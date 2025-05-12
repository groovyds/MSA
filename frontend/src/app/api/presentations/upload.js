async function uploadLargeFile(file) {
    const chunkSize = 10 * 1024 * 1024; // 10MB chunks
    const totalChunks = Math.ceil(file.size / chunkSize);

    // Start the upload
    const startResponse = await fetch('/start-upload', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename: file.name })
    });
    const { upload_id } = await startResponse.json();

    // Upload each chunk
    for (let i = 0; i < totalChunks; i++) {
        const chunk = file.slice(i * chunkSize, (i + 1) * chunkSize);
        const formData = new FormData();
        formData.append('chunk', chunk);
        formData.append('upload_id', upload_id);
        formData.append('chunk_index', i);
        await fetch('/upload-chunk', {
            method: 'POST',
            body: formData
        });
    }

    // Finalize the upload
    await fetch('/finalize-upload', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ upload_id })
    });
    console.log('Upload complete!');
}

// Example usage
document.getElementById('fileInput').addEventListener('change', (event) => {
    const file = event.target.files[0];
    if (file) {
        uploadLargeFile(file);
    }
});