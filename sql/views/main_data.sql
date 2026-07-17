CREATE OR ALTER VIEW dbo.main_data
AS

SELECT
    /* ---------------------------------------------------------
       Company normalization
       --------------------------------------------------------- */
    CASE
        WHEN r.wallet_bank IN (
            'Wallet_A',
            'Wallet_B',
            'Wallet_C',
            'Wallet_D'
        )
        AND LOWER(mb.merchant) IN (
            'merchant_a',
            'merchant_b'
        )
            THEN 'Company_A'

        WHEN r.wallet_bank IN (
            'Wallet_A',
            'Wallet_B',
            'Wallet_C',
            'Wallet_D'
        )
            THEN 'Company_B'

        ELSE r.company
    END AS company,

    r.wallet_bank,

    /* ---------------------------------------------------------
       Effective transaction date
       --------------------------------------------------------- */
    CASE
        WHEN nr.norm_reference = 'Deposit'
            THEN COALESCE(
                r.depositdate,
                r.transaction_date
            )

        WHEN nr.norm_reference = 'Withdrawal'
            THEN COALESCE(
                r.withdrawaldate,
                r.transaction_date
            )

        ELSE r.transaction_date
    END AS transaction_date,

    r.depositdate,
    r.withdrawaldate,
    r.pay_id,

    r.status,
    sm.normalized_status AS norm_status,

    r.amount,
    r.currency,

    /* ---------------------------------------------------------
       Commission calculation

       Priority:
       1. Wallet-specific commission
       2. Commission supplied by the provider
       3. Commission calculated from an MDR rate
       --------------------------------------------------------- */
    CASE
        WHEN r.wallet_bank = 'Wallet_Commission_Special'
            THEN wc.wallet_commission

        WHEN NULLIF(r.commission, 0) IS NOT NULL
            THEN r.commission

        WHEN cr.mdr IS NOT NULL
            THEN
                r.amount
                * TRY_CONVERT(
                    DECIMAL(18, 8),
                    cr.mdr
                )

        ELSE NULL
    END AS commission,

    /* Rate used when commission was calculated */
    CASE
        WHEN NULLIF(r.commission, 0) IS NULL
         AND cr.mdr IS NOT NULL
            THEN TRY_CONVERT(
                DECIMAL(18, 8),
                cr.mdr
            )

        ELSE NULL
    END AS commission_rate_used,

    r.currency AS commissioncurrency,

    /* ---------------------------------------------------------
       Effective historical exchange rate
       --------------------------------------------------------- */
    COALESCE(
        fx.effective_exchange_rate,
        1
    ) AS exchangerate,

    /* ---------------------------------------------------------
       Signed amount in original currency

       Deposits are positive.
       Withdrawals are negative.
       --------------------------------------------------------- */
    CASE
        WHEN nr.norm_reference = 'Deposit'
            THEN ABS(r.amount)

        WHEN nr.norm_reference = 'Withdrawal'
            THEN -ABS(r.amount)

        ELSE r.amount
    END AS originalamount,

    /* ---------------------------------------------------------
       Amount converted into the reporting currency
       --------------------------------------------------------- */
    CASE
        WHEN nr.norm_reference = 'Deposit'
            THEN ABS(
                r.amount
                / NULLIF(
                    COALESCE(
                        fx.effective_exchange_rate,
                        1
                    ),
                    0
                )
            )

        WHEN nr.norm_reference = 'Withdrawal'
            THEN -ABS(
                r.amount
                / NULLIF(
                    COALESCE(
                        fx.effective_exchange_rate,
                        1
                    ),
                    0
                )
            )

        ELSE
            r.amount
            / NULLIF(
                COALESCE(
                    fx.effective_exchange_rate,
                    1
                ),
                0
            )
    END AS finalamount,

    r.project,
    mb.merchant AS norm_project,

    r.notes,
    r.reference,
    nr.norm_reference,
    r.paymentmethod,

    /* Data lineage fields */
    r.path,
    r.ingection_id,
    r.ingection_time,
    r.raw_hash

FROM dbo.raw_data_normalized_v2 AS r

/* -------------------------------------------------------------
   Status normalization
   ------------------------------------------------------------- */
LEFT JOIN dbo.dim_wallet_status_mapping AS sm
    ON r.wallet_bank = sm.wallet_bank
   AND r.status = sm.source_status

/* -------------------------------------------------------------
   Transaction direction mapping
   ------------------------------------------------------------- */
LEFT JOIN dbo.dim_wallet_transaction_type_mapping AS tm
    ON r.wallet_bank = tm.wallet_bank
   AND r.reference = tm.source_reference

/* -------------------------------------------------------------
   Deposit / Withdrawal normalization

   Most wallets use the mapping table.
   Certain providers require additional parsing rules.
   ------------------------------------------------------------- */
CROSS APPLY
(
    SELECT
        CASE
            /* Provider with a fixed transaction direction */
            WHEN r.wallet_bank = 'Wallet_Fixed_Withdrawal'
                THEN 'Withdrawal'

            /* Provider where direction is parsed from text */
            WHEN r.wallet_bank = 'Wallet_Text_Direction'
                THEN
                    CASE
                        WHEN LOWER(
                            COALESCE(r.project, '')
                        ) LIKE '%incoming%'
                            THEN 'Deposit'

                        WHEN LOWER(
                            COALESCE(r.project, '')
                        ) LIKE '%outgoing%'
                            THEN 'Withdrawal'

                        ELSE NULL
                    END

            /* Standard mapping */
            ELSE tm.transaction_type
        END AS norm_reference
) AS nr

/* -------------------------------------------------------------
   Merchant and transaction metadata enrichment
   ------------------------------------------------------------- */
LEFT JOIN
(
    SELECT DISTINCT
        transaction_id,
        transaction_type,
        merchant,
        country_group,
        requested_currency,
        source_exchange_rate,
        processed_currency,
        processed_exchange_rate

    FROM dbo.vw_transaction_metadata
) AS mb
    ON r.pay_id = mb.transaction_id
   AND nr.norm_reference =
        CASE
            WHEN UPPER(
                LTRIM(RTRIM(mb.transaction_type))
            ) = 'DEPOSIT'
                THEN 'Deposit'

            WHEN UPPER(
                LTRIM(RTRIM(mb.transaction_type))
            ) IN (
                'WITHDRAWAL',
                'WITHDRAW',
                'PAYOUT'
            )
                THEN 'Withdrawal'

            ELSE mb.transaction_type
        END

/* -------------------------------------------------------------
   Find the most recent available exchange rate on or before the
   effective transaction date.
   ------------------------------------------------------------- */
OUTER APPLY
(
    SELECT TOP 1
        er.rate_date,
        er.currency,
        er.rate,
        er.rate_time

    FROM dbo.vw_daily_exchange_rates AS er

    WHERE UPPER(
              LTRIM(RTRIM(er.currency))
          )
          =
          UPPER(
              LTRIM(RTRIM(r.currency))
          )

      AND er.rate_date <=
          CAST(
              CASE
                  WHEN nr.norm_reference = 'Deposit'
                      THEN COALESCE(
                          r.depositdate,
                          r.transaction_date
                      )

                  WHEN nr.norm_reference = 'Withdrawal'
                      THEN COALESCE(
                          r.withdrawaldate,
                          r.transaction_date
                      )

                  ELSE r.transaction_date
              END
              AS DATE
          )

    ORDER BY
        er.rate_date DESC,
        er.rate_time DESC
) AS dr

/* -------------------------------------------------------------
   Commission rule enrichment
   ------------------------------------------------------------- */
LEFT JOIN dbo.vw_commission_rules AS cr
    ON r.pay_id = cr.transaction_id
   AND r.wallet_bank = cr.wallet_bank

   /* Some providers allow cross-currency matching */
   AND
   (
        r.wallet_bank = 'Wallet_Cross_Currency'
        OR
        UPPER(
            LTRIM(RTRIM(r.currency))
        )
        =
        UPPER(
            LTRIM(RTRIM(cr.requested_currency))
        )
   )

   AND cr.transaction_direction =
        CASE
            WHEN nr.norm_reference = 'Deposit'
                THEN 'Payin'

            WHEN nr.norm_reference = 'Withdrawal'
                THEN 'Payout'

            ELSE NULL
        END

/* -------------------------------------------------------------
   Base currency does not require conversion.
   Other currencies use the selected historical rate.
   ------------------------------------------------------------- */
CROSS APPLY
(
    SELECT
        CASE
            WHEN UPPER(
                LTRIM(RTRIM(r.currency))
            ) = 'BASE_CURRENCY'
                THEN CONVERT(
                    DECIMAL(18, 8),
                    1
                )

            ELSE dr.rate
        END AS effective_exchange_rate
) AS fx

/* -------------------------------------------------------------
   Wallet-specific commission aggregation

   Some providers store the transaction and its commission as
   separate rows linked by the same payment identifier.
   ------------------------------------------------------------- */
OUTER APPLY
(
    SELECT
        SUM(x.amount) AS wallet_commission

    FROM dbo.raw_data_normalized_v2 AS x

    WHERE x.wallet_bank = 'Wallet_Commission_Special'
      AND x.pay_id = r.pay_id
      AND x.notes = 'COMMISSION_ROW'
) AS wc

/* -------------------------------------------------------------
   Reporting filters

   Certain providers are included without metadata matching.
   Standard providers require a matching transaction identifier.
   ------------------------------------------------------------- */
WHERE
(
    r.wallet_bank IN (
        'Wallet_Standalone_A',
        'Wallet_Standalone_B'
    )
    OR mb.transaction_id IS NOT NULL
)
AND
(
    r.wallet_bank <> 'Wallet_Commission_Special'
    OR r.notes = 'TRANSACTION_ROW'
);