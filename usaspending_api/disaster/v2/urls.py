from django.conf.urls import url

from usaspending_api.disaster.v2.views.award.count import AwardCountViewSet
from usaspending_api.disaster.v2.views.agency.count import AgencyCountViewSet
from usaspending_api.disaster.v2.views.award.amount import AmountViewSet
from usaspending_api.disaster.v2.views.def_code.count import DefCodeCountViewSet
from usaspending_api.disaster.v2.views.federal_account.count import FederalAccountCountViewSet
from usaspending_api.disaster.v2.views.federal_account.loans import LoansViewSet
from usaspending_api.disaster.v2.views.federal_account.spending import SpendingViewSet
from usaspending_api.disaster.v2.views.object_class.count import ObjectClassCountViewSet
from usaspending_api.disaster.v2.views.overview import OverviewViewSet
from usaspending_api.disaster.v2.views.recipient.count import RecipientCountViewSet
from usaspending_api.disaster.v2.views.spending import ExperimentalDisasterViewSet
from usaspending_api.disaster.v2.views.spending_by_geography import SpendingByGeographyViewSet

urlpatterns = [
    url(r"^agency/count/$", AgencyCountViewSet.as_view()),
    url(r"^award/amount/$", AmountViewSet.as_view()),
    url(r"^award/count/$", AwardCountViewSet.as_view()),
    url(r"^def_code/count/$", DefCodeCountViewSet.as_view()),
    url(r"^federal_account/count/$", FederalAccountCountViewSet.as_view()),
    url(r"^federal_account/loans/$", LoansViewSet.as_view()),
    url(r"^federal_account/spending/$", SpendingViewSet.as_view()),
    url(r"^object_class/count/$", ObjectClassCountViewSet.as_view()),
    url(r"^overview/$", OverviewViewSet.as_view()),
    url(r"^recipient/count/$", RecipientCountViewSet.as_view()),
    url(r"^spending/$", ExperimentalDisasterViewSet.as_view()),
    url(r"^spending_by_geography/$", SpendingByGeographyViewSet.as_view()),
]
