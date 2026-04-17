import os
import time
from fastapi.testclient import TestClient
from main import app


def run() -> None:
    with TestClient(app) as client:
        admin_email = os.getenv("admin_email", "admin@example.com")
        admin_password = os.getenv("admin_password", "admin123")

        # Admin endpoint with admin credentials (should pass).
        admin_ok = client.post(
            "/api/v1/users/login/admin",
            json={"email": admin_email, "password": admin_password},
        )
        print("login_admin_with_admin:", admin_ok.status_code)

        # Admin endpoint with customer credentials (should fail 403).
        cust_email = f"cust_role_{int(time.time())}@example.com"
        client.post(
            "/api/v1/users",
            json={
                "full_name": "Role Customer",
                "email": cust_email,
                "password": "Customer@123",
                "role": "customer",
            },
        )
        admin_bad = client.post(
            "/api/v1/users/login/admin",
            json={"email": cust_email, "password": "Customer@123"},
        )
        print("login_admin_with_customer:", admin_bad.status_code, admin_bad.json())

        # Employee endpoint with support_agent credentials (should pass).
        emp_email = f"agent_role_{int(time.time())}@example.com"
        client.post(
            "/api/v1/users",
            json={
                "full_name": "Support Agent",
                "email": emp_email,
                "password": "Agent@1234",
                "role": "support_agent",
            },
        )
        employee_ok = client.post(
            "/api/v1/users/login/employee",
            json={"email": emp_email, "password": "Agent@1234"},
        )
        print("login_employee_with_agent:", employee_ok.status_code)

        # Employee endpoint with admin credentials (should fail 403).
        employee_bad = client.post(
            "/api/v1/users/login/employee",
            json={"email": admin_email, "password": admin_password},
        )
        print("login_employee_with_admin:", employee_bad.status_code, employee_bad.json())


if __name__ == "__main__":
    run()
