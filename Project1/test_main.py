import unittest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, create_engine, Session
from sqlmodel.pool import StaticPool

from main import app
from database import get_session

# Setup in-memory SQLite database engine for unit tests
test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

def override_get_session():
    with Session(test_engine) as session:
        yield session

app.dependency_overrides[get_session] = override_get_session

class TestLostAndFoundAPI(unittest.TestCase):
    def setUp(self):
        SQLModel.metadata.create_all(test_engine)
        self.client = TestClient(app)

    def tearDown(self):
        SQLModel.metadata.drop_all(test_engine)

    def test_create_item_success(self):
        response = self.client.post(
            "/items",
            json={
                "title": "Blue Water Bottle",
                "description": "Stainless steel Milton 1L bottle",
                "category": "Accessories",
                "location": "Library 2nd Floor",
                "reported_by": "Sachin",
                "status": "Lost",
            },
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["title"], "Blue Water Bottle")
        self.assertEqual(data["status"], "Lost")
        self.assertIn("id", data)

    def test_create_item_validation_empty_title(self):
        response = self.client.post(
            "/items",
            json={
                "title": "   ",
                "description": "Stainless steel bottle",
                "category": "Accessories",
                "location": "Library",
                "reported_by": "Sachin",
                "status": "Lost",
            },
        )
        self.assertEqual(response.status_code, 422)

    def test_create_item_validation_short_description(self):
        response = self.client.post(
            "/items",
            json={
                "title": "Water Bottle",
                "description": "ab",
                "category": "Accessories",
                "location": "Library",
                "reported_by": "Sachin",
                "status": "Lost",
            },
        )
        self.assertEqual(response.status_code, 422)

    def test_create_item_validation_invalid_status(self):
        response = self.client.post(
            "/items",
            json={
                "title": "Blue Water Bottle",
                "description": "Stainless steel bottle",
                "category": "Accessories",
                "location": "Library",
                "reported_by": "Sachin",
                "status": "Stolen",
            },
        )
        self.assertEqual(response.status_code, 422)

    def test_get_all_items(self):
        self.client.post(
            "/items",
            json={
                "title": "Laptop Charger",
                "description": "Dell Type-C 65W charger",
                "category": "Electronics",
                "location": "Lab 3",
                "reported_by": "Alice",
                "status": "Found",
            },
        )
        response = self.client.get("/items")
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.json()), 1)

    def test_get_item_by_id(self):
        create_res = self.client.post(
            "/items",
            json={
                "title": "ID Card",
                "description": "Student ID card for CS Department",
                "category": "Documents",
                "location": "Cafeteria",
                "reported_by": "Bob",
                "status": "Lost",
            },
        )
        item_id = create_res.json()["id"]

        response = self.client.get(f"/items/{item_id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["title"], "ID Card")

    def test_get_item_by_id_not_found(self):
        response = self.client.get("/items/99999")
        self.assertEqual(response.status_code, 404)
        self.assertIn("does not exist", response.json()["detail"])

    def test_update_item(self):
        create_res = self.client.post(
            "/items",
            json={
                "title": "Headphones",
                "description": "Black Sony wireless headphones",
                "category": "Electronics",
                "location": "Sports Complex",
                "reported_by": "Charlie",
                "status": "Lost",
            },
        )
        item_id = create_res.json()["id"]

        update_res = self.client.put(
            f"/items/{item_id}",
            json={"status": "Returned", "location": "Main Office (Handed over)"},
        )
        self.assertEqual(update_res.status_code, 200)
        self.assertEqual(update_res.json()["status"], "Returned")
        self.assertEqual(update_res.json()["location"], "Main Office (Handed over)")

    def test_update_item_not_found(self):
        response = self.client.put("/items/99999", json={"status": "Returned"})
        self.assertEqual(response.status_code, 404)

    def test_delete_item(self):
        create_res = self.client.post(
            "/items",
            json={
                "title": "Umbrella",
                "description": "Foldable red umbrella",
                "category": "Accessories",
                "location": "Auditorium",
                "reported_by": "Dave",
                "status": "Found",
            },
        )
        item_id = create_res.json()["id"]

        del_res = self.client.delete(f"/items/{item_id}")
        self.assertEqual(del_res.status_code, 200)

        get_res = self.client.get(f"/items/{item_id}")
        self.assertEqual(get_res.status_code, 404)

    def test_delete_item_not_found(self):
        response = self.client.delete("/items/99999")
        self.assertEqual(response.status_code, 404)

    def test_filter_by_status(self):
        self.client.post(
            "/items",
            json={
                "title": "Keys",
                "description": "Set of 3 keys with blue keychain",
                "category": "Accessories",
                "location": "Grounds",
                "reported_by": "Eve",
                "status": "Lost",
            },
        )
        self.client.post(
            "/items",
            json={
                "title": "Scientific Calculator",
                "description": "Casio fx-991EX calculator",
                "category": "Electronics",
                "location": "Room 101",
                "reported_by": "Frank",
                "status": "Found",
            },
        )

        res_lost = self.client.get("/items/status/Lost")
        self.assertEqual(res_lost.status_code, 200)
        items = res_lost.json()
        self.assertGreaterEqual(len(items), 1)
        self.assertTrue(all(item["status"] == "Lost" for item in items))

    def test_filter_by_status_invalid(self):
        res = self.client.get("/items/status/UnknownStatus")
        self.assertEqual(res.status_code, 400)

    def test_filter_by_category(self):
        self.client.post(
            "/items",
            json={
                "title": "USB Flash Drive",
                "description": "SanDisk 64GB USB drive",
                "category": "Electronics",
                "location": "Computer Lab 1",
                "reported_by": "Grace",
                "status": "Found",
            },
        )
        res_cat = self.client.get("/items/category/Electronics")
        self.assertEqual(res_cat.status_code, 200)
        items = res_cat.json()
        self.assertGreaterEqual(len(items), 1)
        self.assertTrue(all(item["category"].lower() == "electronics" for item in items))

if __name__ == "__main__":
    unittest.main()
