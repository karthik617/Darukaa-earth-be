def test_register_login_refresh_logout_flow(client):

    r = client.post(
        "/auth/register",
        json={"email": "karthik@test.com", "password": "Password123!"},
    )
    assert r.status_code == 201

    r = client.post(
        "/auth/login",
        data={"username": "karthik@test.com", "password": "Password123!"},
    )
    assert r.status_code == 200

    login_data = r.json()
    assert "access_token" in login_data

    assert "refresh_token" in client.cookies
    old_refresh = client.cookies.get("refresh_token")

    r = client.post("/auth/refresh")
    assert r.status_code == 200

    refreshed = r.json()
    assert "access_token" in refreshed

    assert "refresh_token" in client.cookies
    new_refresh = client.cookies.get("refresh_token")
    assert new_refresh != old_refresh

    client.cookies.set("refresh_token", old_refresh)
    r = client.post("/auth/refresh")
    assert r.status_code == 401

    client.cookies.set("refresh_token", new_refresh)
    r = client.post("/auth/logout")
    assert r.status_code == 204

    r = client.post("/auth/refresh")
    assert r.status_code == 401
