CREATE TABLE customers (
    id bigint PRIMARY KEY,
    first_name text NOT NULL,
    last_name text NOT NULL,
    email text NOT NULL,
    phone text
);

CREATE TABLE bank_accounts (
    id bigint PRIMARY KEY,
    customer_id bigint NOT NULL REFERENCES customers(id),
    account_number text NOT NULL,
    account_type text NOT NULL,
    bank_name text NOT NULL,
    currency text NOT NULL,
    balance numeric(12, 2) NOT NULL,
    status text NOT NULL
);

CREATE TABLE transactions (
    id bigint PRIMARY KEY,
    account_id bigint NOT NULL REFERENCES bank_accounts(id),
    transaction_type text NOT NULL,
    amount numeric(12, 2) NOT NULL,
    currency text NOT NULL,
    merchant text NOT NULL,
    category text NOT NULL,
    status text NOT NULL,
    posted_at timestamp NOT NULL
);
