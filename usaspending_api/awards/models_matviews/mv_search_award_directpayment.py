from usaspending_api.awards.models_matviews.base_mv_model import BaseSearchAwardModel


class MatviewSearchAwardDirectPayment(BaseSearchAwardModel):
    class Meta:
        managed = False
        db_table = "mv_search_award_directpayment"
