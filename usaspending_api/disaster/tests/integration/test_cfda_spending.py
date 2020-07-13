import pytest
from rest_framework import status

from usaspending_api.search.tests.data.utilities import setup_elasticsearch_test

url = "/api/v2/disaster/cfda/spending/"


@pytest.mark.django_db
def test_correct_response_defc_no_results(
    client, monkeypatch, helpers, elasticsearch_award_index, awards_and_transactions
):
    setup_elasticsearch_test(monkeypatch, elasticsearch_award_index)

    resp = helpers.post_for_spending_endpoint(client, url, def_codes=["N"])
    expected_results = []
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["results"] == expected_results


@pytest.mark.django_db
def test_correct_response_single_defc(
    client, monkeypatch, helpers, elasticsearch_award_index, cfda_awards_and_transactions
):
    setup_elasticsearch_test(monkeypatch, elasticsearch_award_index)

    resp = helpers.post_for_spending_endpoint(client, url, def_codes=["L"])
    expected_results = [
        {"code": "30.300", "count": 1, "description": "CFDA 3", "id": 300, "obligation": 2000.0, "outlay": 1000.0},
        {"code": "20.200", "count": 1, "description": "CFDA 2", "id": 200, "obligation": 20.0, "outlay": 0.0},
        {"code": "10.100", "count": 1, "description": "CFDA 1", "id": 100, "obligation": 2.0, "outlay": 0.0},
    ]
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["results"] == expected_results


@pytest.mark.django_db
def test_correct_response_multiple_defc(
    client, monkeypatch, helpers, elasticsearch_award_index, cfda_awards_and_transactions
):
    setup_elasticsearch_test(monkeypatch, elasticsearch_award_index)

    resp = helpers.post_for_spending_endpoint(client, url, def_codes=["L", "M"])
    expected_results = [
        {"code": "30.300", "count": 1, "description": "CFDA 3", "id": 300, "obligation": 2000.0, "outlay": 1000.0},
        {"code": "20.200", "count": 2, "description": "CFDA 2", "id": 200, "obligation": 220.0, "outlay": 100.0},
        {"code": "10.100", "count": 1, "description": "CFDA 1", "id": 100, "obligation": 2.0, "outlay": 0.0},
    ]

    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["results"] == expected_results


@pytest.mark.django_db
def test_correct_response_with_query(
    client, monkeypatch, helpers, elasticsearch_award_index, cfda_awards_and_transactions
):
    setup_elasticsearch_test(monkeypatch, elasticsearch_award_index)

    resp = helpers.post_for_spending_endpoint(client, url, def_codes=["L", "M"], query="GIBBERISH")
    expected_results = []
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["results"] == expected_results

    resp = helpers.post_for_spending_endpoint(client, url, def_codes=["L", "M"], query="3")
    expected_results = [
        {"code": "30.300", "count": 1, "description": "CFDA 3", "id": 300, "obligation": 2000.0, "outlay": 1000.0}
    ]
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["results"] == expected_results


@pytest.mark.django_db
def test_correct_response_with_award_type_codes(
    client, monkeypatch, helpers, elasticsearch_award_index, cfda_awards_and_transactions
):
    setup_elasticsearch_test(monkeypatch, elasticsearch_award_index)

    resp = helpers.post_for_spending_endpoint(client, url, def_codes=["L", "M"], award_type_codes=["IDV_A"])
    expected_results = []
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["results"] == expected_results

    resp = helpers.post_for_spending_endpoint(client, url, def_codes=["L", "M"], award_type_codes=["07", "A", "B"])
    expected_results = [
        {"code": "20.200", "count": 1, "description": "CFDA 2", "id": 200, "obligation": 20.0, "outlay": 0.0},
        {"code": "10.100", "count": 1, "description": "CFDA 1", "id": 100, "obligation": 2.0, "outlay": 0.0},
    ]
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["results"] == expected_results


@pytest.mark.django_db
def test_invalid_defc(client, monkeypatch, helpers, elasticsearch_award_index, cfda_awards_and_transactions):
    setup_elasticsearch_test(monkeypatch, elasticsearch_award_index)

    resp = helpers.post_for_spending_endpoint(client, url, def_codes=["ZZ"])
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert resp.data["detail"] == "Field 'filter|def_codes' is outside valid values ['L', 'M', 'N']"


@pytest.mark.django_db
def test_invalid_defc_type(client, monkeypatch, helpers, elasticsearch_award_index, cfda_awards_and_transactions):
    setup_elasticsearch_test(monkeypatch, elasticsearch_award_index)

    resp = helpers.post_for_spending_endpoint(client, url, def_codes="100")
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert resp.data["detail"] == "Invalid value in 'filter|def_codes'. '100' is not a valid type (array)"


@pytest.mark.django_db
def test_missing_defc(client, monkeypatch, helpers, elasticsearch_award_index, cfda_awards_and_transactions):
    setup_elasticsearch_test(monkeypatch, elasticsearch_award_index)

    resp = helpers.post_for_spending_endpoint(client, url)
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert resp.data["detail"] == "Missing value: 'filter|def_codes' is a required field"


@pytest.mark.django_db
def test_pagination_page_and_limit(
    client, monkeypatch, helpers, elasticsearch_award_index, cfda_awards_and_transactions
):
    setup_elasticsearch_test(monkeypatch, elasticsearch_award_index)

    resp = helpers.post_for_spending_endpoint(client, url, def_codes=["L", "M"], page=2, limit=1)
    expected_results = {
        "results": [
            {"code": "20.200", "count": 2, "description": "CFDA 2", "id": 200, "obligation": 220.0, "outlay": 100.0}
        ],
        "page_metadata": {
            "hasNext": True,
            "hasPrevious": True,
            "limit": 1,
            "next": 3,
            "page": 2,
            "previous": 1,
            "total": 3,
        },
    }

    assert resp.status_code == status.HTTP_200_OK
    assert resp.json() == expected_results
