from django.conf.urls import url

from usaspending_api.references.v2.views import (
    agency,
    toptier_agencies,
    data_dictionary,
    glossary,
    award_types,
    def_codes,
    submission_periods,
)
from usaspending_api.references.v2.views.filter_tree import naics, tas, psc

urlpatterns = [
    url(r"^agency/(?P<pk>[0-9]+)/$", agency.AgencyViewSet.as_view()),
    url(r"^award_types/$", award_types.AwardTypeGroups.as_view()),
    url(r"^data_dictionary/$", data_dictionary.DataDictionaryViewSet.as_view()),
    url(r"^def_codes/$", def_codes.DEFCodesViewSet.as_view()),
    url(r"^filter_tree/psc/$", psc.PSCViewSet.as_view()),
    url(r"^filter_tree/psc/(?P<tier1>(\w| )*)/$", psc.PSCViewSet.as_view()),
    url(r"^filter_tree/psc/(?P<tier1>(\w| )*)/(?P<tier2>\w*)/$", psc.PSCViewSet.as_view()),
    url(r"^filter_tree/psc/(?P<tier1>(\w| )*)/(?P<tier2>\w*)/(?P<tier3>\w*)/$", psc.PSCViewSet.as_view()),
    url(r"^filter_tree/tas/$", tas.TASViewSet.as_view()),
    url(r"^filter_tree/tas/(?P<tier1>\w*)/$", tas.TASViewSet.as_view()),
    url(r"^filter_tree/tas/(?P<tier1>\w*)/(?P<tier2>(\w|-)*)/$", tas.TASViewSet.as_view()),
    url(r"^filter_tree/tas/(?P<tier1>\w*)/(?P<tier2>(\w|-)*)/(?P<tier3>.*)/$", tas.TASViewSet.as_view()),
    url(r"^glossary/$", glossary.GlossaryViewSet.as_view()),
    url(r"^naics/$", naics.NAICSViewSet.as_view()),
    url(r"^naics/(?P<requested_naics>[0-9]+)/$", naics.NAICSViewSet.as_view()),
    url(r"^submission_periods/", submission_periods.SubmissionPeriodsViewSet.as_view()),
    url(r"^toptier_agencies/$", toptier_agencies.ToptierAgenciesViewSet.as_view()),
]
