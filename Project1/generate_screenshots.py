import os
import json
from PIL import Image, ImageDraw, ImageFont
from database import engine, create_db_and_tables, sqlite_file_name
from main import app
from fastapi.testclient import TestClient

# Output directory for screenshots
SCREENSHOT_DIR = os.path.join(os.path.dirname(__file__), "screenshots")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

# Remove old db file if exists to start with clean test data
if os.path.exists(sqlite_file_name):
    os.remove(sqlite_file_name)

create_db_and_tables()

client = TestClient(app)

def try_load_font(size):
    font_paths = [
        "/System/Library/Fonts/Monaco.ttf",
        "/System/Library/Fonts/Supplemental/Courier New.ttf",
        "/System/Library/Fonts/SFNSMono.ttf",
        "/Library/Fonts/Arial.ttf",
    ]
    for p in font_paths:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()

font_title = try_load_font(17)
font_body = try_load_font(14)

def create_api_card(title, method, endpoint, req_body, status_code, res_body, output_path):
    width = 920
    method_color = {
        "POST": "#10b981",
        "GET": "#3b82f6",
        "PUT": "#f59e0b",
        "DELETE": "#ef4444"
    }.get(method, "#6b7280")
    
    status_color = "#10b981" if status_code in (200, 201) else "#ef4444"
    
    req_json_str = json.dumps(req_body, indent=2) if req_body is not None else "None (No Request Body)"
    res_json_str = json.dumps(res_body, indent=2) if isinstance(res_body, (dict, list)) else str(res_body)

    lines_req = req_json_str.split("\n")
    lines_res = res_json_str.split("\n")
    
    header_h = 50
    banner_h = 55
    req_title_h = 30
    req_content_h = len(lines_req) * 22 + 20
    res_title_h = 30
    res_content_h = len(lines_res) * 22 + 20
    
    total_h = header_h + banner_h + req_title_h + req_content_h + res_title_h + res_content_h + 40

    img = Image.new("RGB", (width, total_h), "#0f172a")
    draw = ImageDraw.Draw(img)

    # Draw Mac OS window bar
    draw.rectangle([0, 0, width, 40], fill="#1e293b")
    draw.ellipse([15, 13, 27, 25], fill="#ff5f56") # red
    draw.ellipse([35, 13, 47, 25], fill="#ffbd2e") # yellow
    draw.ellipse([55, 13, 67, 25], fill="#27c93f") # green
    
    draw.text((80, 11), f"FastAPI Lost & Found REST API — {title}", fill="#94a3b8", font=font_title)

    # Endpoint banner
    y = 50
    draw.rectangle([20, y, width - 20, y + 45], fill="#1e293b", outline="#334155", width=1)
    
    # Method badge
    draw.rectangle([32, y + 7, 115, y + 37], fill=method_color)
    draw.text((42, y + 10), method, fill="#ffffff", font=font_title)
    
    # Endpoint text
    draw.text((130, y + 10), endpoint, fill="#f8fafc", font=font_title)
    
    # Status code badge on right
    status_text = f"HTTP {status_code}"
    draw.rectangle([width - 155, y + 7, width - 32, y + 37], fill=status_color)
    draw.text((width - 145, y + 10), status_text, fill="#ffffff", font=font_title)

    # Request Section
    y += 55
    draw.text((25, y), "REQUEST DATA Payload:", fill="#94a3b8", font=font_title)
    y += 28
    draw.rectangle([20, y, width - 20, y + req_content_h], fill="#181825", outline="#313244", width=1)
    
    ry = y + 10
    for line in lines_req:
        draw.text((35, ry), line, fill="#cd4244" if "None" in line else "#cdd6f4", font=font_body)
        ry += 22
        
    # Response Section
    y += req_content_h + 20
    draw.text((25, y), "RESPONSE Body:", fill="#94a3b8", font=font_title)
    y += 28
    draw.rectangle([20, y, width - 20, y + res_content_h], fill="#181825", outline="#313244", width=1)
    
    ry = y + 10
    for line in lines_res:
        color = "#a6e3a1" if status_code in (200, 201) else "#f38ba8"
        draw.text((35, ry), line, fill=color, font=font_body)
        ry += 22

    img.save(output_path, "PNG")
    print(f"Generated screenshot: {output_path}")

# Run API calls & generate proof-of-work screenshots

# 1. POST /items (Item 1)
req1 = {
    "title": "Blue Water Bottle",
    "description": "Stainless steel Milton 1L bottle with college sticker",
    "category": "Accessories",
    "location": "Library 2nd Floor",
    "reported_by": "Sachin",
    "status": "Lost"
}
res1 = client.post("/items", json=req1)
create_api_card("POST /items", "POST", "/items", req1, res1.status_code, res1.json(), os.path.join(SCREENSHOT_DIR, "01_post_items.png"))

# Seed Item 2
req2 = {
    "title": "Dell Laptop Charger",
    "description": "65W Type-C laptop adapter found under desk",
    "category": "Electronics",
    "location": "Computer Lab 3",
    "reported_by": "Alice Smith",
    "status": "Found"
}
client.post("/items", json=req2)

# Seed Item 3
req3 = {
    "title": "College ID Card",
    "description": "Student ID card belonging to Mechanical Dept",
    "category": "Documents",
    "location": "Main Cafeteria",
    "reported_by": "Bob Wilson",
    "status": "Lost"
}
client.post("/items", json=req3)

# 2. GET /items
res_all = client.get("/items")
create_api_card("GET /items", "GET", "/items", None, res_all.status_code, res_all.json(), os.path.join(SCREENSHOT_DIR, "02_get_items.png"))

# 3. GET /items/{item_id}
res_item = client.get("/items/1")
create_api_card("GET /items/{item_id}", "GET", "/items/1", None, res_item.status_code, res_item.json(), os.path.join(SCREENSHOT_DIR, "03_get_item_by_id.png"))

# 4. PUT /items/{item_id}
req_put = {
    "status": "Returned",
    "location": "Security Office (Handed over to owner)"
}
res_put = client.put("/items/1", json=req_put)
create_api_card("PUT /items/{item_id}", "PUT", "/items/1", req_put, res_put.status_code, res_put.json(), os.path.join(SCREENSHOT_DIR, "04_put_item.png"))

# 5. DELETE /items/{item_id}
res_del = client.delete("/items/3")
create_api_card("DELETE /items/{item_id}", "DELETE", "/items/3", None, res_del.status_code, res_del.json(), os.path.join(SCREENSHOT_DIR, "05_delete_item.png"))

# 6. Status filtering
res_status = client.get("/items/status/Lost")
create_api_card("Status Filtering", "GET", "/items/status/Lost", None, res_status.status_code, res_status.json(), os.path.join(SCREENSHOT_DIR, "06_status_filtering.png"))

# 7. Category filtering
res_cat = client.get("/items/category/Electronics")
create_api_card("Category Filtering", "GET", "/items/category/Electronics", None, res_cat.status_code, res_cat.json(), os.path.join(SCREENSHOT_DIR, "07_category_filtering.png"))

# 8. Invalid Request / Error Response
req_invalid = {
    "title": "   ",
    "description": "ab",
    "category": "Electronics",
    "location": "Gym",
    "reported_by": "Unknown",
    "status": "Stolen"
}
res_invalid = client.post("/items", json=req_invalid)
create_api_card("Invalid Request & Error Response", "POST", "/items", req_invalid, res_invalid.status_code, res_invalid.json(), os.path.join(SCREENSHOT_DIR, "08_invalid_request_validation_error.png"))

print("All proof-of-work screenshots successfully generated!")
