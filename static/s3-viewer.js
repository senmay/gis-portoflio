
class S3Viewer {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.init();
    }

    init() {
        this.fetchS3Data();
    }

    async fetchS3Data() {
        try {
            const response = await fetch('/api/s3/list');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            this.render(data);
        } catch (error) {
            console.error('Error fetching S3 data:', error);
            this.container.innerHTML = '<p>Error loading data from S3.</p>';
        }
    }

    render(data) {
        if (!data || data.length === 0) {
            this.container.innerHTML = '<p>No objects found in the bucket.</p>';
            return;
        }

        const table = `
            <table class="table">
                <thead>
                    <tr>
                        <th>Key</th>
                        <th>Size (KB)</th>
                        <th>Last Modified</th>
                    </tr>
                </thead>
                <tbody>
                    ${data.map(item => `
                        <tr>
                            <td>${item.key}</td>
                            <td>${(item.size / 1024).toFixed(2)}</td>
                            <td>${new Date(item.last_modified).toLocaleString()}</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
        this.container.innerHTML = table;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new S3Viewer('s3-viewer');
});
