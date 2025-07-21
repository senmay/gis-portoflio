/**
 * WMS Layer Viewer JavaScript
 * Handles WMS layer management, coordinate export, and measurement tools
 */

class WMSLayerViewer {
    constructor(mapId, config = {}) {
        this.mapId = mapId;
        this.config = {
            defaultCenter: [52.2297, 21.0122],
            defaultZoom: 13,
            geoserverWorkspace: config.geoserverWorkspace || 'default',
            ...config
        };
        
        // Map and layer management
        this.map = null;
        this.baseLayer = null;
        this.currentWMSLayer = null;
        this.coordinateMarkers = null;
        this.measurementLayer = null;
        
        // State management
        this.coordinates = [];
        this.measurementPoints = [];
        this.measurementLine = null;
        this.isCoordinateMode = false;
        this.isMeasureMode = false;
        
        // DOM elements
        this.elements = {};
        
        this.init();
    }
    
    /**
     * Initialize the WMS viewer
     */
    init() {
        this.initializeMap();
        this.initializeDOMElements();
        this.attachEventListeners();
        this.loadWMSLayers();
    }
    
    /**
     * Initialize the Leaflet map
     */
    initializeMap() {
        // Initialize map with fixed size
        this.map = L.map(this.mapId).setView(this.config.defaultCenter, this.config.defaultZoom);
        
        // Base layer (OSM)
        this.baseLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        }).addTo(this.map);
        
        // Initialize layer groups
        this.coordinateMarkers = L.featureGroup().addTo(this.map);
        this.measurementLayer = L.featureGroup().addTo(this.map);
        
        // Force map size recalculation after initialization
        setTimeout(() => {
            this.map.invalidateSize();
        }, 100);
        
        // Map click handler - use higher priority to avoid conflicts with other libraries
        this.map.on('click', (e) => this.onMapClick(e), this);
        
        // Ensure our click handler has priority
        this.map.getContainer().addEventListener('click', (e) => {
            console.log('Container clicked - ensuring our handler works');
        }, true);
    }
    
    /**
     * Initialize DOM element references
     */
    initializeDOMElements() {
        this.elements = {
            layerSelect: document.getElementById('layer-select'),
            opacitySlider: document.getElementById('opacity-slider'),
            opacityValue: document.getElementById('opacity-value'),
            layerInfo: document.getElementById('layer-info'),
            coordinateTool: document.getElementById('coordinate-tool'),
            measureTool: document.getElementById('measure-tool'),
            clearAll: document.getElementById('clear-all'),
            exportCoordinates: document.getElementById('export-coordinates'),
            clearCoordinates: document.getElementById('clear-coordinates'),
            coordinateCount: document.getElementById('coordinate-count'),
            coordinateList: document.getElementById('coordinate-list'),
            measurementDisplay: document.getElementById('measurement-display'),
            toast: document.getElementById('toast')
        };
    }
    
    /**
     * Attach event listeners to DOM elements
     */
    attachEventListeners() {
        const { elements } = this;
        
        elements.layerSelect.addEventListener('change', () => this.onLayerChange());
        elements.opacitySlider.addEventListener('input', () => this.onOpacityChange());
        elements.coordinateTool.addEventListener('click', () => this.toggleCoordinateMode());
        elements.measureTool.addEventListener('click', () => this.toggleMeasureMode());
        elements.clearAll.addEventListener('click', () => this.clearAllData());
        elements.exportCoordinates.addEventListener('click', () => this.exportCoordinatesToFile());
        elements.clearCoordinates.addEventListener('click', () => this.clearCoordinatePoints());
    }
    
    /**
     * Load available WMS layers from the server
     */
    async loadWMSLayers() {
        try {
            const response = await fetch('/api/layers');
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            this.populateLayerSelect(data.layers);
            
        } catch (error) {
            console.error('Error loading WMS layers:', error);
            this.handleLayerLoadError(error);
        }
    }
    
    /**
     * Populate the layer select dropdown
     */
    populateLayerSelect(layers) {
        const { layerSelect } = this.elements;
        
        layerSelect.innerHTML = '<option value="">-- Wybierz warstwę --</option>';
        
        if (layers && layers.length > 0) {
            layers.forEach(layer => {
                const option = document.createElement('option');
                option.value = layer.name;
                option.textContent = layer.title || layer.name;
                layerSelect.appendChild(option);
            });
        } else {
            layerSelect.innerHTML = '<option value="">Brak dostępnych warstw</option>';
        }
    }
    
    /**
     * Handle layer loading errors
     */
    handleLayerLoadError(error) {
        const { layerSelect } = this.elements;
        layerSelect.innerHTML = '<option value="">Błąd ładowania warstw</option>';
        this.showToast('Błąd ładowania warstw WMS. Sprawdź połączenie z GeoServer.', true);
    }
    
    /**
     * Handle layer selection change
     */
    async onLayerChange() {
        const selectedLayer = this.elements.layerSelect.value;
        
        // Remove current WMS layer
        this.removeCurrentWMSLayer();
        
        if (!selectedLayer) {
            this.disableLayerControls();
            return;
        }
        
        try {
            await this.loadWMSLayer(selectedLayer);
        } catch (error) {
            console.error('Error loading WMS layer:', error);
            this.showToast(`Błąd ładowania warstwy: ${selectedLayer}`, true);
        }
    }
    
    /**
     * Remove current WMS layer from map
     */
    removeCurrentWMSLayer() {
        if (this.currentWMSLayer) {
            this.map.removeLayer(this.currentWMSLayer);
            this.currentWMSLayer = null;
        }
    }
    
    /**
     * Disable layer-related controls
     */
    disableLayerControls() {
        this.elements.opacitySlider.disabled = true;
        this.elements.layerInfo.classList.add('hidden');
    }
    
    /**
     * Load a specific WMS layer
     */
    async loadWMSLayer(layerName) {
        try {
            // Get layer information
            const layerInfo = await this.getLayerInfo(layerName);
            
            // Create WMS layer
            this.currentWMSLayer = L.tileLayer.wms(layerInfo.wms_url, {
                layers: `${this.config.geoserverWorkspace}:${layerName}`,
                format: 'image/png',
                transparent: true,
                version: '1.3.0',
                crs: L.CRS.EPSG3857,
                // Error handling for tile loading
                errorTileUrl: 'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7'
            });
            
            // Handle layer loading events
            this.currentWMSLayer.on('loading', () => {
                this.showToast('Ładowanie warstwy...');
            });
            
            this.currentWMSLayer.on('load', () => {
                this.showToast(`Załadowano warstwę: ${layerName}`);
            });
            
            this.currentWMSLayer.on('tileerror', (e) => {
                console.error('Tile loading error:', e);
                this.showToast('Błąd ładowania niektórych fragmentów warstwy', true);
            });
            
            // Add layer to map
            this.currentWMSLayer.addTo(this.map);
            
            // Zoom to layer extent if bounding box is available
            if (layerInfo.bbox_epsg3857) {
                this.zoomToLayerExtent(layerInfo.bbox_epsg3857);
            }
            
            // Enable controls
            this.enableLayerControls();
            
            // Display layer information
            this.displayLayerInfo(layerInfo);
            
        } catch (error) {
            throw new Error(`Failed to load WMS layer: ${error.message}`);
        }
    }
    
    /**
     * Get layer information from server
     */
    async getLayerInfo(layerName) {
        const response = await fetch(`/api/layer-info/${layerName}`);
        
        if (!response.ok) {
            throw new Error(`Failed to get layer info: ${response.status}`);
        }
        
        return await response.json();
    }
    
    /**
     * Zoom map to layer extent using EPSG:3857 bounding box
     */
    zoomToLayerExtent(bbox_epsg3857) {
        try {
            // Parse bounding box string: "minx,miny,maxx,maxy"
            const [minx, miny, maxx, maxy] = bbox_epsg3857.split(',').map(parseFloat);
            
            // Convert EPSG:3857 bounds to LatLng for Leaflet
            const southWest = L.CRS.EPSG3857.unproject(L.point(minx, miny));
            const northEast = L.CRS.EPSG3857.unproject(L.point(maxx, maxy));
            
            // Create bounds and fit map to them
            const bounds = L.latLngBounds(southWest, northEast);
            this.map.fitBounds(bounds, {
                padding: [20, 20], // Add some padding around the bounds
                maxZoom: 18 // Don't zoom in too much
            });
            
            console.log(`Zoomed to layer extent: ${bbox_epsg3857}`);
            
        } catch (error) {
            console.error('Error zooming to layer extent:', error);
            // Don't show error to user, just log it
        }
    }
    
    /**
     * Enable layer-related controls
     */
    enableLayerControls() {
        this.elements.opacitySlider.disabled = false;
        this.elements.opacitySlider.value = 100;
        this.elements.opacityValue.textContent = '100';
    }
    
    /**
     * Display layer information
     */
    displayLayerInfo(layerData) {
        const { layerInfo } = this.elements;
        
        layerInfo.innerHTML = `
            <strong>${layerData.title || layerData.name}</strong><br>
            ${layerData.abstract || 'Brak opisu'}<br>
            <small>Typ: ${layerData.type || 'WMS'} | Status: ${layerData.enabled ? 'Aktywna' : 'Nieaktywna'}</small>
        `;
        layerInfo.classList.remove('hidden');
    }
    
    /**
     * Handle opacity slider change
     */
    onOpacityChange() {
        const opacity = this.elements.opacitySlider.value / 100;
        this.elements.opacityValue.textContent = this.elements.opacitySlider.value;
        
        if (this.currentWMSLayer) {
            this.currentWMSLayer.setOpacity(opacity);
        }
    }
    
    /**
     * Toggle coordinate collection mode
     */
    toggleCoordinateMode() {
        this.isCoordinateMode = !this.isCoordinateMode;
        this.isMeasureMode = false;
        
        this.elements.coordinateTool.classList.toggle('active', this.isCoordinateMode);
        this.elements.measureTool.classList.remove('active');
        
        this.map.getContainer().style.cursor = this.isCoordinateMode ? 'crosshair' : '';
        
        console.log('Coordinate mode toggled:', this.isCoordinateMode);
        
        if (this.isCoordinateMode) {
            this.showToast('Tryb współrzędnych aktywny - kliknij na mapę');
        } else {
            this.showToast('Tryb współrzędnych wyłączony');
        }
    }
    
    /**
     * Toggle measurement mode
     */
    toggleMeasureMode() {
        this.isMeasureMode = !this.isMeasureMode;
        this.isCoordinateMode = false;
        
        this.elements.measureTool.classList.toggle('active', this.isMeasureMode);
        this.elements.coordinateTool.classList.remove('active');
        
        this.map.getContainer().style.cursor = this.isMeasureMode ? 'crosshair' : '';
        
        if (this.isMeasureMode) {
            this.measurementPoints = [];
            this.elements.measurementDisplay.style.display = 'block';
            this.elements.measurementDisplay.textContent = 'Kliknij pierwszy punkt';
            this.showToast('Tryb pomiaru aktywny - kliknij punkty na mapie');
        } else {
            this.elements.measurementDisplay.style.display = 'none';
        }
    }
    
    /**
     * Handle map click events
     */
    onMapClick(e) {
        console.log('Map clicked:', e.latlng, 'Coordinate mode:', this.isCoordinateMode, 'Measure mode:', this.isMeasureMode);
        
        if (this.isCoordinateMode) {
            console.log('Adding coordinate point...');
            this.addCoordinatePoint(e.latlng);
        } else if (this.isMeasureMode) {
            console.log('Adding measurement point...');
            this.addMeasurementPoint(e.latlng);
        }
    }
    
    /**
     * Add a coordinate point to the collection
     */
    addCoordinatePoint(latlng) {
        console.log('addCoordinatePoint called with:', latlng);
        console.log('coordinateMarkers layer group:', this.coordinateMarkers);
        
        const marker = L.marker(latlng, {
            icon: L.divIcon({
                className: 'coordinate-marker',
                html: '<div style="background: #FFD700; width: 12px; height: 12px; border-radius: 50%; border: 2px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3); z-index: 1000;"></div>',
                iconSize: [16, 16],
                iconAnchor: [8, 8]
            })
        }).addTo(this.coordinateMarkers).bindTooltip(`${latlng.lat.toFixed(6)}, ${latlng.lng.toFixed(6)}`, {permanent: false, direction: 'top'});
        
        console.log('Marker created and added:', marker);
        
        this.coordinates.push({
            lng: latlng.lng.toFixed(6),
            lat: latlng.lat.toFixed(6),
            marker: marker
        });
        
        console.log('Coordinates array now has', this.coordinates.length, 'points');
        
        this.updateCoordinateDisplay();
        this.showToast(`Dodano punkt: ${latlng.lat.toFixed(6)}, ${latlng.lng.toFixed(6)}`);
    }
    
    /**
     * Add a measurement point
     */
    addMeasurementPoint(latlng) {
        this.measurementPoints.push(latlng);
        
        // Add point marker
        L.marker(latlng, {
            icon: L.divIcon({
                className: 'measurement-marker',
                html: '<div style="background: #ff6b6b; width: 6px; height: 6px; border-radius: 50%; border: 1px solid white;"></div>',
                iconSize: [8, 8],
                iconAnchor: [4, 4]
            })
        }).addTo(this.measurementLayer);
        
        this.updateMeasurementDisplay();
    }
    
    /**
     * Update measurement display
     */
    updateMeasurementDisplay() {
        const pointCount = this.measurementPoints.length;
        
        if (pointCount === 1) {
            this.elements.measurementDisplay.textContent = 'Kliknij drugi punkt';
        } else if (pointCount >= 2) {
            // Draw line and calculate distance
            if (this.measurementLine) {
                this.measurementLayer.removeLayer(this.measurementLine);
            }
            
            this.measurementLine = L.polyline(this.measurementPoints, {
                color: '#ff6b6b',
                weight: 2,
                dashArray: '5, 5'
            }).addTo(this.measurementLayer);
            
            const distance = this.calculateDistance();
            this.elements.measurementDisplay.textContent = `Odległość: ${distance}`;
            
            if (pointCount > 2) {
                this.elements.measurementDisplay.textContent += ' (kliknij kolejny punkt lub wyczyść)';
            }
        }
    }
    
    /**
     * Calculate total distance of measurement points
     */
    calculateDistance() {
        if (this.measurementPoints.length < 2) return '0 m';
        
        let totalDistance = 0;
        for (let i = 1; i < this.measurementPoints.length; i++) {
            totalDistance += this.measurementPoints[i-1].distanceTo(this.measurementPoints[i]);
        }
        
        if (totalDistance < 1000) {
            return `${totalDistance.toFixed(1)} m`;
        } else {
            return `${(totalDistance / 1000).toFixed(2)} km`;
        }
    }
    
    /**
     * Update coordinate display
     */
    updateCoordinateDisplay() {
        const count = this.coordinates.length;
        
        this.elements.coordinateCount.textContent = `Punktów: ${count}`;
        this.elements.exportCoordinates.disabled = count === 0;
        this.elements.clearCoordinates.disabled = count === 0;
    }
    
    /**
     * Remove a specific coordinate point
     */
    removeCoordinate(index) {
        if (this.coordinates[index] && this.coordinates[index].marker) {
            this.coordinateMarkers.removeLayer(this.coordinates[index].marker);
        }
        this.coordinates.splice(index, 1);
        this.updateCoordinateDisplay();
    }
    
    /**
     * Clear all data (coordinates and measurements)
     */
    clearAllData() {
        this.clearCoordinatePoints();
        this.clearMeasurements();
        this.isCoordinateMode = false;
        this.isMeasureMode = false;
        this.elements.coordinateTool.classList.remove('active');
        this.elements.measureTool.classList.remove('active');
        this.map.getContainer().style.cursor = '';
        this.showToast('Wyczyszczono wszystkie dane');
    }
    
    /**
     * Clear coordinate points
     */
    clearCoordinatePoints() {
        this.coordinateMarkers.clearLayers();
        this.coordinates = [];
        this.updateCoordinateDisplay();
    }
    
    /**
     * Clear measurements
     */
    clearMeasurements() {
        this.measurementLayer.clearLayers();
        this.measurementPoints = [];
        this.measurementLine = null;
        this.elements.measurementDisplay.style.display = 'none';
    }
    
    /**
     * Export coordinates to file
     */
    async exportCoordinatesToFile() {
        if (this.coordinates.length === 0) {
            this.showToast('Brak współrzędnych do eksportu', true);
            return;
        }
        
        const coordinatesToExport = this.coordinates.map(coord => ({ lat: coord.lat, lng: coord.lng }));
        try {
            console.log('Exporting coordinates:', JSON.stringify({ coordinates: coordinatesToExport }));
            const response = await fetch('/api/export-coordinates', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ coordinates: coordinatesToExport })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            // Download file
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            
            // Extract filename from Content-Disposition header
            const contentDisposition = response.headers.get('Content-Disposition');
            const filename = contentDisposition 
                ? contentDisposition.split('filename=')[1].replace(/"/g, '')
                : `coordinates_${new Date().toISOString().slice(0, 10)}.txt`;
            
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            
            this.showToast(`Eksportowano ${this.coordinates.length} współrzędnych`);
            
        } catch (error) {
            console.error('Export error:', error);
            this.showToast('Błąd eksportu współrzędnych', true);
        }
    }
    
    /**
     * Show toast notification
     */
    showToast(message, isError = false) {
        const toast = this.elements.toast;
        toast.textContent = message;
        toast.className = 'toast show';
        
        if (isError) {
            toast.classList.add('error');
        }
        
        setTimeout(() => {
            toast.className = toast.className.replace('show', '');
            toast.classList.remove('error');
        }, 3000);
    }
    
    /**
     * Get current layer information
     */
    getCurrentLayerInfo() {
        return {
            hasWMSLayer: !!this.currentWMSLayer,
            layerName: this.elements.layerSelect.value,
            opacity: this.elements.opacitySlider.value,
            coordinateCount: this.coordinates.length,
            measurementPointCount: this.measurementPoints.length
        };
    }
    
    /**
     * Refresh WMS layers list
     */
    async refreshLayers() {
        this.elements.layerSelect.innerHTML = '<option value="">Ładowanie warstw...</option>';
        await this.loadWMSLayers();
    }
}

// Initialize WMS viewer when DOM is loaded
let wmsViewer;

document.addEventListener('DOMContentLoaded', function() {
    // Get configuration from template or use defaults
    const config = window.wmsConfig || {};
    
    // Initialize WMS viewer
    wmsViewer = new WMSLayerViewer('map', config);
    
    // Make it globally accessible for inline event handlers
    window.wmsViewer = wmsViewer;
});