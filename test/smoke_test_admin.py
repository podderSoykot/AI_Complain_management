import os
import time
from fastapi.testclient import TestClient
from main import app


def run() -> None:
    with TestClient(app) as client:
        # Ensure app is up.
        health = client.get("/api/v1/health")
        print("health:", health.status_code)

        admin_email = os.getenv("admin_email", "admin@example.com")
        admin_password = os.getenv("admin_password", "admin123")

        # Login with seeded admin from .env
        login = client.post("/api/v1/users/login", json={"email": admin_email, "password": admin_password})
        print("admin_login:", login.status_code, login.json())
        token = login.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"} if token else {}

        # Admin endpoints
        users_resp = client.get("/api/v1/admin/users", headers=headers)
        print("admin_users:", users_resp.status_code)
        tickets_resp = client.get("/api/v1/admin/tickets", headers=headers)
        print("admin_tickets:", tickets_resp.status_code)
        stats_resp = client.get("/api/v1/admin/stats", headers=headers)
        print("admin_stats:", stats_resp.status_code, stats_resp.json())

        # Non-admin token should be forbidden on admin endpoints.
        customer_email = f"cust{int(time.time())}@example.com"
        create_customer = client.post(
            "/api/v1/users",
            json={
                "full_name": "Customer Demo",
                "email": customer_email,
                "password": "Customer@123",
                "role": "customer",
            },
        )
        print("create_customer:", create_customer.status_code)

        customer_login = client.post(
            "/api/v1/users/login",
            json={"email": customer_email, "password": "Customer@123"},
        )
        print("customer_login:", customer_login.status_code)
        ctoken = customer_login.json().get("access_token")
        cheaders = {"Authorization": f"Bearer {ctoken}"} if ctoken else {}
        forbidden = client.get("/api/v1/admin/stats", headers=cheaders)
        print("admin_stats_with_customer:", forbidden.status_code, forbidden.json())


if __name__ == "__main__":
    run()
