import math

def generate_velocity_chart(data: list) -> str:
    """
    Generates an SVG line/area chart showing Code Change Velocity (additions vs deletions).
    Expected data schema: list of {'commit_date': 'YYYY-MM-DD', 'total_additions': A, 'total_deletions': D, ...}
    """
    width = 800
    height = 300
    
    # Handle empty state
    if not data:
        return f"""
        <svg viewBox="0 0 {width} {height}" class="w-full h-full" xmlns="http://www.w3.org/2000/svg">
            <rect width="100%" height="100%" fill="none"/>
            <text x="{width/2}" y="{height/2}" fill="#94A3B8" font-family="sans-serif" font-size="16" text-anchor="middle" font-weight="500">
                No activity history available. Start committing to see velocity analytics!
            </text>
        </svg>
        """
        
    margin = {"left": 70, "right": 30, "top": 30, "bottom": 50}
    plot_w = width - margin["left"] - margin["right"]
    plot_h = height - margin["top"] - margin["bottom"]
    
    # Calculate bounds
    max_val = 10  # Minimum threshold to avoid division by zero or super compressed charts
    for row in data:
        max_val = max(max_val, row.get("total_additions") or 0, row.get("total_deletions") or 0)
        
    # Standardize Y-max to a neat number
    order = 10 ** int(math.log10(max_val)) if max_val > 0 else 1
    if max_val / order < 2:
        y_max = 2 * order
    elif max_val / order < 5:
        y_max = 5 * order
    else:
        y_max = 10 * order
        
    # Avoid crazy limits
    if y_max < max_val:
        y_max = int(max_val * 1.1)

    n_points = len(data)
    
    # Helper to convert coordinates
    def get_coords(idx, val):
        x = margin["left"] + (idx / max(1, n_points - 1)) * plot_w
        # y is inverted in SVG
        y = margin["top"] + plot_h - ((val / y_max) * plot_h)
        return x, y
        
    # Generate points
    add_points = []
    del_points = []
    
    for i, row in enumerate(data):
        add_v = row.get("total_additions") or 0
        del_v = row.get("total_deletions") or 0
        add_points.append(get_coords(i, add_v))
        del_points.append(get_coords(i, del_v))
        
    # Render Path for Additions (Emerald)
    add_path_str = ""
    add_area_str = ""
    if add_points:
        # Stroke path
        add_path_str = "M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in add_points)
        # Area path
        first_x, first_y = add_points[0]
        last_x, last_y = add_points[-1]
        add_area_str = f"M {first_x:.1f},{margin['top']+plot_h:.1f} L " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in add_points) + f" L {last_x:.1f},{margin['top']+plot_h:.1f} Z"
        
    # Render Path for Deletions (Rose)
    del_path_str = ""
    del_area_str = ""
    if del_points:
        # Stroke path
        del_path_str = "M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in del_points)
        # Area path
        first_x, first_y = del_points[0]
        last_x, last_y = del_points[-1]
        del_area_str = f"M {first_x:.1f},{margin['top']+plot_h:.1f} L " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in del_points) + f" L {last_x:.1f},{margin['top']+plot_h:.1f} Z"

    # Build Y grid lines and labels
    y_labels = []
    grid_lines = []
    for i in range(5):
        val = int((i / 4) * y_max)
        _, y = get_coords(0, val)
        grid_lines.append(f'<line x1="{margin["left"]}" y1="{y:.1f}" x2="{width - margin["right"]}" y2="{y:.1f}" stroke="#334155" stroke-dasharray="4" stroke-width="1" />')
        y_labels.append(f'<text x="{margin["left"] - 10}" y="{y + 4:.1f}" fill="#94A3B8" font-family="sans-serif" font-size="11" text-anchor="end">{val:,}</text>')

    # Build X labels
    x_labels = []
    x_grid = []
    step = max(1, n_points // 7)  # Show up to 7 labels to avoid overlapping
    for i, row in enumerate(data):
        if i % step == 0 or i == n_points - 1:
            x, _ = get_coords(i, 0)
            date_str = row.get("commit_date") or ""
            # Format YYYY-MM-DD -> MM/DD or simple representation
            short_date = date_str[5:] if len(date_str) >= 10 else date_str
            x_labels.append(f'<text x="{x:.1f}" y="{margin["top"] + plot_h + 20}" fill="#94A3B8" font-family="sans-serif" font-size="11" text-anchor="middle">{short_date}</text>')
            x_grid.append(f'<line x1="{x:.1f}" y1="{margin["top"]}" x2="{x:.1f}" y2="{margin["top"] + plot_h}" stroke="#1E293B" stroke-width="1"/>')

    # SVGs string template
    svg = f"""
    <svg viewBox="0 0 {width} {height}" width="100%" height="100%" xmlns="http://www.w3.org/2000/svg">
        <defs>
            <linearGradient id="add-grad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stop-color="#10B981" stop-opacity="0.25"/>
                <stop offset="100%" stop-color="#10B981" stop-opacity="0.0"/>
            </linearGradient>
            <linearGradient id="del-grad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stop-color="#F43F5E" stop-opacity="0.25"/>
                <stop offset="100%" stop-color="#F43F5E" stop-opacity="0.0"/>
            </linearGradient>
        </defs>
        
        <!-- Grid & Axes -->
        {"".join(x_grid)}
        {"".join(grid_lines)}
        
        <!-- Y Axis Line -->
        <line x1="{margin["left"]}" y1="{margin["top"]}" x2="{margin["left"]}" y2="{margin["top"] + plot_h}" stroke="#475569" stroke-width="1.5"/>
        
        <!-- X Axis Line -->
        <line x1="{margin["left"]}" y1="{margin["top"] + plot_h}" x2="{width - margin["right"]}" y2="{margin["top"] + plot_h}" stroke="#475569" stroke-width="1.5"/>

        <!-- Area fills -->
        {f'<path d="{add_area_str}" fill="url(#add-grad)" />' if add_area_str else ''}
        {f'<path d="{del_area_str}" fill="url(#del-grad)" />' if del_area_str else ''}

        <!-- Line strokes -->
        {f'<path d="{add_path_str}" fill="none" stroke="#10B981" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" />' if add_path_str else ''}
        {f'<path d="{del_path_str}" fill="none" stroke="#F43F5E" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" />' if del_path_str else ''}

        <!-- Dots -->
        {"".join(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="4" fill="#10B981" stroke="#0F172A" stroke-width="1.5" />' for cx, cy in add_points)}
        {"".join(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="4" fill="#F43F5E" stroke="#0F172A" stroke-width="1.5" />' for cx, cy in del_points)}

        <!-- Labels -->
        {"".join(y_labels)}
        {"".join(x_labels)}
        
        <!-- Legend -->
        <g transform="translate({width - 240}, 10)">
            <rect x="0" y="0" width="8" height="8" rx="2" fill="#10B981"/>
            <text x="15" y="8" fill="#E2E8F0" font-family="sans-serif" font-size="11" font-weight="600">Additions</text>
            
            <rect x="90" y="0" width="8" height="8" rx="2" fill="#F43F5E"/>
            <text x="105" y="8" fill="#E2E8F0" font-family="sans-serif" font-size="11" font-weight="600">Deletions</text>
        </g>
    </svg>
    """
    return svg

def generate_heatmap_chart(data: list) -> str:
    """
    Generates an SVG heatmap grid of hour-of-day (X-axis, 0-23) by day-of-week (Y-axis, Sun-Sat).
    data schema: list of {'day_of_week': 0..6, 'hour_of_day': 0..23, 'commit_count': C}
    """
    width = 800
    height = 240
    
    # Initialize grid
    grid = [[0 for _ in range(24)] for _ in range(7)]
    max_commits = 0
    total_commits = 0
    
    for row in data:
        d = row.get("day_of_week")
        h = row.get("hour_of_day")
        c = row.get("commit_count") or 0
        if 0 <= d < 7 and 0 <= h < 24:
            grid[d][h] = c
            max_commits = max(max_commits, c)
            total_commits += c
            
    if total_commits == 0:
        return f"""
        <svg viewBox="0 0 {width} {height}" class="w-full h-full" xmlns="http://www.w3.org/2000/svg">
            <rect width="100%" height="100%" fill="none"/>
            <text x="{width/2}" y="{height/2}" fill="#94A3B8" font-family="sans-serif" font-size="16" text-anchor="middle" font-weight="500">
                Heatmap will display here once commits are registered.
            </text>
        </svg>
        """

    margin = {"left": 50, "right": 20, "top": 30, "bottom": 35}
    cell_w = (width - margin["left"] - margin["right"]) / 24
    cell_h = (height - margin["top"] - margin["bottom"]) / 7
    
    # Beautiful Indigo color gradient
    def get_color(count):
        if count == 0:
            return "#1E293B"  # Slate-800
        # Dynamic intensity scale
        intensity = count / max_commits
        if intensity <= 0.25:
            return "#312E81"  # Indigo-950
        elif intensity <= 0.5:
            return "#4338CA"  # Indigo-700
        elif intensity <= 0.75:
            return "#4F46E5"  # Indigo-600
        else:
            return "#818CF8"  # Indigo-400

    rects = []
    for d in range(7):
        for h in range(24):
            count = grid[d][h]
            color = get_color(count)
            x = margin["left"] + h * cell_w + 2
            y = margin["top"] + d * cell_h + 2
            rect_w = cell_w - 4
            rect_h = cell_h - 4
            
            # Tooltip trigger using SVG title
            rects.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{rect_w:.1f}" height="{rect_h:.1f}" rx="3" fill="{color}">'
                f'<title>{count} commits on {["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"][d]} at {h:02d}:00</title>'
                f'</rect>'
            )

    # Days of week labels (Y axis)
    day_labels = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    y_labels = []
    for d in range(7):
        y = margin["top"] + d * cell_h + cell_h / 2 + 4
        y_labels.append(f'<text x="{margin["left"] - 12}" y="{y:.1f}" fill="#94A3B8" font-family="sans-serif" font-size="11" text-anchor="end">{day_labels[d]}</text>')

    # Hours labels (X axis)
    x_labels = []
    for h in range(24):
        x = margin["left"] + h * cell_w + cell_w / 2
        # Display 12am, 6am, 12pm, 6pm, etc.
        if h % 3 == 0:
            label = "12am" if h == 0 else ("6am" if h == 6 else ("12pm" if h == 12 else ("6pm" if h == 18 else f"{h}")))
            x_labels.append(f'<text x="{x:.1f}" y="{height - margin["bottom"] + 18}" fill="#94A3B8" font-family="sans-serif" font-size="10" text-anchor="middle">{label}</text>')

    # Heatmap legend
    legend_colors = ["#1E293B", "#312E81", "#4338CA", "#4F46E5", "#818CF8"]
    legend_rects = []
    lx_start = width - margin["right"] - 180
    for idx, col in enumerate(legend_colors):
        lx = lx_start + idx * 25
        legend_rects.append(f'<rect x="{lx}" y="5" width="16" height="10" rx="2" fill="{col}"/>')
        
    legend_text = f"""
    <g transform="translate({lx_start - 35}, 14)">
        <text fill="#94A3B8" font-family="sans-serif" font-size="10" text-anchor="end">Less</text>
    </g>
    <g transform="translate({lx_start + 130}, 14)">
        <text fill="#94A3B8" font-family="sans-serif" font-size="10" text-anchor="start">More</text>
    </g>
    """

    svg = f"""
    <svg viewBox="0 0 {width} {height}" width="100%" height="100%" xmlns="http://www.w3.org/2000/svg">
        <g>
            {"".join(rects)}
        </g>
        <g>
            {"".join(y_labels)}
        </g>
        <g>
            {"".join(x_labels)}
        </g>
        <!-- Legend -->
        <g>
            {"".join(legend_rects)}
            {legend_text}
        </g>
    </svg>
    """
    return svg

def generate_donut_chart(data: list) -> str:
    """
    Generates a visual SVG donut chart for file type distribution.
    data schema: list of {'extension': '.py', 'total_additions': A, 'total_deletions': D, ...}
    """
    width = 400
    height = 240
    
    # Filter and calculate totals
    stats = []
    total_changes = 0
    for row in data:
        ext = row.get("extension") or "other"
        adds = row.get("total_additions") or 0
        dels = row.get("total_deletions") or 0
        total = adds + dels
        if total > 0:
            stats.append({"ext": ext, "total": total})
            total_changes += total
            
    if total_changes == 0:
        return f"""
        <svg viewBox="0 0 {width} {height}" class="w-full h-full" xmlns="http://www.w3.org/2000/svg">
            <rect width="100%" height="100%" fill="none"/>
            <text x="{width/2}" y="{height/2}" fill="#94A3B8" font-family="sans-serif" font-size="14" text-anchor="middle" font-weight="500">
                Commit changes to see file distributions!
            </text>
        </svg>
        """

    # Harmonized palette
    colors = ["#6366F1", "#8B5CF6", "#10B981", "#F59E0B", "#F43F5E", "#64748B"]
    
    # Circumference for r = 70 is ~439.82
    radius = 65
    circumference = 2 * math.pi * radius
    stroke_width = 24
    
    cx = 120
    cy = 120
    
    circles = []
    legend = []
    offset = 0
    
    for idx, stat in enumerate(stats):
        color = colors[idx % len(colors)]
        percentage = stat["total"] / total_changes
        slice_len = circumference * percentage
        dash_offset = -offset
        
        # Donut Slice
        circles.append(
            f'<circle cx="{cx}" cy="{cy}" r="{radius}" fill="transparent" '
            f'stroke="{color}" stroke-width="{stroke_width}" '
            f'stroke-dasharray="{slice_len:.2f} {circumference:.2f}" '
            f'stroke-dashoffset="{dash_offset:.2f}" '
            f'transform="rotate(-90 {cx} {cy})">'
            f'<title>{stat["ext"]}: {stat["total"]:,} lines ({percentage*100:.1f}%)</title>'
            f'</circle>'
        )
        
        # Legend item
        ly = 35 + idx * 28
        legend.append(
            f'<g transform="translate(240, {ly})">'
            f'<circle cx="10" cy="8" r="6" fill="{color}"/>'
            f'<text x="24" y="12" fill="#E2E8F0" font-family="sans-serif" font-size="12" font-weight="600">{stat["ext"]}</text>'
            f'<text x="140" y="12" fill="#94A3B8" font-family="sans-serif" font-size="11" text-anchor="end">{percentage*100:.1f}%</text>'
            f'</g>'
        )
        
        offset += slice_len

    svg = f"""
    <svg viewBox="0 0 {width} {height}" width="100%" height="100%" xmlns="http://www.w3.org/2000/svg">
        <g>
            {"".join(circles)}
            <!-- Center label -->
            <circle cx="{cx}" cy="{cy}" r="{radius - stroke_width/2 - 2}" fill="#0F172A"/>
            <text x="{cx}" y="{cy - 5}" fill="#94A3B8" font-family="sans-serif" font-size="10" text-anchor="middle" letter-spacing="1">CHANGES</text>
            <text x="{cx}" y="{cy + 15}" fill="#F8FAFC" font-family="sans-serif" font-size="16" font-weight="800" text-anchor="middle">{total_changes:,}</text>
        </g>
        <g>
            {"".join(legend)}
        </g>
    </svg>
    """
    return svg
