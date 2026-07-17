TRUNCATE TABLE dim_wallet_status_mapping;

INSERT INTO dim_wallet_status_mapping VALUES

-- Provider A
('Wallet_A', 'Captured',  'Success'),
('Wallet_A', 'Pending',   'Pending'),
('Wallet_A', 'Declined',  'Rejected'),

-- Provider B
('Wallet_B', 'COMPLETED', 'Success'),
('Wallet_B', 'PROCESSING','Pending'),
('Wallet_B', 'FAILED',    'Rejected'),

-- Provider C
('Wallet_C', 'approved',  'Success'),
('Wallet_C', 'waiting',   'Pending'),
('Wallet_C', 'declined',  'Rejected'),

-- Provider D
('Wallet_D', 'paid',      'Success'),
('Wallet_D', 'new',       'Pending'),
('Wallet_D', 'canceled',  'Rejected'),

-- Provider E
('Wallet_E', 'PROCESSED', 'Success'),
('Wallet_E', 'PENDING',   'Pending'),
('Wallet_E', 'TIMEOUT',   'Rejected'),

-- Provider F
('Wallet_F', 'Payment successful', 'Success'),
('Wallet_F', 'Payment pending',     'Pending'),
('Wallet_F', 'Payment failed',      'Rejected'),

-- Provider G
('Wallet_G', 'Исполнена', 'Success'),
('Wallet_G', 'Ожидает',   'Pending'),
('Wallet_G', 'Отклонена', 'Rejected'),

-- Missing or malformed source statuses
('Wallet_H', NULL,        'Rejected'),
('Wallet_H', '',          'Rejected'),
('Wallet_H', '-',         'Rejected');