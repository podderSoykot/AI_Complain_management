import os
import time
from fastapi.testclient import TestClient
from main import app


def run() -> None:
    with TestClient(app) as client:
        admin_email = os.getenv("admin_email", "admin@example.com")
        admin_password = os.getenv("admin_password", "admin123")
        login = client.post("/api/v1/users/login/admin", json={"email": admin_email, "password": admin_password})
        token = login.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        print("admin_login:", login.status_code)

        emp_email = f"unique_agent_{int(time.time())}@example.com"
        emp_create = client.post(
            "/api/v1/users",
            json={
                "full_name": "Unique Agent",
                "email": emp_email,
                "password": "Agent@1234",
                "role": "support_agent",
            },
        )
        emp_id = emp_create.json().get("id")
        print("create_employee:", emp_create.status_code, emp_create.json())

        # Update employee role and status from admin endpoints.
        role_upd = client.patch(f"/api/v1/admin/users/{emp_id}/role", json={"role": "supervisor"}, headers=headers)
        print("update_role:", role_upd.status_code, role_upd.json())
        status_upd = client.patch(f"/api/v1/admin/users/{emp_id}/status", json={"is_active": 1}, headers=headers)
        print("update_status:", status_upd.status_code, status_upd.json())

        cust_email = f"unique_customer_{int(time.time())}@example.com"
        client.post(
            "/api/v1/users",
            json={
                "full_name": "Unique Customer",
                "email": cust_email,
                "password": "Customer@123",
                "role": "customer",
            },
        )
        cust_login = client.post("/api/v1/users/login", json={"email": cust_email, "password": "Customer@123"})
        cust_token = cust_login.json().get("access_token")
        cust_headers = {"Authorization": f"Bearer {cust_token}"} if cust_token else {}
        ticket_resp = client.post(
            "/api/v1/tickets",
            json={
                "title": "Need unique smart assignment",
                "description": "Admin should use smart assignment to select least loaded employee.",
            },
            headers=cust_headers,
        )
        ticket_id = ticket_resp.json().get("id")
        print("create_ticket:", ticket_resp.status_code, ticket_resp.json())

        smart = client.post(f"/api/v1/admin/tickets/{ticket_id}/smart-assign", headers=headers)
        print("smart_assign:", smart.status_code, smart.json())

        insights = client.get("/api/v1/admin/insights/workload", headers=headers)
        print("workload_insights:", insights.status_code, insights.json())


if __name__ == "__main__":
    run()
