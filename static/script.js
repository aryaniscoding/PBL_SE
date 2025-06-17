document.addEventListener('DOMContentLoaded', function() {
    fetchUserData();
});

function fetchUserData() {
    fetch('/user/data')
    .then(response => response.json())
    .then(data => {
        // Update car details
        document.getElementById('plateNumber').textContent = data.plateNumber || 'N/A';
        document.getElementById('region').textContent = data.region || 'N/A';
        document.getElementById('carModel').textContent = data.carModel || 'N/A';
        document.getElementById('carColor').textContent = data.carColor || 'N/A';

        // Update car images
        const carImages = document.getElementById('carImages');
        carImages.innerHTML = data.images.map(image => `
            <img src="${image}" alt="Car Image">
        `).join('');

        // Update recent entries
        const recentEntries = document.getElementById('recentEntries');
        recentEntries.innerHTML = data.recentEntries.map(entry => `
            <div class="entry">
                <p><strong>Timestamp:</strong> ${entry.timestamp}</p>
                <p><strong>Fare:</strong> ${entry.fare.toFixed(2)} units</p>
                <img src="${entry.image}" alt="Entry Image" width="100">
            </div>
        `).join('');
    })
    .catch(error => {
        console.error('Error fetching user data:', error);
        alert('Failed to fetch user data');
    });
}