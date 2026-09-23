import unittest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.database import get_session
from app.main import app


class TestCollegeEventAPI(unittest.TestCase):
    """Automated test suite verifying all Event and Reservation API endpoints and business logic."""

    def setUp(self):
        """Create an isolated in-memory SQLite database for each test."""
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(self.engine)

        def get_session_override():
            with Session(self.engine) as session:
                yield session

        app.dependency_overrides[get_session] = get_session_override
        self.client = TestClient(app)

    def tearDown(self):
        """Clean up dependency overrides and dispose engine after test run."""
        app.dependency_overrides.clear()
        self.engine.dispose()

    # ---------------------------------------------------------
    # Event Tests
    # ---------------------------------------------------------

    def test_create_event_success(self):
        """Test successful event creation (POST /events)."""
        payload = {
            "title": "AI & Robotics Workshop",
            "venue": "Auditorium A",
            "capacity": 50,
            "organizer": "Robotics Club",
            "status": "Open",
        }
        response = self.client.post("/events", json=payload)
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["title"], payload["title"])
        self.assertEqual(data["capacity"], 50)
        self.assertEqual(data["status"], "Open")
        self.assertIn("id", data)

    def test_create_event_invalid_capacity(self):
        """Test that capacity must be greater than 0."""
        payload = {
            "title": "Invalid Workshop",
            "venue": "Room 101",
            "capacity": 0,  # Invalid: capacity must be > 0
            "organizer": "Tech Dept",
            "status": "Open",
        }
        response = self.client.post("/events", json=payload)
        self.assertEqual(response.status_code, 422)

    def test_create_event_negative_capacity(self):
        """Test that negative capacity is rejected."""
        payload = {
            "title": "Invalid Workshop",
            "venue": "Room 101",
            "capacity": -5,
            "organizer": "Tech Dept",
            "status": "Open",
        }
        response = self.client.post("/events", json=payload)
        self.assertEqual(response.status_code, 422)

    def test_create_event_empty_fields(self):
        """Test that title, venue, or organizer cannot be empty strings."""
        payload = {
            "title": "   ",
            "venue": "Room 101",
            "capacity": 20,
            "organizer": "Tech Dept",
            "status": "Open",
        }
        response = self.client.post("/events", json=payload)
        self.assertEqual(response.status_code, 422)

    def test_list_events(self):
        """Test returning all events (GET /events)."""
        self.client.post("/events", json={
            "title": "Hackathon 2026",
            "venue": "Innovation Lab",
            "capacity": 100,
            "organizer": "Coding Club",
            "status": "Open",
        })
        self.client.post("/events", json={
            "title": "Web3 Seminar",
            "venue": "Seminar Hall B",
            "capacity": 30,
            "organizer": "Blockchain Society",
            "status": "Open",
        })
        response = self.client.get("/events")
        self.assertEqual(response.status_code, 200)
        events = response.json()
        self.assertGreaterEqual(len(events), 2)

    def test_get_event_by_id(self):
        """Test getting a specific event (GET /events/{event_id})."""
        create_res = self.client.post("/events", json={
            "title": "Cybersecurity Conclave",
            "venue": "Auditorium B",
            "capacity": 40,
            "organizer": "Cyber Cell",
            "status": "Open",
        })
        event_id = create_res.json()["id"]

        # Existing event
        res = self.client.get(f"/events/{event_id}")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["id"], event_id)
        self.assertEqual(res.json()["title"], "Cybersecurity Conclave")

        # Non-existent event
        res_404 = self.client.get("/events/999999")
        self.assertEqual(res_404.status_code, 404)

    def test_update_event(self):
        """Test updating event information (PUT /events/{event_id})."""
        create_res = self.client.post("/events", json={
            "title": "Cloud Computing 101",
            "venue": "Room 204",
            "capacity": 25,
            "organizer": "Cloud Club",
            "status": "Open",
        })
        event_id = create_res.json()["id"]

        update_res = self.client.put(f"/events/{event_id}", json={
            "venue": "Main Hall",
            "status": "Closed",
        })
        self.assertEqual(update_res.status_code, 200)
        updated = update_res.json()
        self.assertEqual(updated["venue"], "Main Hall")
        self.assertEqual(updated["status"], "Closed")
        self.assertEqual(updated["title"], "Cloud Computing 101")

    def test_delete_event(self):
        """Test deleting an event and cascading reservations (DELETE /events/{event_id})."""
        create_res = self.client.post("/events", json={
            "title": "IoT Workshop",
            "venue": "Lab 4",
            "capacity": 15,
            "organizer": "IoT Club",
            "status": "Open",
        })
        event_id = create_res.json()["id"]

        # Add reservation
        res = self.client.post(f"/events/{event_id}/reserve", json={
            "student_name": "Test Student",
            "roll_number": "IOT-01",
            "email": "iot@college.edu",
        })
        res_id = res.json()["id"]

        # Delete event
        delete_res = self.client.delete(f"/events/{event_id}")
        self.assertEqual(delete_res.status_code, 200)

        # Event should now be 404
        self.assertEqual(self.client.get(f"/events/{event_id}").status_code, 404)

        # Reservation should also be gone
        self.assertEqual(self.client.delete(f"/reservations/{res_id}").status_code, 404)

    # ---------------------------------------------------------
    # Reservation Tests & Business Logic
    # ---------------------------------------------------------

    def test_reserve_seat_success(self):
        """Test successful reservation creation (POST /events/{event_id}/reserve)."""
        ev = self.client.post("/events", json={
            "title": "DevOps Bootcamp",
            "venue": "Lab 3",
            "capacity": 10,
            "organizer": "DevOps Guild",
            "status": "Open",
        }).json()

        res = self.client.post(f"/events/{ev['id']}/reserve", json={
            "student_name": "Aarav Sharma",
            "roll_number": "CS2026-001",
            "email": "aarav.sharma@college.edu",
        })
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertEqual(data["student_name"], "Aarav Sharma")
        self.assertEqual(data["roll_number"], "CS2026-001")
        self.assertEqual(data["email"], "aarav.sharma@college.edu")
        self.assertEqual(data["event_id"], ev["id"])

    def test_reserve_seat_invalid_email(self):
        """Test validation: invalid email format is rejected."""
        ev = self.client.post("/events", json={
            "title": "Design Thinking",
            "venue": "Studio 1",
            "capacity": 15,
            "organizer": "Design Club",
            "status": "Open",
        }).json()

        res = self.client.post(f"/events/{ev['id']}/reserve", json={
            "student_name": "Rohan Verma",
            "roll_number": "DS2026-010",
            "email": "not-an-email",
        })
        self.assertEqual(res.status_code, 422)

    def test_reserve_seat_empty_student_name(self):
        """Test validation: empty student name is rejected."""
        ev = self.client.post("/events", json={
            "title": "Design Thinking",
            "venue": "Studio 1",
            "capacity": 15,
            "organizer": "Design Club",
            "status": "Open",
        }).json()

        res = self.client.post(f"/events/{ev['id']}/reserve", json={
            "student_name": "   ",
            "roll_number": "DS2026-010",
            "email": "rohan@college.edu",
        })
        self.assertEqual(res.status_code, 422)

    def test_reserve_seat_non_existent_event(self):
        """Test that reservation fails if event does not exist (404)."""
        res = self.client.post("/events/99999/reserve", json={
            "student_name": "Neha Patel",
            "roll_number": "IT2026-025",
            "email": "neha@college.edu",
        })
        self.assertEqual(res.status_code, 404)

    def test_reserve_seat_closed_event(self):
        """Test business logic: prevent reservation when event is Closed."""
        ev = self.client.post("/events", json={
            "title": "Closed Symposium",
            "venue": "Room 5",
            "capacity": 50,
            "organizer": "Dean Office",
            "status": "Closed",
        }).json()

        res = self.client.post(f"/events/{ev['id']}/reserve", json={
            "student_name": "Kavya Singh",
            "roll_number": "EC2026-042",
            "email": "kavya@college.edu",
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn("Closed", res.json()["detail"])

    def test_reserve_seat_capacity_limit(self):
        """Test business logic: prevent reservations when event is already full."""
        ev = self.client.post("/events", json={
            "title": "Micro-Workshop",
            "venue": "Lab 1",
            "capacity": 2,
            "organizer": "AI Club",
            "status": "Open",
        }).json()
        event_id = ev["id"]

        # 1st reservation
        res1 = self.client.post(f"/events/{event_id}/reserve", json={
            "student_name": "Student One",
            "roll_number": "ST-001",
            "email": "st1@college.edu",
        })
        self.assertEqual(res1.status_code, 201)

        # 2nd reservation
        res2 = self.client.post(f"/events/{event_id}/reserve", json={
            "student_name": "Student Two",
            "roll_number": "ST-002",
            "email": "st2@college.edu",
        })
        self.assertEqual(res2.status_code, 201)

        # 3rd reservation (exceeds capacity of 2)
        res3 = self.client.post(f"/events/{event_id}/reserve", json={
            "student_name": "Student Three",
            "roll_number": "ST-003",
            "email": "st3@college.edu",
        })
        self.assertEqual(res3.status_code, 400)
        self.assertIn("maximum capacity", res3.json()["detail"].lower())

    def test_reserve_seat_duplicate_prevention(self):
        """Test preventing duplicate reservations by the same student for the same event."""
        ev = self.client.post("/events", json={
            "title": "Quantum Computing Seminar",
            "venue": "Lab 2",
            "capacity": 10,
            "organizer": "Physics Dept",
            "status": "Open",
        }).json()

        # Initial reservation
        res1 = self.client.post(f"/events/{ev['id']}/reserve", json={
            "student_name": "Priya Sen",
            "roll_number": "PH2026-08",
            "email": "priya@college.edu",
        })
        self.assertEqual(res1.status_code, 201)

        # Duplicate reservation with same roll number
        res2 = self.client.post(f"/events/{ev['id']}/reserve", json={
            "student_name": "Priya Sen",
            "roll_number": "PH2026-08",
            "email": "priya2@college.edu",
        })
        self.assertEqual(res2.status_code, 400)
        self.assertIn("already has a reservation", res2.json()["detail"])

    # ---------------------------------------------------------
    # Availability & Cancellation Tests
    # ---------------------------------------------------------

    def test_event_availability(self):
        """Test GET /events/{event_id}/availability returns accurate counts."""
        ev = self.client.post("/events", json={
            "title": "Data Science Summit",
            "venue": "Auditorium C",
            "capacity": 5,
            "organizer": "Data Club",
            "status": "Open",
        }).json()
        event_id = ev["id"]

        # Initial check
        avail0 = self.client.get(f"/events/{event_id}/availability").json()
        self.assertEqual(avail0, {"capacity": 5, "booked": 0, "remaining": 5})

        # Book 2 seats
        self.client.post(f"/events/{event_id}/reserve", json={
            "student_name": "User 1",
            "roll_number": "U-1",
            "email": "u1@college.edu",
        })
        self.client.post(f"/events/{event_id}/reserve", json={
            "student_name": "User 2",
            "roll_number": "U-2",
            "email": "u2@college.edu",
        })

        # Check updated availability
        avail1 = self.client.get(f"/events/{event_id}/availability").json()
        self.assertEqual(avail1, {"capacity": 5, "booked": 2, "remaining": 3})

    def test_list_event_reservations(self):
        """Test GET /events/{event_id}/reservations returns all event reservations."""
        ev = self.client.post("/events", json={
            "title": "Flutter Workshop",
            "venue": "Lab 5",
            "capacity": 20,
            "organizer": "Mobile Club",
            "status": "Open",
        }).json()

        self.client.post(f"/events/{ev['id']}/reserve", json={
            "student_name": "Ananya Roy",
            "roll_number": "MO-001",
            "email": "ananya@college.edu",
        })

        res = self.client.get(f"/events/{ev['id']}/reservations")
        self.assertEqual(res.status_code, 200)
        reservations = res.json()
        self.assertEqual(len(reservations), 1)
        self.assertEqual(reservations[0]["student_name"], "Ananya Roy")

    def test_cancel_reservation(self):
        """Test DELETE /reservations/{reservation_id} frees up seats."""
        ev = self.client.post("/events", json={
            "title": "Game Dev Workshop",
            "venue": "Hall D",
            "capacity": 1,
            "organizer": "Gaming Club",
            "status": "Open",
        }).json()

        booking = self.client.post(f"/events/{ev['id']}/reserve", json={
            "student_name": "Gamer One",
            "roll_number": "GM-01",
            "email": "gamer@college.edu",
        }).json()
        res_id = booking["id"]

        # Check full
        avail = self.client.get(f"/events/{ev['id']}/availability").json()
        self.assertEqual(avail["remaining"], 0)

        # Cancel reservation
        del_res = self.client.delete(f"/reservations/{res_id}")
        self.assertEqual(del_res.status_code, 200)
        self.assertIn("successfully cancelled", del_res.json()["message"])

        # Seat restored
        avail_after = self.client.get(f"/events/{ev['id']}/availability").json()
        self.assertEqual(avail_after["remaining"], 1)
        self.assertEqual(avail_after["booked"], 0)

        # Cancelling again returns 404
        self.assertEqual(self.client.delete(f"/reservations/{res_id}").status_code, 404)


if __name__ == "__main__":
    unittest.main()
