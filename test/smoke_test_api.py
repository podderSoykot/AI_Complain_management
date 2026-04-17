from fastapi.testclient import TestClient
from main import app
import time


def run() -> None:
    with TestClient(app) as client:
        unique_email = f"rahim{int(time.time())}@example.com"

        health = client.get("/api/v1/health")
        print("health:", health.status_code, health.json())

        user_payload = {
            "full_name": "Rahim Ahmed",
            "email": unique_email,
            "password": "Rahim@1234",
            "role": "customer",
        }
        user_resp = client.post("/api/v1/users", json=user_payload)
        print("create_user:", user_resp.status_code, user_resp.json())
        tenant_id = user_resp.json().get("tenant_id", "example_com")

        list_resp = client.get("/api/v1/users", params={"tenant_id": tenant_id, "limit": 10})
        print("list_users:", list_resp.status_code, list_resp.json())

        ticket_payload = {
            "title": "Payment deducted but service not activated",
            "description": "I paid today and money was deducted but my account is not active yet. This is urgent.",
        }
        no_auth_ticket = client.post("/api/v1/tickets", json=ticket_payload)
        print("create_ticket_without_login:", no_auth_ticket.status_code, no_auth_ticket.json())

        login_payload = {"email": unique_email, "password": "Rahim@1234"}
        login_resp = client.post("/api/v1/users/login", json=login_payload)
        print("login:", login_resp.status_code, login_resp.json())

        token = login_resp.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        ticket_resp = client.post("/api/v1/tickets", json=ticket_payload, headers=headers)
        print("create_ticket_with_login:", ticket_resp.status_code, ticket_resp.json())


if __name__ == "__main__":
    run()
