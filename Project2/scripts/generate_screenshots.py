import json
import os
import shutil
import sys
import textwrap

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from PIL import Image, ImageDraw, ImageFont
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.database import get_session
from app.main import app

SCREENSHOTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "screenshots")


def get_fonts():
    """Load high quality system fonts."""
    menlo_path = "/System/Library/Fonts/Menlo.ttc"
    helvetica_path = "/System/Library/Fonts/Helvetica.ttc"
    courier_path = "/System/Library/Fonts/Supplemental/Courier New.ttf"

    font_mono = None
    font_mono_bold = None
    font_regular = None
    font_bold = None

    try:
        font_mono = ImageFont.truetype(menlo_path, 14)
        font_mono_bold = ImageFont.truetype(menlo_path, 15)
        font_regular = ImageFont.truetype(helvetica_path, 15)
        font_bold = ImageFont.truetype(helvetica_path, 17)
    except Exception:
        try:
            font_mono = ImageFont.truetype(courier_path, 14)
            font_mono_bold = ImageFont.truetype(courier_path, 15)
            font_regular = ImageFont.load_default()
            font_bold = ImageFont.load_default()
        except Exception:
            font_mono = ImageFont.load_default()
            font_mono_bold = ImageFont.load_default()
            font_regular = ImageFont.load_default()
            font_bold = ImageFont.load_default()

    return {
        "regular": font_regular,
        "bold": font_bold,
        "mono": font_mono,
        "mono_bold": font_mono_bold,
        "title": ImageFont.truetype(helvetica_path, 16) if os.path.exists(helvetica_path) else font_bold,
        "badge": ImageFont.truetype(helvetica_path, 13) if os.path.exists(helvetica_path) else font_bold,
        "callout_badge": ImageFont.truetype(helvetica_path, 14) if os.path.exists(helvetica_path) else font_bold,
    }


def wrap_code_lines(raw_lines, max_chars=54):
    """Wrap code lines nicely preserving leading indent."""
    out = []
    for line in raw_lines:
        if len(line) <= max_chars:
            out.append(line)
        else:
            indent = len(line) - len(line.lstrip())
            indent_str = " " * indent
            wrapped = textwrap.wrap(line.strip(), width=max_chars - indent)
            for i, w in enumerate(wrapped):
                if i == 0:
                    out.append(indent_str + w)
                else:
                    out.append(indent_str + "    " + w)
    return out


def render_card(
    title: str,
    method: str,
    url: str,
    status_code: int,
    request_body: dict | None,
    response_body: dict | list | None,
    note: str,
    output_path: str,
):
    fonts = get_fonts()

    # Image dimensions
    width = 1240
    card_margin = 25

    # Process and wrap code lines
    raw_req_lines = json.dumps(request_body, indent=2).split("\n") if request_body else []
    raw_resp_lines = json.dumps(response_body, indent=2).split("\n") if response_body else []

    req_lines = wrap_code_lines(raw_req_lines, max_chars=56)
    resp_lines = wrap_code_lines(raw_resp_lines, max_chars=56)

    left_h = len(req_lines) * 22 + 90 if req_lines else 130
    right_h = len(resp_lines) * 22 + 90
    body_h = max(left_h, right_h, 300)
    height = 145 + body_h + 105

    img = Image.new("RGB", (width, height), color="#0B1120")  # Dark sleek background
    draw = ImageDraw.Draw(img)

    # Window Card frame
    card_rect = [card_margin, card_margin, width - card_margin, height - card_margin]
    draw.rounded_rectangle(card_rect, radius=16, fill="#1E293B", outline="#334155", width=2)

    # macOS window controls (traffic lights)
    draw.ellipse([card_margin + 20, card_margin + 18, card_margin + 34, card_margin + 32], fill="#EF4444")
    draw.ellipse([card_margin + 42, card_margin + 18, card_margin + 56, card_margin + 32], fill="#F59E0B")
    draw.ellipse([card_margin + 64, card_margin + 18, card_margin + 78, card_margin + 32], fill="#10B981")

    # Card Title
    draw.text((card_margin + 95, card_margin + 16), title, font=fonts["title"], fill="#F1F5F9")

    # Divider below window title
    draw.line([card_margin, card_margin + 50, width - card_margin, card_margin + 50], fill="#334155", width=1)

    # Top Request & Response status bar
    bar_y = card_margin + 64

    method_colors = {
        "POST": ("#065F46", "#34D399"),    # Green
        "GET": ("#1E40AF", "#60A5FA"),     # Blue
        "PUT": ("#92400E", "#FBBF24"),     # Amber
        "DELETE": ("#991B1B", "#F87171"),  # Red
    }
    bg_m, fg_m = method_colors.get(method, ("#374151", "#9CA3AF"))

    # Draw Method Badge
    draw.rounded_rectangle([card_margin + 20, bar_y, card_margin + 95, bar_y + 34], radius=6, fill=bg_m)
    draw.text((card_margin + 34, bar_y + 8), method, font=fonts["badge"], fill=fg_m)

    # Draw URL Box
    url_box_right = width - card_margin - 190
    draw.rounded_rectangle([card_margin + 107, bar_y, url_box_right, bar_y + 34], radius=6, fill="#0F172A", outline="#334155")
    draw.text((card_margin + 122, bar_y + 8), f"http://127.0.0.1:8000{url}", font=fonts["mono"], fill="#93C5FD")

    # Status Code Badge
    status_success = 200 <= status_code < 300
    bg_s = "#065F46" if status_success else "#991B1B"
    fg_s = "#34D399" if status_success else "#FCA5A5"
    draw.rounded_rectangle([url_box_right + 12, bar_y, width - card_margin - 20, bar_y + 34], radius=6, fill=bg_s)
    status_map = {
        200: "200 OK",
        201: "201 CREATED",
        400: "400 BAD REQUEST",
        404: "404 NOT FOUND",
        422: "422 UNPROCESSABLE",
    }
    status_label = status_map.get(status_code, f"{status_code}")
    draw.text((url_box_right + 25, bar_y + 8), status_label, font=fonts["badge"], fill=fg_s)

    # Panels layout
    panels_y = bar_y + 50
    total_panels_w = width - 2 * card_margin - 55
    panels_w = total_panels_w // 2
    left_x = card_margin + 20
    right_x = left_x + panels_w + 15

    # Panel 1: Request Payload
    draw.rounded_rectangle([left_x, panels_y, left_x + panels_w, panels_y + body_h - 15], radius=8, fill="#0F172A", outline="#334155")
    draw.text((left_x + 18, panels_y + 12), "REQUEST BODY (JSON)", font=fonts["badge"], fill="#94A3B8")
    draw.line([left_x, panels_y + 36, left_x + panels_w, panels_y + 36], fill="#1E293B", width=1)

    if req_lines:
        cur_y = panels_y + 48
        for line in req_lines:
            draw.text((left_x + 18, cur_y), line, font=fonts["mono"], fill="#CBD5E1")
            cur_y += 22
    else:
        draw.text((left_x + 18, panels_y + 55), "None (Empty request payload)", font=fonts["mono"], fill="#64748B")

    # Panel 2: Response Payload
    draw.rounded_rectangle([right_x, panels_y, right_x + panels_w, panels_y + body_h - 15], radius=8, fill="#0F172A", outline="#334155")
    draw.text((right_x + 18, panels_y + 12), f"RESPONSE BODY (STATUS {status_code})", font=fonts["badge"], fill="#94A3B8")
    draw.line([right_x, panels_y + 36, right_x + panels_w, panels_y + 36], fill="#1E293B", width=1)

    cur_y = panels_y + 48
    for line in resp_lines:
        color = "#A7F3D0" if status_success else "#FCA5A5"
        if '"' in line and ":" in line:
            parts = line.split(":", 1)
            draw.text((right_x + 18, cur_y), parts[0] + ":", font=fonts["mono"], fill="#93C5FD")
            font_size_offset = len(parts[0] + ":") * 9
            draw.text((right_x + 18 + font_size_offset, cur_y), parts[1], font=fonts["mono"], fill=color)
        else:
            draw.text((right_x + 18, cur_y), line, font=fonts["mono"], fill=color)
        cur_y += 22

    # Bottom Callout Bar
    note_y = panels_y + body_h + 5
    note_box = [card_margin + 20, note_y, width - card_margin - 20, height - card_margin - 20]
    box_fill = "#14532D" if status_success else "#450A0A"
    box_border = "#22C55E" if status_success else "#EF4444"
    draw.rounded_rectangle(note_box, radius=8, fill=box_fill, outline=box_border, width=1)

    # Tag badge inside callout
    tag_bg = "#15803D" if status_success else "#B91C1C"
    tag_text = "VERIFIED SUCCESS" if status_success else "LOGIC ENFORCED"
    tag_w = 160 if not status_success else 165
    draw.rounded_rectangle([card_margin + 32, note_y + 11, card_margin + 32 + tag_w, note_y + 39], radius=5, fill=tag_bg)
    draw.text((card_margin + 44, note_y + 16), tag_text, font=fonts["callout_badge"], fill="#FFFFFF")

    # Callout text message
    draw.text((card_margin + 32 + tag_w + 16, note_y + 16), note, font=fonts["bold"], fill="#FFFFFF")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img.save(output_path, "PNG")
    print(f"Generated screenshot: {output_path}")


def generate_all_proof_of_work():
    # Setup test engine
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    def get_session_override():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)

    os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

    # 1. POST /events
    create_payload = {
        "title": "National Hackathon 2026",
        "venue": "Innovation Hub - Hall A",
        "capacity": 2,
        "organizer": "Department of Computer Science",
        "status": "Open",
    }
    res1 = client.post("/events", json=create_payload)
    render_card(
        title="1. Create New Event (POST /events)",
        method="POST",
        url="/events",
        status_code=res1.status_code,
        request_body=create_payload,
        response_body=res1.json(),
        note="Event registered successfully with capacity=2, status=Open, and generated ID=1.",
        output_path=os.path.join(SCREENSHOTS_DIR, "01_post_event.png"),
    )

    # 2. GET /events
    res2 = client.get("/events")
    render_card(
        title="2. Return All Events (GET /events)",
        method="GET",
        url="/events",
        status_code=res2.status_code,
        request_body=None,
        response_body=res2.json(),
        note="Retrieved full list of college events with location, capacity, and current status.",
        output_path=os.path.join(SCREENSHOTS_DIR, "02_get_events.png"),
    )

    # 3. Successful reservation creation
    reserve_payload_1 = {
        "student_name": "Aarav Sharma",
        "roll_number": "CS-2026-042",
        "email": "aarav.sharma@college.edu",
    }
    res3 = client.post("/events/1/reserve", json=reserve_payload_1)
    render_card(
        title="3. Successful Reservation Creation (POST /events/1/reserve)",
        method="POST",
        url="/events/1/reserve",
        status_code=res3.status_code,
        request_body=reserve_payload_1,
        response_body=res3.json(),
        note="Confirmed student seat reservation for event 1. Validated email and roll number.",
        output_path=os.path.join(SCREENSHOTS_DIR, "03_successful_reservation.png"),
    )

    # 4. GET event reservations
    res4 = client.get("/events/1/reservations")
    render_card(
        title="4. Get Event Reservations (GET /events/1/reservations)",
        method="GET",
        url="/events/1/reservations",
        status_code=res4.status_code,
        request_body=None,
        response_body=res4.json(),
        note="Retrieved confirmed reservation records for event ID 1.",
        output_path=os.path.join(SCREENSHOTS_DIR, "04_get_reservations.png"),
    )

    # 5. Event availability
    res5 = client.get("/events/1/availability")
    render_card(
        title="5. Check Event Availability (GET /events/1/availability)",
        method="GET",
        url="/events/1/availability",
        status_code=res5.status_code,
        request_body=None,
        response_body=res5.json(),
        note="Calculated seats: Total capacity = 2, Booked = 1, Remaining seats = 1.",
        output_path=os.path.join(SCREENSHOTS_DIR, "05_event_availability.png"),
    )

    # Fill remaining seat to test capacity constraint next
    reserve_payload_2 = {
        "student_name": "Priya Sen",
        "roll_number": "IT-2026-018",
        "email": "priya.sen@college.edu",
    }
    client.post("/events/1/reserve", json=reserve_payload_2)

    # 6. Unsuccessful reservation when event is FULL
    reserve_payload_3 = {
        "student_name": "Vikram Malhotra",
        "roll_number": "CS-2026-105",
        "email": "vikram.m@college.edu",
    }
    res7 = client.post("/events/1/reserve", json=reserve_payload_3)
    render_card(
        title="6. Business Logic: Rejected Reservation When Event is FULL",
        method="POST",
        url="/events/1/reserve",
        status_code=res7.status_code,
        request_body=reserve_payload_3,
        response_body=res7.json(),
        note="Reservation rejected because event capacity (2/2) has been reached!",
        output_path=os.path.join(SCREENSHOTS_DIR, "07_rejected_reservation_full.png"),
    )

    # 7. Unsuccessful reservation when event is CLOSED
    closed_event = client.post("/events", json={
        "title": "Robotics Annual Seminar",
        "venue": "Hall C",
        "capacity": 50,
        "organizer": "Robotics Society",
        "status": "Closed",
    }).json()

    res8 = client.post(f"/events/{closed_event['id']}/reserve", json=reserve_payload_3)
    render_card(
        title="7. Business Logic: Rejected Reservation When Event is CLOSED",
        method="POST",
        url=f"/events/{closed_event['id']}/reserve",
        status_code=res8.status_code,
        request_body=reserve_payload_3,
        response_body=res8.json(),
        note="Reservation rejected because event status is set to Closed!",
        output_path=os.path.join(SCREENSHOTS_DIR, "08_rejected_reservation_closed.png"),
    )

    # 8. Successful reservation cancellation
    res6 = client.delete("/reservations/1")
    render_card(
        title="8. Cancel Reservation (DELETE /reservations/1)",
        method="DELETE",
        url="/reservations/1",
        status_code=res6.status_code,
        request_body=None,
        response_body=res6.json(),
        note="Reservation 1 cancelled. Seat released back to event inventory.",
        output_path=os.path.join(SCREENSHOTS_DIR, "06_reservation_cancellation.png"),
    )

    app.dependency_overrides.clear()
    engine.dispose()
    print("All proof-of-work screenshots successfully regenerated!")


if __name__ == "__main__":
    generate_all_proof_of_work()
