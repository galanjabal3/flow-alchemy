def test_list_workflows_empty(client, auth_headers):
    response = client.get("/api/workflows/", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == []


def test_create_workflow(client, auth_headers):
    workflow_data = {
        "name": "Test Workflow",
        "description": "A test workflow",
        "definition": {"nodes": [], "edges": []},
    }
    response = client.post("/api/workflows/", json=workflow_data, headers=auth_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Workflow"
    assert data["definition"] == {"nodes": [], "edges": []}


def test_get_workflow(client, auth_headers):
    workflow_data = {"name": "Get Test", "definition": {"nodes": []}}
    create_resp = client.post("/api/workflows/", json=workflow_data, headers=auth_headers)
    workflow_id = create_resp.json()["id"]

    response = client.get(f"/api/workflows/{workflow_id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["name"] == "Get Test"


def test_get_workflow_not_found(client, auth_headers):
    response = client.get("/api/workflows/99999", headers=auth_headers)
    assert response.status_code == 404


def test_update_workflow(client, auth_headers):
    workflow_data = {"name": "Original", "definition": {"nodes": []}}
    create_resp = client.post("/api/workflows/", json=workflow_data, headers=auth_headers)
    workflow_id = create_resp.json()["id"]

    update_data = {"name": "Updated"}
    response = client.put(f"/api/workflows/{workflow_id}", json=update_data, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["name"] == "Updated"


def test_delete_workflow(client, auth_headers):
    workflow_data = {"name": "To Delete", "definition": {"nodes": []}}
    create_resp = client.post("/api/workflows/", json=workflow_data, headers=auth_headers)
    workflow_id = create_resp.json()["id"]

    response = client.delete(f"/api/workflows/{workflow_id}", headers=auth_headers)
    assert response.status_code == 204

    get_resp = client.get(f"/api/workflows/{workflow_id}", headers=auth_headers)
    assert get_resp.status_code == 404


def test_unauthorized_access(client):
    response = client.get("/api/workflows/")
    assert response.status_code == 403
