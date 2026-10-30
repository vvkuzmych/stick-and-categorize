import uuid
from concurrent.futures import ThreadPoolExecutor


def new_id() -> str:
    return str(uuid.uuid4())


def test_empty_lists(client):
    assert client.get("/notes").json() == []
    assert client.get("/categories").json() == []


def test_create_note_without_category(client):
    note_id = new_id()
    r = client.post("/notes", json={"id": note_id, "text": "Buy milk"})
    assert r.status_code == 201
    assert r.json()["id"] == note_id
    assert r.json()["category"] is None
    assert client.get("/notes").json()[0]["text"] == "Buy milk"


def test_duplicate_note_id_returns_existing_note(client):
    note_id = new_id()
    first = client.post("/notes", json={"id": note_id, "text": "Buy milk"})
    second = client.post("/notes", json={"id": note_id, "text": "something else"})
    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json() == first.json()
    assert len(client.get("/notes").json()) == 1


def test_category_names_match_ignoring_case_and_spaces(client):
    for name in ["Work", "work", "  WORK ", "wo rk"]:
        client.post("/notes", json={"id": new_id(), "text": "x", "category": name})
    assert client.get("/categories").json() == ["wo rk", "Work"]  # sorted by normalized name
    notes = client.get("/notes").json()
    assert [n["category"] for n in notes] == ["Work", "Work", "Work", "wo rk"]


def test_blank_category_means_none(client):
    r = client.post("/notes", json={"id": new_id(), "text": "x", "category": "   "})
    assert r.status_code == 201
    assert r.json()["category"] is None
    assert client.get("/categories").json() == []


def test_blank_text_is_rejected(client):
    assert client.post("/notes", json={"id": new_id(), "text": "  "}).status_code == 422


def test_invalid_id_is_rejected(client):
    assert client.post("/notes", json={"id": "nope", "text": "x"}).status_code == 422


def test_two_parallel_category_creations_make_one_category(client):
    def post(_):
        return client.post("/notes", json={"id": new_id(), "text": "x", "category": "Work"})

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(post, range(8)))
    assert all(r.status_code == 201 for r in results)
    assert client.get("/categories").json() == ["Work"]
    assert len(client.get("/notes").json()) == 8


def test_parallel_posts_of_same_note_id_make_one_note(client):
    note_id = new_id()

    def post(_):
        return client.post("/notes", json={"id": note_id, "text": "x", "category": "Work"})

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(post, range(8)))
    assert all(r.status_code in (200, 201) for r in results)
    assert len(client.get("/notes").json()) == 1
