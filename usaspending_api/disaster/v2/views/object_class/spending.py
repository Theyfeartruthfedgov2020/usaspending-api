from typing import List

from django.db.models import Q, Sum, F, Value, Case, When, Min, TextField, IntegerField
from django.db.models.functions import Coalesce, Cast
from rest_framework.response import Response

from usaspending_api.common.cache_decorator import cache_response
from usaspending_api.common.data_classes import Pagination
from usaspending_api.common.helpers.generic_helper import get_pagination_metadata
from usaspending_api.disaster.v2.views.elasticsearch_account_base import ElasticsearchAccountDisasterBase
from usaspending_api.disaster.v2.views.object_class.object_class_result import (
    ObjectClassResults,
    MajorClass,
    ObjectClass,
)
from usaspending_api.disaster.v2.views.disaster_base import (
    PaginationMixin,
    SpendingMixin,
    FabaOutlayMixin,
)
from usaspending_api.financial_activities.models import FinancialAccountsByProgramActivityObjectClass


def construct_response(results: list, pagination: Pagination, strip_total_budgetary_resources=True):
    object_classes = ObjectClassResults()
    for row in results:
        major_code = row.pop("major_code")
        major_class = MajorClass(
            id=major_code, code=major_code, award_count=0, description=row.pop("major_description")
        )
        object_classes[major_class].include(ObjectClass(**row))

    return {
        "results": object_classes.finalize(pagination, strip_total_budgetary_resources),
        "page_metadata": get_pagination_metadata(len(object_classes), pagination.limit, pagination.page),
    }


class ObjectClassSpendingViewSet(SpendingMixin, FabaOutlayMixin, PaginationMixin, ElasticsearchAccountDisasterBase):
    """View to implement the API"""

    endpoint_doc = "usaspending_api/api_contracts/contracts/v2/disaster/object_class/spending.md"

    # Defined for the Elasticsearch implementation of Spending by Award
    agg_key = "financial_accounts_by_award.object_class"  # primary (tier-1) aggregation key
    nested_nonzero_fields = {"outlay": "gross_outlay_amount_by_award_cpe", "obligation": "transaction_obligated_amount"}
    nonzero_fields = {"outlay": "total_covid_outlay", "obligation": "total_covid_obligation"}
    query_fields = [
        "major_object_class_name",
        "major_object_class_name.contains",
        "object_class_name",
        "object_class_name.contains",
    ]
    top_hits_fields = [
        "financial_accounts_by_award.object_class_id",
        "financial_accounts_by_award.major_object_class_name",
        "financial_accounts_by_award.object_class_name",
        "financial_accounts_by_award.major_object_class",
    ]

    @cache_response()
    def post(self, request):
        if self.spending_type == "award":
            return self.perform_elasticsearch_search()
        else:
            results = list(self.total_queryset)
            extra_columns = []
            response = construct_response(results, self.pagination)
            response["totals"] = self.accumulate_total_values(results, extra_columns)

        return Response(response)

    @property
    def total_queryset(self):
        filters = [
            self.is_in_provided_def_codes,
            self.is_non_zero_total_spending,
            self.all_closed_defc_submissions,
            Q(object_class__isnull=False),
        ]

        object_class_annotations = {
            "major_code": F("object_class__major_object_class"),
            "description": F("object_class__object_class_name"),
            "code": F("object_class__object_class"),
            "id": Cast(Min("object_class_id"), TextField()),
            "major_description": F("object_class__major_object_class_name"),
        }

        annotations = {
            **object_class_annotations,
            "obligation": Coalesce(
                Sum(
                    Case(
                        When(
                            self.final_period_submission_query_filters,
                            then=F("obligations_incurred_by_program_object_class_cpe"),
                        ),
                        default=Value(0),
                    )
                ),
                0,
            ),
            "outlay": Coalesce(
                Sum(
                    Case(
                        When(
                            self.final_period_submission_query_filters,
                            then=F("gross_outlay_amount_by_program_object_class_cpe"),
                        ),
                        default=Value(0),
                    )
                ),
                0,
            ),
            "award_count": Value(None, output_field=IntegerField()),
        }

        # Assuming it is more performant to fetch all rows once rather than
        #  run a count query and fetch only a page's worth of results
        return (
            FinancialAccountsByProgramActivityObjectClass.objects.filter(*filters)
            .values("object_class__major_object_class", "object_class__major_object_class_name",)
            .annotate(**annotations)
            .values(*annotations.keys())
        )

    def build_elasticsearch_result(self, info_buckets: List[dict]) -> List[dict]:
        temp_results = {}
        child_results = []
        for bucket in info_buckets:
            child = self._build_child_json_result(bucket)
            child_results.append(child)
        for child in child_results:
            result = self._build_json_result(child)
            child.pop("parent_data")
            if result["code"] in temp_results.keys():
                temp_results[result["code"]] = {
                    "id": int(result["id"]),
                    "code": result["code"],
                    "description": result["description"],
                    "award_count": temp_results[result["code"]]["award_count"] + result["award_count"],
                    # the count of distinct awards contributing to the totals
                    "obligation": temp_results[result["code"]]["obligation"] + result["obligation"],
                    "outlay": temp_results[result["code"]]["outlay"] + result["outlay"],
                    "children": temp_results[result["code"]]["children"] + result["children"],
                }
            else:
                temp_results[result["code"]] = result
        results = [x for x in temp_results.values()]
        return results

    def _build_json_result(self, child):
        return {
            "id": child["parent_data"][1],
            "code": child["parent_data"][1],
            "description": child["parent_data"][0],
            "award_count": child["award_count"],
            # the count of distinct awards contributing to the totals
            "obligation": child["obligation"],
            "outlay": child["outlay"],
            "children": [child],
        }

    def _build_child_json_result(self, bucket: dict):
        return {
            "id": bucket["dim_metadata"]["hits"]["hits"][0]["_source"]["object_class_id"],
            "code": bucket["key"],
            "description": bucket["dim_metadata"]["hits"]["hits"][0]["_source"]["object_class_name"],
            # the count of distinct awards contributing to the totals
            "award_count": int(bucket["count_awards_by_dim"]["award_count"]["value"]),
            **{
                key: round(float(bucket.get(f"sum_{val}", {"value": 0})["value"]), 2)
                for key, val in self.nested_nonzero_fields.items()
            },
            "parent_data": [
                bucket["dim_metadata"]["hits"]["hits"][0]["_source"]["major_object_class_name"],
                bucket["dim_metadata"]["hits"]["hits"][0]["_source"]["major_object_class"],
            ],
        }
