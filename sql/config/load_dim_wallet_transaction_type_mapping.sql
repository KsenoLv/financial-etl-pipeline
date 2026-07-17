TRUNCATE TABLE dim_wallet_transaction_type_mapping;

INSERT INTO dim_wallet_transaction_type_mapping VALUES

-- Provider A
('Wallet_A', 'Purchase',       'Deposit'),
('Wallet_A', 'Payout',         'Withdrawal'),
('Wallet_A', 'Refund',         'Refund'),

-- Provider B
('Wallet_B', 'PAYMENT',        'Deposit'),
('Wallet_B', 'WITHDRAWAL',     'Withdrawal'),
('Wallet_B', 'CHARGEBACK',     'Chargeback'),

-- Provider C
('Wallet_C', 'deposit',        'Deposit'),
('Wallet_C', 'withdrawal',     'Withdrawal'),
('Wallet_C', 'processing',     'Pending'),

-- Provider D
('Wallet_D', 'Receive Money',  'Deposit'),
('Wallet_D', 'Send Money',     'Withdrawal'),
('Wallet_D', 'Exchange',       'Pending'),

-- Provider E
('Wallet_E', 'credit',         'Deposit'),
('Wallet_E', 'debit',          'Withdrawal'),
('Wallet_E', 'fee',            'Withdrawal'),

-- Provider F
('Wallet_F', 'sale',           'Deposit'),
('Wallet_F', 'refund',         'Refund'),
('Wallet_F', 'chargeback',     'Chargeback'),

-- Provider G
('Wallet_G', 'IN',             'Deposit'),
('Wallet_G', 'OUT',            'Withdrawal'),
('Wallet_G', NULL,             'Unknown'),

-- Provider H
('Wallet_H', 'INTERNAL_TRANSFER', 'Pending'),
('Wallet_H', 'EXTERNAL_TRANSFER', 'Pending'),
('Wallet_H', 'TRANSACTION_FEE',   'Pending'),

-- Provider I
('Wallet_I', 'Final_credit',      'Deposit'),
('Wallet_I', 'Final_withdrawal',  'Withdrawal'),
('Wallet_I', 'Exchange_from',     'Unknown'),
('Wallet_I', 'Exchange_to',       'Deposit'),

-- Unrecognized or unsupported references
('Wallet_J', 'fx',             'Unknown'),
('Wallet_J', '',               'Unknown'),
('Wallet_J', NULL,             'Unknown');