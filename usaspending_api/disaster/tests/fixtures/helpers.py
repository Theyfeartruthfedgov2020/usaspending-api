import datetime
import json
import pytest
import usaspending_api.common.helpers.fiscal_year_helpers


class Helpers:
    @staticmethod
    def post_for_spending_endpoint(client, url, **kwargs):
        request_body = {}
        filters = {}
        pagination = {}

        if kwargs.get("def_codes"):
            filters["def_codes"] = kwargs["def_codes"]
        if kwargs.get("query"):
            filters["query"] = kwargs["query"]

        request_body["filter"] = filters

        if kwargs.get("page"):
            pagination["page"] = kwargs["page"]
        if kwargs.get("limit"):
            pagination["limit"] = kwargs["limit"]
        if kwargs.get("order"):
            pagination["order"] = kwargs["order"]
        if kwargs.get("sort"):
            pagination["sort"] = kwargs["sort"]

        request_body["pagination"] = pagination

        if kwargs.get("spending_type"):
            request_body["spending_type"] = kwargs["spending_type"]

        resp = client.post(url, content_type="application/json", data=json.dumps(request_body))
        return resp

    @staticmethod
    def post_for_count_endpoint(client, url, def_codes=None, award_type_codes=None):
        if award_type_codes:
            request_body = json.dumps({"filter": {"def_codes": def_codes, "award_type_codes": award_type_codes}})
        elif def_codes:
            request_body = json.dumps({"filter": {"def_codes": def_codes}})
        else:
            request_body = json.dumps({"filter": {}})
        resp = client.post(url, content_type="application/json", data=request_body)
        return resp

    @staticmethod
    def post_for_amount_endpoint(client, url, def_codes, award_type_codes):
        filters = {}
        if def_codes:
            filters["def_codes"] = def_codes
        if award_type_codes:
            filters["award_type_codes"] = award_type_codes
        resp = client.post(url, content_type="application/json", data=json.dumps({"filter": filters}))
        return resp

    @staticmethod
    def patch_datetime_now(monkeypatch, year, month, day):
        patched_datetime = datetime.datetime(year, month, day, tzinfo=datetime.timezone.utc)

        class PatchedDatetime(datetime.datetime):
            @classmethod
            def now(cls, *args):
                return patched_datetime

        monkeypatch.setattr("usaspending_api.submissions.helpers.datetime", PatchedDatetime)
        monkeypatch.setattr("usaspending_api.disaster.v2.views.disaster_base.datetime", PatchedDatetime)
        usaspending_api.common.helpers.fiscal_year_helpers.current_fiscal_year = lambda: year


@pytest.fixture
def helpers():
    return Helpers
