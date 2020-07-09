DROP VIEW IF EXISTS award_delta_view;
CREATE VIEW award_delta_view AS
SELECT
  vw_award_search.award_id,
  a.generated_unique_award_id,
    CASE
    WHEN vw_award_search.type IN ('02', '03', '04', '05', '06', '10', '07', '08', '09', '11') AND vw_award_search.fain IS NOT NULL THEN vw_award_search.fain
    WHEN vw_award_search.piid IS NOT NULL THEN vw_award_search.piid  -- contracts. Did it this way to easily handle IDV contracts
    ELSE vw_award_search.uri
  END AS display_award_id,

  vw_award_search.category,
  vw_award_search.type,
  vw_award_search.type_description,
  vw_award_search.piid,
  vw_award_search.fain,
  vw_award_search.uri,
  vw_award_search.total_obligation,
  vw_award_search.description,
  vw_award_search.award_amount,
  vw_award_search.total_subsidy_cost,
  vw_award_search.total_loan_value,
  
  GREATEST(
    a.update_date,
    TREASURY_ACCT.linked_date
  ) as update_date,

  vw_award_search.recipient_name,
  vw_award_search.recipient_unique_id,
  recipient_lookup.recipient_hash,
  vw_award_search.parent_recipient_unique_id,
  vw_award_search.business_categories,

  vw_award_search.action_date,
  vw_award_search.fiscal_year,
  vw_award_search.last_modified_date,
  vw_award_search.period_of_performance_start_date,
  vw_award_search.period_of_performance_current_end_date,
  vw_award_search.date_signed,
  vw_award_search.ordering_period_end_date,

  vw_award_search.original_loan_subsidy_cost,
  vw_award_search.face_value_loan_guarantee,

  vw_award_search.awarding_agency_id,
  vw_award_search.funding_agency_id,
  vw_award_search.awarding_toptier_agency_name,
  vw_award_search.funding_toptier_agency_name,
  vw_award_search.awarding_subtier_agency_name,
  vw_award_search.funding_subtier_agency_name,
  vw_award_search.awarding_toptier_agency_code,
  vw_award_search.funding_toptier_agency_code,
  vw_award_search.awarding_subtier_agency_code,
  vw_award_search.funding_subtier_agency_code,

  vw_award_search.recipient_location_country_code,
  vw_award_search.recipient_location_country_name,
  vw_award_search.recipient_location_state_code,
  vw_award_search.recipient_location_county_code,
  vw_award_search.recipient_location_county_name,
  vw_award_search.recipient_location_congressional_code,
  vw_award_search.recipient_location_zip5,
  vw_award_search.recipient_location_city_name,

  vw_award_search.pop_country_code,
  vw_award_search.pop_country_name,
  vw_award_search.pop_state_code,
  vw_award_search.pop_county_code,
  vw_award_search.pop_county_name,
  vw_award_search.pop_zip5,
  vw_award_search.pop_congressional_code,
  vw_award_search.pop_city_name,
  vw_award_search.pop_city_code,

  vw_award_search.cfda_number,
  vw_award_search.sai_number,
  vw_award_search.type_of_contract_pricing,
  vw_award_search.extent_competed,
  vw_award_search.type_set_aside,

  vw_award_search.product_or_service_code,
  vw_award_search.product_or_service_description,
  vw_award_search.naics_code,
  vw_award_search.naics_description,

  CASE
    WHEN
        vw_award_search.recipient_location_state_code IS NOT NULL
        AND vw_award_search.recipient_location_county_code IS NOT NULL
      THEN CONCAT(
        '{"country_code":"', vw_award_search.recipient_location_country_code,
        '","state_code":"', vw_award_search.recipient_location_state_code,
        '","state_fips":"', RL_STATE_LOOKUP.fips,
        '","county_code":"', vw_award_search.recipient_location_county_code,
        '","county_name":"', vw_award_search.recipient_location_county_name,
        '","population":"', RL_COUNTY_POPULATION.latest_population, '"}'
      )
    ELSE NULL
  END AS recipient_location_county_agg_key,
  CASE
    WHEN
        vw_award_search.recipient_location_state_code IS NOT NULL
        AND vw_award_search.recipient_location_congressional_code IS NOT NULL
      THEN CONCAT(
        '{"country_code":"', vw_award_search.recipient_location_country_code,
        '","state_code":"', vw_award_search.recipient_location_state_code,
        '","state_fips":"', RL_STATE_LOOKUP.fips,
        '","congressional_code":"', vw_award_search.recipient_location_congressional_code,
        '","population":"', RL_DISTRICT_POPULATION.latest_population, '"}'
      )
    ELSE NULL
  END AS recipient_location_congressional_agg_key,
  CASE
    WHEN vw_award_search.recipient_location_state_code IS NOT NULL
      THEN CONCAT(
        '{"country_code":"', vw_award_search.recipient_location_country_code,
        '","state_code":"', vw_award_search.recipient_location_state_code,
        '","state_name":"', RL_STATE_LOOKUP.name,
        '","population":"', RL_STATE_POPULATION.latest_population, '"}'
      )
    ELSE NULL
  END AS recipient_location_state_agg_key,

  TREASURY_ACCT.tas_paths,
  TREASURY_ACCT.tas_components,
  DEFC.disaster_emergency_fund_codes as disaster_emergency_fund_codes,
  DEFC.gross_outlay_amount_by_award_cpe as total_covid_outlay,
  DEFC.transaction_obligated_amount as total_covid_obligation
FROM vw_award_search
INNER JOIN awards a ON (a.id = vw_award_search.award_id)
LEFT JOIN (
  SELECT
    recipient_hash,
    legal_business_name AS recipient_name,
    duns
  FROM
    recipient_lookup AS rlv
) recipient_lookup ON (recipient_lookup.duns = vw_award_search.recipient_unique_id AND vw_award_search.recipient_unique_id IS NOT NULL)
LEFT JOIN (
  SELECT   code, name, fips, MAX(id)
  FROM     state_data
  GROUP BY code, name, fips
) RL_STATE_LOOKUP ON (RL_STATE_LOOKUP.code = vw_award_search.recipient_location_state_code)
LEFT JOIN ref_population_county RL_STATE_POPULATION ON (RL_STATE_POPULATION.state_code = RL_STATE_LOOKUP.fips AND RL_STATE_POPULATION.county_number = '000')
LEFT JOIN ref_population_county RL_COUNTY_POPULATION ON (RL_COUNTY_POPULATION.state_code = RL_STATE_LOOKUP.fips AND RL_COUNTY_POPULATION.county_number = vw_award_search.recipient_location_county_code)
LEFT JOIN ref_population_cong_district RL_DISTRICT_POPULATION ON (RL_DISTRICT_POPULATION.state_code = RL_STATE_LOOKUP.fips AND RL_DISTRICT_POPULATION.congressional_district = vw_award_search.recipient_location_congressional_code)
LEFT JOIN (
    SELECT
        faba.award_id,
        ARRAY_AGG(DISTINCT disaster_emergency_fund_code) AS disaster_emergency_fund_codes,
        COALESCE(sum(CASE WHEN latest_closed_period_per_fy.is_quarter IS NOT NULL THEN faba.gross_outlay_amount_by_award_cpe END), 0) AS gross_outlay_amount_by_award_cpe,
        COALESCE(sum(faba.transaction_obligated_amount), 0) AS transaction_obligated_amount
    FROM
        financial_accounts_by_awards faba
    INNER JOIN disaster_emergency_fund_code defc
        ON defc.code = faba.disaster_emergency_fund_code
        AND defc.group_name = 'covid_19'
    INNER JOIN submission_attributes sa
        ON faba.submission_id = sa.submission_id
        AND sa.reporting_period_start >= '2020-04-01'
    LEFT JOIN (
        SELECT   submission_fiscal_year, is_quarter, max(submission_fiscal_month) AS submission_fiscal_month
        FROM     dabs_submission_window_schedule
        WHERE    submission_reveal_date < now() AND period_start_date >= '2020-04-01'
        GROUP BY submission_fiscal_year, is_quarter
    ) AS latest_closed_period_per_fy
        ON latest_closed_period_per_fy.submission_fiscal_year = sa.reporting_fiscal_year
        AND latest_closed_period_per_fy.submission_fiscal_month = sa.reporting_fiscal_period
        AND latest_closed_period_per_fy.is_quarter = sa.quarter_format_flag
    WHERE faba.award_id IS NOT NULL
GROUP BY
    faba.award_id
HAVING
    COALESCE(sum(CASE WHEN latest_closed_period_per_fy.is_quarter IS NOT NULL THEN faba.gross_outlay_amount_by_award_cpe END), 0) != 0
    OR COALESCE(sum(faba.transaction_obligated_amount), 0) != 0
) DEFC ON (DEFC.award_id = vw_award_search.award_id)
LEFT JOIN (
  SELECT
    faba.award_id,
    MAX(faba.linked_date) as linked_date,
    ARRAY_AGG(
      DISTINCT CONCAT(
        'agency=', agency.toptier_code,
        'faaid=', fa.agency_identifier,
        'famain=', fa.main_account_code,
        'aid=', taa.agency_id,
        'main=', taa.main_account_code,
        'ata=', taa.allocation_transfer_agency_id,
        'sub=', taa.sub_account_code,
        'bpoa=', taa.beginning_period_of_availability,
        'epoa=', taa.ending_period_of_availability,
        'a=', taa.availability_type_code
       )
     ) tas_paths,
     ARRAY_AGG(
      DISTINCT CONCAT(
        'aid=', taa.agency_id,
        'main=', taa.main_account_code,
        'ata=', taa.allocation_transfer_agency_id,
        'sub=', taa.sub_account_code,
        'bpoa=', taa.beginning_period_of_availability,
        'epoa=', taa.ending_period_of_availability,
        'a=', taa.availability_type_code
       )
     ) tas_components
 FROM
   treasury_appropriation_account taa
   INNER JOIN financial_accounts_by_awards faba ON (taa.treasury_account_identifier = faba.treasury_account_id)
   INNER JOIN federal_account fa ON (taa.federal_account_id = fa.id)
   INNER JOIN toptier_agency agency ON (fa.parent_toptier_agency_id = agency.toptier_agency_id)
 WHERE
   faba.award_id IS NOT NULL
 GROUP BY
   faba.award_id
) TREASURY_ACCT ON (TREASURY_ACCT.award_id = vw_award_search.award_id);
