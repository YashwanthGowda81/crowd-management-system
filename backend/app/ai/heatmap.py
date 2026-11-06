import cv2
import numpy as np
import base64
from typing import Dict, List, Optional, Any

class HeatmapGenerator:
    def __init__(self, width: int = 640, height: int = 480):
        self.width = width
        self.height = height
        self.grid = np.zeros((height, width), dtype=np.float32)

    def accumulate_points(self, boxes: list):
        """
        Accumulates centroid coordinates from bounding boxes onto spatial grid.
        boxes: List of [x1, y1, x2, y2, conf]
        """
        # Decays old heat points slightly so dynamic movement reflects accurately
        self.grid *= 0.92

        for box in boxes:
            x1, y1, x2, y2 = box[:4]
            cx = int((x1 + x2) / 2)
            cy = int((y1 + y2) / 2)
            
            if 0 <= cx < self.width and 0 <= cy < self.height:
                # Add Gaussian heat spot around centroid
                cv2.circle(self.grid, (cx, cy), 28, (1.0,), -1)

    def accumulate_normalized_point(self, norm_x: float, norm_y: float, weight: float = 1.0):
        """
        Accumulates relative percentage point (0.0 to 100.0) onto grid.
        Useful for area/venue-wide map accumulation.
        """
        self.grid *= 0.94
        cx = int((norm_x / 100.0) * self.width)
        cy = int((norm_y / 100.0) * self.height)
        if 0 <= cx < self.width and 0 <= cy < self.height:
            cv2.circle(self.grid, (cx, cy), 35, (float(weight),), -1)

    def generate_heatmap_overlay(self, base_image: np.ndarray = None) -> np.ndarray:
        """Generates colorized OpenCV JET colormap matrix."""
        # Normalize grid between 0 and 255
        norm_grid = cv2.normalize(self.grid, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
        
        # Apply Gaussian Blur for smooth spatial gradients
        blurred = cv2.GaussianBlur(norm_grid, (31, 31), 0)
        
        # Apply JET Colormap (Blue = Low, Yellow = Medium, Red = High Density)
        heatmap_color = cv2.applyColorMap(blurred, cv2.COLORMAP_JET)

        if base_image is not None:
            base_resized = cv2.resize(base_image, (self.width, self.height))
            blended = cv2.addWeighted(base_resized, 0.5, heatmap_color, 0.5, 0)
            return blended

        return heatmap_color

    def generate_base64_heatmap(self, transparent_zero: bool = False) -> str:
        """Generates Base64 encoded JPEG/PNG string for frontend web display."""
        norm_grid = cv2.normalize(self.grid, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
        blurred = cv2.GaussianBlur(norm_grid, (31, 31), 0)

        if transparent_zero:
            # Generate RGBA image where low-density background is transparent
            heatmap_color = cv2.applyColorMap(blurred, cv2.COLORMAP_JET)
            b, g, r = cv2.split(heatmap_color)
            # Alpha mask proportional to heat intensity
            alpha = np.clip(blurred * 1.4, 0, 255).astype(np.uint8)
            rgba = cv2.merge([b, g, r, alpha])
            _, buffer = cv2.imencode('.png', rgba)
            base64_str = base64.b64encode(buffer).decode('utf-8')
            return f"data:image/png;base64,{base64_str}"
        else:
            heatmap_color = cv2.applyColorMap(blurred, cv2.COLORMAP_JET)
            _, buffer = cv2.imencode('.jpg', heatmap_color, [cv2.IMWRITE_JPEG_QUALITY, 85])
            base64_str = base64.b64encode(buffer).decode('utf-8')
            return f"data:image/jpeg;base64,{base64_str}"


class MultiLevelHeatmapManager:
    """Manages Camera-level, Zone-level, and Area-level heatmaps."""
    def __init__(self):
        self.camera_generators: Dict[str, HeatmapGenerator] = {}
        self.zone_generators: Dict[str, HeatmapGenerator] = {}
        self.area_generator = HeatmapGenerator(width=800, height=600)

    def get_camera_generator(self, camera_id: str) -> HeatmapGenerator:
        if camera_id not in self.camera_generators:
            self.camera_generators[camera_id] = HeatmapGenerator()
        return self.camera_generators[camera_id]

    def get_zone_generator(self, zone_id: str) -> HeatmapGenerator:
        if zone_id not in self.zone_generators:
            self.zone_generators[zone_id] = HeatmapGenerator()
        return self.zone_generators[zone_id]

    def accumulate_camera_boxes(self, camera_id: str, boxes: list, zone_id: Optional[str] = None):
        gen = self.get_camera_generator(camera_id)
        gen.accumulate_points(boxes)

        if zone_id:
            zone_gen = self.get_zone_generator(zone_id)
            zone_gen.accumulate_points(boxes)

    def accumulate_area_pin(self, x_pct: float, y_pct: float, count: int):
        weight = min(3.0, max(0.5, count / 50.0))
        self.area_generator.accumulate_normalized_point(x_pct, y_pct, weight=weight)


heatmap_manager = MultiLevelHeatmapManager()
# Backward compatible global instance
global_heatmap_gen = heatmap_manager.area_generator


from dataclasses import dataclass

@dataclass
class HeatmapProfile:
    name: str  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    min_density: float
    max_density: float
    jet_range: tuple  # (min_val, max_val) in 0-255 JET index range
    alpha_range: tuple  # (min_alpha, peak_alpha)
    radius_scale: float
    sigma_scale: float


HEATMAP_PROFILES: Dict[str, HeatmapProfile] = {
    "LOW": HeatmapProfile(
        name="LOW",
        min_density=0.0,
        max_density=44.99,
        jet_range=(35.0, 85.0),  # Cool Blue to Cyan
        alpha_range=(75.0, 160.0),  # High floorplan transparency preserved
        radius_scale=0.85,  # Small localized hotspots
        sigma_scale=2.4
    ),
    "MEDIUM": HeatmapProfile(
        name="MEDIUM",
        min_density=45.0,
        max_density=74.99,
        jet_range=(95.0, 180.0),  # Cyan / Greenish-Yellow / Yellow
        alpha_range=(95.0, 190.0),
        radius_scale=1.0,
        sigma_scale=2.2
    ),
    "HIGH": HeatmapProfile(
        name="HIGH",
        min_density=75.0,
        max_density=89.99,
        jet_range=(185.0, 225.0),  # Yellow / Orange / Red
        alpha_range=(115.0, 215.0),
        radius_scale=1.15,
        sigma_scale=2.0
    ),
    "CRITICAL": HeatmapProfile(
        name="CRITICAL",
        min_density=90.0,
        max_density=100.0,
        jet_range=(230.0, 255.0),  # Orange / Red / Crimson
        alpha_range=(135.0, 240.0),  # Strong intense hotspots
        radius_scale=1.3,
        sigma_scale=1.8
    )
}


def get_profile_for_density(density: float) -> HeatmapProfile:
    """Selects the calibrated rendering profile based on crowd density percentage."""
    if density >= 90.0:
        return HEATMAP_PROFILES["CRITICAL"]
    elif density >= 75.0:
        return HEATMAP_PROFILES["HIGH"]
    elif density >= 45.0:
        return HEATMAP_PROFILES["MEDIUM"]
    else:
        return HEATMAP_PROFILES["LOW"]


def generate_venue_density_overlay(
    points: List[Dict[str, Any]],
    width: int = 1000,
    height: int = 750
) -> str:
    """
    Generates an event-scoped, transparent PNG crowd density heatmap overlay
    scaled precisely to the uploaded venue map coordinate space (0.0 to 100.0%).
    
    Density profiles (JET colormap & dynamic alpha):
    - Profile A: LOW (< 45%): Cool Blue / Cyan, localized faint hotspots, high floorplan clarity
    - Profile B: MEDIUM (45 - 74%): Cyan, Greenish-Yellow, Yellow hotspots
    - Profile C: HIGH (75 - 89%): Yellow, Orange, Red stronger hotspots
    - Profile D: CRITICAL (>= 90%): Intense Orange, Red, Crimson hotspots
    
    Zero density areas are 100% transparent so the underlying architectural floorplan
    remains completely visible.
    """
    if not points:
        return ""

    active_points = [p for p in points if (p.get("count", 0) > 0 or p.get("density", 0) > 0)]
    if not active_points:
        return ""

    grid = np.zeros((height, width), dtype=np.float32)
    alpha_grid = np.zeros((height, width), dtype=np.float32)

    for pt in active_points:
        norm_x = float(pt.get("x", 50.0))
        norm_y = float(pt.get("y", 50.0))
        density = float(pt.get("density", 0.0))

        # Clamp normalized coordinates to 0..100
        norm_x = max(0.0, min(100.0, norm_x))
        norm_y = max(0.0, min(100.0, norm_y))

        cx = int((norm_x / 100.0) * width)
        cy = int((norm_y / 100.0) * height)
        default_radius = max(50, int(min(width, height) * 0.085))
        base_radius = int(pt.get("radius", default_radius))

        profile = get_profile_for_density(density)
        range_span = max(0.01, profile.max_density - profile.min_density)
        ratio = min(1.0, max(0.0, (density - profile.min_density) / range_span))
        target_val = profile.jet_range[0] + ratio * (profile.jet_range[1] - profile.jet_range[0])

        effective_radius = max(20, int(base_radius * profile.radius_scale))
        sigma = max(1.0, effective_radius / profile.sigma_scale)

        pt_min_a, pt_max_a = profile.alpha_range
        target_alpha = pt_min_a + ratio * (pt_max_a - pt_min_a)

        # Draw smooth Gaussian hotspot onto grid
        y_min = max(0, cy - effective_radius)
        y_max = min(height, cy + effective_radius + 1)
        x_min = max(0, cx - effective_radius)
        x_max = min(width, cx + effective_radius + 1)

        if y_max > y_min and x_max > x_min:
            y_coords, x_coords = np.ogrid[y_min - cy:y_max - cy, x_min - cx:x_max - cx]
            dist_sq = x_coords**2 + y_coords**2
            kernel = np.exp(-0.5 * dist_sq / (sigma**2))
            kernel[dist_sq > effective_radius**2] = 0.0

            hotspot_val = target_val * kernel
            hotspot_alpha = target_alpha * kernel

            grid[y_min:y_max, x_min:x_max] = np.maximum(grid[y_min:y_max, x_min:x_max], hotspot_val)
            alpha_grid[y_min:y_max, x_min:x_max] = np.maximum(alpha_grid[y_min:y_max, x_min:x_max], hotspot_alpha)

    if grid.max() <= 0:
        return ""

    grid_u8 = np.clip(grid, 0, 255).astype(np.uint8)
    blurred_color = cv2.GaussianBlur(grid_u8, (15, 15), 0)

    # Colormap JET aligns with: Blue/Cyan -> Yellow -> Orange -> Red
    heatmap_color = cv2.applyColorMap(blurred_color, cv2.COLORMAP_JET)

    # Feather alpha at boundary smoothly, 0 in unobserved regions
    alpha_u8 = np.clip(alpha_grid, 0, 255).astype(np.uint8)
    alpha_blurred = cv2.GaussianBlur(alpha_u8, (15, 15), 0)
    # Ensure zero areas remain zero
    alpha_blurred[blurred_color == 0] = 0

    b, g, r = cv2.split(heatmap_color)
    rgba = cv2.merge([b, g, r, alpha_blurred])

    _, buffer = cv2.imencode('.png', rgba)
    base64_str = base64.b64encode(buffer).decode('utf-8')
    return f"data:image/png;base64,{base64_str}"
