import logging
import copy
import pytest

from django.core.management import call_command
from django.db import connections
from django.db.models import Q
from django.test import TestCase
from model_mommy import mommy

from usaspending_api.awards.models import FinancialAccountsByAwards
from usaspending_api.etl.transaction_loaders.data_load_helpers import format_insert_or_update_column_sql


@pytest.mark.usefixtures("broker_db_setup", "db")
class LoadSubmissionIntegrationTests(TestCase):
    logger = logging.getLogger(__name__)
    multi_db = True

    @classmethod
    def setUpClass(cls):
        # Setup default data in USAspending Test DB
        mommy.make(
            "accounts.TreasuryAppropriationAccount",
            treasury_account_identifier=-99999,
            allocation_transfer_agency_id="999",
            agency_id="999",
            beginning_period_of_availability="1700-01-01",
            ending_period_of_availability="1700-12-31",
            availability_type_code="000",
            main_account_code="0000",
            sub_account_code="0000",
            tas_rendering_label="1004-1002-1003-1007-1008",
        )
        mommy.make(
            "references.ObjectClass", id=0, major_object_class="00", object_class="000", direct_reimbursable=None
        )

        # Setup default data in Broker Test DB
        broker_objects_to_insert = {
            "tas_lookup": {"broker_object": _assemble_broker_tas_lookup_records(), "conflict_column": "tas_id"},
            "submission": {"broker_object": _assemble_broker_submission_records(), "conflict_column": "submission_id"},
            "certified_award_financial": {
                "broker_object": _assemble_certified_award_financial_records(),
                "conflict_column": "certified_award_financial_id",
            },
        }
        connection = connections["data_broker"]
        with connection.cursor() as cursor:
            for broker_table_name, value in broker_objects_to_insert.items():
                broker_object = value["broker_object"]
                conflict_column = value["conflict_column"]
                for load_object in [dict(**{broker_table_name: _}) for _ in broker_object]:
                    columns, values, pairs = format_insert_or_update_column_sql(cursor, load_object, broker_table_name)
                    insert_sql = (
                        f"INSERT INTO {broker_table_name} {columns} VALUES {values}"
                        f" ON CONFLICT ({conflict_column}) DO UPDATE SET {pairs};"
                    )
                    cursor.execute(insert_sql)

    @classmethod
    def tearDownClass(cls):
        pass

    def test_load_submission_transaction_obligated_amount(self):
        """ Test load submission management command for File C transaction_obligated_amount NaNs """
        call_command("load_submission", "-9999")

        expected_results = 0
        actual_results = FinancialAccountsByAwards.objects.filter(
            Q(transaction_obligated_amount="NaN") | Q(transaction_obligated_amount=None)
        ).count()

        assert expected_results == actual_results

    def test_load_submission_file_c_fain_and_uri(self):
        """
        Test load submission management command for File C records with FAIN and URI
        """
        mommy.make(
            "awards.Award",
            id=-999,
            uri="RANDOM_LOAD_SUB_URI_999",
            fain="RANDOM_LOAD_SUB_FAIN_999",
            latest_transaction_id=-999,
        )
        mommy.make(
            "awards.Award",
            id=-1999,
            uri="RANDOM_LOAD_SUB_URI_1999",
            fain="RANDOM_LOAD_SUB_FAIN_1999",
            latest_transaction_id=-1999,
        )
        mommy.make("awards.TransactionNormalized", id=-999)
        mommy.make("awards.TransactionNormalized", id=-1999)

        call_command("load_submission", "-9999")

        expected_results = {"award_ids": [-1999, -999]}
        actual_results = {
            "award_ids": sorted(
                list(
                    FinancialAccountsByAwards.objects.filter(award_id__isnull=False).values_list("award_id", flat=True)
                )
            )
        }

        assert expected_results == actual_results

    def test_load_submission_file_c_uri(self):
        """
        Test load submission management command for File C records with only a URI
        """
        mommy.make("awards.Award", id=-997, uri="RANDOM_LOAD_SUB_URI", latest_transaction_id=-997)
        mommy.make("awards.TransactionNormalized", id=-997)

        call_command("load_submission", "-9999")

        expected_results = {"award_ids": [-997]}
        actual_results = {
            "award_ids": list(
                FinancialAccountsByAwards.objects.filter(award_id__isnull=False).values_list("award_id", flat=True)
            )
        }

        assert expected_results == actual_results

    def test_load_submission_file_c_fain(self):
        """
        Test load submission management command for File C records with only a FAIN
        """
        mommy.make("awards.Award", id=-997, fain="RANDOM_LOAD_SUB_FAIN", latest_transaction_id=-997)
        mommy.make("awards.TransactionNormalized", id=-997)

        call_command("load_submission", "-9999")

        expected_results = {"award_ids": [-997]}
        actual_results = {
            "award_ids": list(
                FinancialAccountsByAwards.objects.filter(award_id__isnull=False).values_list("award_id", flat=True)
            )
        }

        assert expected_results == actual_results

    def test_load_submission_file_c_piid_with_parent_piid(self):
        """
        Test load submission management command for File C records with only a piid and parent piid
        """
        mommy.make(
            "awards.Award",
            id=-997,
            piid="RANDOM_LOAD_SUB_PIID",
            parent_award_piid="RANDOM_LOAD_SUB_PARENT_PIID",
            latest_transaction_id=-997,
        )
        mommy.make("awards.TransactionNormalized", id=-997)

        call_command("load_submission", "-9999")

        expected_results = {"award_ids": [-997, -997]}
        actual_results = {
            "award_ids": list(
                FinancialAccountsByAwards.objects.filter(award_id__isnull=False).values_list("award_id", flat=True)
            )
        }

        assert expected_results == actual_results

    def test_load_submission_file_c_piid_with_no_parent_piid(self):
        """
        Test load submission management command for File C records with only a piid and no parent piid
        """
        mommy.make(
            "awards.Award", id=-998, piid="RANDOM_LOAD_SUB_PIID", parent_award_piid=None, latest_transaction_id=-998
        )
        mommy.make("awards.TransactionNormalized", id=-998)

        call_command("load_submission", "-9999")

        expected_results = {"award_ids": [-998]}
        actual_results = {
            "award_ids": list(
                FinancialAccountsByAwards.objects.filter(award_id__isnull=False).values_list("award_id", flat=True)
            )
        }

        assert expected_results == actual_results

    def test_load_submission_file_c_piid_with_unmatched_parent_piid(self):
        """
        Test load submission management command for File C records that are not expected to be linked to Award data
        """
        mommy.make(
            "awards.Award",
            id=-1001,
            piid="RANDOM_LOAD_SUB_PIID",
            parent_award_piid="PARENT_LOAD_SUB_PIID_DNE",
            latest_transaction_id=-1234,
        )
        mommy.make("awards.TransactionNormalized", id=-1234)

        call_command("load_submission", "-9999")

        expected_results = {"award_ids": [-1001]}
        actual_results = {
            "award_ids": list(
                FinancialAccountsByAwards.objects.filter(award_id__isnull=False).values_list("award_id", flat=True)
            )
        }

        assert expected_results == actual_results

    def test_load_submission_file_c_no_d_linkage(self):
        """
        Test load submission management command for File C records that are not expected to be linked to Award data
        """
        mommy.make(
            "awards.Award",
            id=-999,
            piid="RANDOM_LOAD_SUB_PIID_DNE",
            parent_award_piid="PARENT_LOAD_SUB_PIID_DNE",
            latest_transaction_id=-999,
        )
        mommy.make("awards.TransactionNormalized", id=-999, award_id=-999)

        call_command("load_submission", "-9999")

        expected_results = {"award_ids": []}
        actual_results = {
            "award_ids": list(
                FinancialAccountsByAwards.objects.filter(award_id__isnull=False).values_list("award_id", flat=True)
            )
        }

        assert expected_results == actual_results

    def test_load_submission_file_c_zero_and_null_transaction_obligated_amount_ignored(self):
        """
        Test that the 'certified_award_financial` rows that have a 'transaction_obligated_amou'
        of zero or null are not loaded from Broker.
        """
        call_command("load_submission", "-9999")

        assert FinancialAccountsByAwards.objects.all().count() == 6


def _assemble_broker_tas_lookup_records() -> list:
    base_record = {
        "created_at": None,
        "updated_at": None,
        "tas_id": None,
        "allocation_transfer_agency": None,
        "agency_identifier": None,
        "beginning_period_of_availa": None,
        "ending_period_of_availabil": None,
        "availability_type_code": None,
        "main_account_code": None,
        "sub_account_code": None,
        "account_num": None,
        "internal_end_date": None,
        "internal_start_date": "2015-01-01",
        "financial_indicator2": None,
        "fr_entity_description": None,
        "fr_entity_type": None,
        "account_title": None,
        "budget_bureau_code": None,
        "budget_bureau_name": None,
        "budget_function_code": None,
        "budget_function_title": None,
        "budget_subfunction_code": None,
        "budget_subfunction_title": None,
        "reporting_agency_aid": None,
        "reporting_agency_name": None,
    }

    default_tas_lookup_record = copy.copy(base_record)
    default_tas_lookup_record["tas_id"] = -999
    default_tas_lookup_record["account_num"] = -99999
    default_tas_lookup_record["allocation_transfer_agency"] = 1001
    default_tas_lookup_record["agency_identifier"] = 1002
    default_tas_lookup_record["availability_type_code"] = 1003
    default_tas_lookup_record["allocation_transfer_agency"] = 1004
    default_tas_lookup_record["beginning_period_of_availa"] = 1005
    default_tas_lookup_record["ending_period_of_availabil"] = 1006
    default_tas_lookup_record["main_account_code"] = 1007
    default_tas_lookup_record["sub_account_code"] = 1008

    return [default_tas_lookup_record]


def _assemble_broker_submission_records() -> list:
    base_record = {
        "created_at": None,
        "updated_at": None,
        "submission_id": None,
        "user_id": None,
        "cgac_code": None,
        "reporting_start_date": None,
        "reporting_end_date": None,
        "is_quarter_format": False,
        "number_of_errors": 0,
        "number_of_warnings": 0,
        "publish_status_id": None,
        "publishable": False,
        "reporting_fiscal_period": 0,
        "reporting_fiscal_year": 0,
        "d2_submission": False,
        "certifying_user_id": None,
        "frec_code": None,
    }

    default_submission_record = copy.copy(base_record)
    default_submission_record["submission_id"] = -9999

    return [default_submission_record]


def _assemble_certified_award_financial_records() -> list:
    base_record = {
        "created_at": None,
        "updated_at": None,
        "certified_award_financial_id": None,
        "submission_id": -9999,
        "job_id": None,
        "row_number": None,
        "agency_identifier": None,
        "allocation_transfer_agency": None,
        "availability_type_code": None,
        "beginning_period_of_availa": None,
        "by_direct_reimbursable_fun": None,
        "deobligations_recov_by_awa_cpe": None,
        "ending_period_of_availabil": None,
        "fain": None,
        "gross_outlay_amount_by_awa_cpe": None,
        "gross_outlay_amount_by_awa_fyb": None,
        "gross_outlays_delivered_or_cpe": None,
        "gross_outlays_delivered_or_fyb": None,
        "gross_outlays_undelivered_cpe": None,
        "gross_outlays_undelivered_fyb": None,
        "main_account_code": None,
        "object_class": "000",
        "obligations_delivered_orde_cpe": None,
        "obligations_delivered_orde_fyb": None,
        "obligations_incurred_byawa_cpe": None,
        "obligations_undelivered_or_cpe": None,
        "obligations_undelivered_or_fyb": None,
        "parent_award_id": None,
        "piid": None,
        "program_activity_code": None,
        "program_activity_name": None,
        "sub_account_code": None,
        "transaction_obligated_amou": 100,
        "uri": None,
        "ussgl480100_undelivered_or_cpe": None,
        "ussgl480100_undelivered_or_fyb": None,
        "ussgl480200_undelivered_or_cpe": None,
        "ussgl480200_undelivered_or_fyb": None,
        "ussgl483100_undelivered_or_cpe": None,
        "ussgl483200_undelivered_or_cpe": None,
        "ussgl487100_downward_adjus_cpe": None,
        "ussgl487200_downward_adjus_cpe": None,
        "ussgl488100_upward_adjustm_cpe": None,
        "ussgl488200_upward_adjustm_cpe": None,
        "ussgl490100_delivered_orde_cpe": None,
        "ussgl490100_delivered_orde_fyb": None,
        "ussgl490200_delivered_orde_cpe": None,
        "ussgl490800_authority_outl_cpe": None,
        "ussgl490800_authority_outl_fyb": None,
        "ussgl493100_delivered_orde_cpe": None,
        "ussgl497100_downward_adjus_cpe": None,
        "ussgl497200_downward_adjus_cpe": None,
        "ussgl498100_upward_adjustm_cpe": None,
        "ussgl498200_upward_adjustm_cpe": None,
        "tas": None,
        "tas_id": -99999,
    }

    row_with_piid_and_no_parent_piid = copy.copy(base_record)
    row_with_piid_and_no_parent_piid["certified_award_financial_id"] = 1
    row_with_piid_and_no_parent_piid["piid"] = "RANDOM_LOAD_SUB_PIID"

    row_with_piid_and_parent_piid = copy.copy(base_record)
    row_with_piid_and_parent_piid["certified_award_financial_id"] = 2
    row_with_piid_and_parent_piid["piid"] = "RANDOM_LOAD_SUB_PIID"
    row_with_piid_and_parent_piid["parent_award_id"] = "RANDOM_LOAD_SUB_PARENT_PIID"

    row_with_fain = copy.copy(base_record)
    row_with_fain["certified_award_financial_id"] = 3
    row_with_fain["fain"] = "RANDOM_LOAD_SUB_FAIN"

    row_with_uri = copy.copy(base_record)
    row_with_uri["certified_award_financial_id"] = 4
    row_with_uri["uri"] = "RANDOM_LOAD_SUB_URI"

    row_with_fain_and_uri_dne = copy.copy(base_record)
    row_with_fain_and_uri_dne["certified_award_financial_id"] = 5
    row_with_fain_and_uri_dne["fain"] = "RANDOM_LOAD_SUB_FAIN_999"
    row_with_fain_and_uri_dne["uri"] = "RANDOM_LOAD_SUB_URI_DNE"

    row_with_uri_and_fain_dne = copy.copy(base_record)
    row_with_uri_and_fain_dne["certified_award_financial_id"] = 6
    row_with_uri_and_fain_dne["fain"] = "RANDOM_LOAD_SUB_FAIN_DNE"
    row_with_uri_and_fain_dne["uri"] = "RANDOM_LOAD_SUB_URI_1999"

    row_with_zero_transaction_obligated_amount = copy.copy(base_record)
    row_with_zero_transaction_obligated_amount["certified_award_financial_id"] = 7
    row_with_zero_transaction_obligated_amount["transaction_obligated_amou"] = 0

    row_with_null_transaction_obligated_amount = copy.copy(base_record)
    row_with_null_transaction_obligated_amount["certified_award_financial_id"] = 8
    row_with_null_transaction_obligated_amount["transaction_obligated_amou"] = None

    return [
        row_with_piid_and_no_parent_piid,
        row_with_piid_and_parent_piid,
        row_with_fain,
        row_with_uri,
        row_with_fain_and_uri_dne,
        row_with_uri_and_fain_dne,
        row_with_zero_transaction_obligated_amount,
        row_with_null_transaction_obligated_amount,
    ]
