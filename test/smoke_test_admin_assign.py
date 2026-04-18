import os
import time
from fastapi.testclient import TestClient
from main import app


def run() -> None:
    with TestClient(app) as client:
        admin_email = os.getenv("admin_email", "admin@example.com")
        admin_password = os.getenv("admin_password", "admin123")

        admin_login = client.post("/api/v1/users/login/admin", json={"email": admin_email, "password": admin_password})
        print("admin_login:", admin_login.status_code)
        admin_token = admin_login.json().get("access_token")
        admin_headers = {"Authorization": f"Bearer {admin_token}"} if admin_token else {}

        # Create support agent user
        agent_email = f"agent_assign_{int(time.time())}@example.com"
        agent_resp = client.post(
            "/api/v1/users",
            json={
                "full_name": "Assign Agent",
                "email": agent_email,
                "password": "Agent@1234",
                "role": "support_agent",
                "department": "Support",
            },
        )
        print("create_agent:", agent_resp.status_code, agent_resp.json())
        agent_id = agent_resp.json().get("id")

        # Create customer and ticket
        customer_email = f"customer_assign_{int(time.time())}@example.com"
        customer_resp = client.post(
            "/api/v1/users",
            json={
                "full_name": "Assign Customer",
                "email": customer_email,
                "password": "Customer@123",
                "role": "customer",
            },
        )
        print("create_customer:", customer_resp.status_code)
        customer_login = client.post(
            "/api/v1/users/login",
            json={"email": customer_email, "password": "Customer@123"},
        )
        customer_token = customer_login.json().get("access_token")
        customer_headers = {"Authorization": f"Bearer {customer_token}"} if customer_token else {}
        ticket_resp = client.post(
            "/api/v1/tickets",
            data={
                "title": "Need manual assignment",
                "description": "Please assign this ticket to a support agent for faster handling.",
            },
            headers=customer_headers,
        )
        print("create_ticket:", ticket_resp.status_code, ticket_resp.json())
        ticket_id = ticket_resp.json().get("id")

        # Admin assigns ticket to agent
        assign_resp = client.post(
            f"/api/v1/admin/tickets/{ticket_id}/assign",
            json={"assignee_user_id": agent_id},
            headers=admin_headers,
        )
        print("assign_ticket:", assign_resp.status_code, assign_resp.json())


if __name__ == "__main__":
    run()
