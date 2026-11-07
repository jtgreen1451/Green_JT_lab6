def test_list_artworks_empty(client):
    # Arrange: reset_db auto has empty tables
    
    # Act
    response = client.get("/artworks/")

    # Assert
    assert response.status_code == 200
    assert response.json() == []


def test_get_seeded_artwork(client, seeded_db):
    # Arrange: seeded_db has already loaded the 11 artworks (the Mona Lisa is first)
    expected = {"id": 1, **seeded_db[0]}

    # Act
    response = client.get("/artworks/1")

    # Assert
    assert response.status_code == 200
    assert response.json() == expected


def test_create_artwork(client, sample_artwork):
    # Arrange
    expected = sample_artwork

    # Act
    response = client.post("/artworks/", json=sample_artwork)

    # Assert
    assert response.status_code == 201

    data = response.json()

    assert "id" in data
    assert isinstance(data["id"], int)

    for key, value in expected.items():
        assert data[key] == value


def test_create_artwork_is_saved(client, created_artwork):
    # Arrange
    artwork_id = created_artwork["id"]

    # Act
    response = client.get(f"/artworks/{artwork_id}")

    # Assert
    assert response.status_code == 200
    assert response.json() == created_artwork


def test_update_artwork(client, created_artwork, updated_artwork):
    # Arrange
    artwork_id = created_artwork["id"]

    # Act
    response = client.put(
        f"/artworks/{artwork_id}",
        json=updated_artwork
    )

    # Assert
    assert response.status_code == 200

    updated_data = response.json()

    assert updated_data["id"] == artwork_id

    for key, value in updated_artwork.items():
        assert updated_data[key] == value

    # Act
    get_response = client.get(f"/artworks/{artwork_id}")

    # Assert
    assert get_response.status_code == 200
    assert get_response.json() == updated_data


def test_delete_artwork(client, created_artwork):
    # Arrange
    artwork_id = created_artwork["id"]

    # Act
    response = client.delete(f"/artworks/{artwork_id}")

    # Assert - DELETE response
    assert response.status_code == 204
    assert response.content == b""

    # Act - GET deleted artwork
    get_response = client.get(f"/artworks/{artwork_id}")

    # Assert - artwork no longer exists
    assert get_response.status_code == 404


import pytest


@pytest.mark.parametrize(
    "method, use_body",
    [
        ("get", False),
        ("put", True),
        ("delete", False),
    ],
    ids=["get", "put", "delete"],
)
def test_artwork_not_found(client, sample_artwork, method, use_body):
    kwargs = {"json": sample_artwork} if use_body else {}
    response = client.request(method, "/artworks/9999", **kwargs)
    assert response.status_code == 404
    assert response.json() == {"detail": "Artwork not found"}


def test_non_integer_id(client):
    # Arrange
    url = "/artworks/mona-lisa"

    # Act
    response = client.get(url)

    # Assert
    assert response.status_code == 422


def test_create_duplicate(client, created_artwork, sample_artwork):
    # Arrange
    # created_artwork creates the original artwork

    # Act
    response = client.post("/artworks/", json=sample_artwork)

    # Assert
    assert response.status_code == 409
    assert response.json() == {
        "detail": "An artwork with that title and artist already exists"
    }


def test_create_duplicate_ignores_case(client, created_artwork, sample_artwork):
    # Arrange
    duplicate_artwork = sample_artwork.copy()
    duplicate_artwork["title"] = duplicate_artwork["title"].upper()
    duplicate_artwork["artist"] = duplicate_artwork["artist"].lower()

    # Act
    response = client.post("/artworks/", json=duplicate_artwork)

    # Assert
    assert response.status_code == 409
    assert response.json() == {
        "detail": "An artwork with that title and artist already exists"
    }


def test_update_into_duplicate(client, seeded_db):
    # Arrange
    artwork_id = 2

    duplicate_artwork = {
        "title": "Mona Lisa",
        "artist": "Leonardo da Vinci",
        "year": 1503,
        "medium": "Oil on poplar panel",
        "museum": "Louvre",
        "image_url": "https://example.com/mona-lisa.jpg",
    }

    # Act - attempt to update Lady with an Ermine
    response = client.put(
        f"/artworks/{artwork_id}",
        json=duplicate_artwork
    )

    # Assert - duplicate update is rejected
    assert response.status_code == 409

    # Act - retrieve artwork 2 again
    get_response = client.get(f"/artworks/{artwork_id}")

    # Assert - original artwork was not changed
    assert get_response.status_code == 200
    data = get_response.json()
    assert data["title"] == "Lady with an Ermine"


def test_update_same_title_and_artist_is_allowed(
    client, created_artwork, sample_artwork
):
    # Arrange
    artwork_id = created_artwork["id"]

    updated_data = sample_artwork.copy()
    updated_data["museum"] = "Louvre"

    # Act
    response = client.put(
        f"/artworks/{artwork_id}",
        json=updated_data
    )

    # Assert - update succeeds
    assert response.status_code == 200

    data = response.json()
    assert data["id"] == artwork_id
    assert data["title"] == sample_artwork["title"]
    assert data["artist"] == sample_artwork["artist"]
    assert data["museum"] == "Louvre"


@pytest.mark.parametrize(
    "missing_field",
    ["title", "artist", "year", "medium", "museum", "image_url"]
)
def test_create_missing_field(client, sample_artwork, missing_field):
    # Arrange
    artwork_data = sample_artwork.copy()
    del artwork_data[missing_field]

    # Act
    response = client.post("/artworks/", json=artwork_data)

    # Assert
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", missing_field]


@pytest.mark.parametrize(
    "field, invalid_value",
    [
        ("year", 3000),
        ("year", "nineteen-oh-seven"),
        ("title", ""),
    ]
)
def test_create_invalid_value(client, sample_artwork, field, invalid_value):
    # Arrange
    artwork_data = sample_artwork.copy()
    artwork_data[field] = invalid_value

    # Act
    response = client.post("/artworks/", json=artwork_data)

    # Assert
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", field]


@pytest.mark.parametrize(
    "skip, limit, expected_count",
    [
        (0, 3, 3),
        (0, 1, 1),
        (3, 3, 3),
        (999, 3, 0),
        (0, 0, 0),
    ]
)
def test_pagination_counts(client, seeded_db, skip, limit, expected_count):
    # Arrange
    params = {"skip": skip, "limit": limit}

    # Act
    response = client.get("/artworks/", params=params)

    # Assert
    assert response.status_code == 200
    assert len(response.json()) == expected_count


@pytest.mark.parametrize(
    "params",
    [
        {"skip": -1},
        {"limit": -1},
        {"limit": 101},
    ]
)
def test_pagination_invalid(client, params):
    # Arrange
    # params contains an invalid query parameter

    # Act
    response = client.get("/artworks/", params=params)

    # Assert
    assert response.status_code == 422


@pytest.mark.parametrize(
    "artist",
    [
        "Claude Monet",
        "monet",
        "da vinci",
        "Artist That Does Not Exist",
    ]
)
def test_filter_by_artist(client, seeded_db, artist):
    # Arrange
    expected_titles = [
        artwork["title"]
        for artwork in seeded_db
        if artist.lower() in artwork["artist"].lower()
    ]

    # Act
    response = client.get("/artworks/", params={"artist": artist})

    # Assert
    assert response.status_code == 200

    actual_titles = [artwork["title"] for artwork in response.json()]
    assert actual_titles == expected_titles


