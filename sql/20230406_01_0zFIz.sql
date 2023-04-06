-- 
-- depends: 

CREATE TYPE provider_type AS ENUM ('open_banking', 'monzo');
CREATE TYPE transaction_state AS ENUM ('pending', 'booked');

CREATE TABLE IF NOT EXISTS banks
(
    id serial NOT NULL,
    name character varying NOT NULL,
    external_id character varying NOT NULL,
    active_requisition_id character varying,
    provider_type provider_type NOT NULL,
    activation_email_sent boolean NOT NULL DEFAULT false,
    CONSTRAINT banks_pkey PRIMARY KEY (id),
    CONSTRAINT external_id_unique_key UNIQUE (external_id)
);

CREATE TABLE IF NOT EXISTS accounts
(
    id serial NOT NULL,
    bank_id integer NOT NULL,
    name character varying NOT NULL,
    external_id character varying,
    CONSTRAINT accounts_pkey PRIMARY KEY (id),
    CONSTRAINT account_unique_id UNIQUE (bank_id, external_id),
    CONSTRAINT bank_foreign_key FOREIGN KEY (bank_id)
        REFERENCES banks (id)
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
);

CREATE TABLE IF NOT EXISTS transactions
(
    id character varying NOT NULL,
    booking_time timestamp without time zone NOT NULL,
    remittance_info character varying NOT NULL,
    transaction_code character varying,
    currency character varying NOT NULL,
    source_currency character varying,
    source_amount money,
    amount numeric NOT NULL,
    exchange_rate double precision,
    source_data jsonb NOT NULL,
    state transaction_state NOT NULL,
    account_id integer NOT NULL,
    sequence_number integer NOT NULL,
    CONSTRAINT transactions_pkey PRIMARY KEY (id),
    CONSTRAINT account_id_foreign_key FOREIGN KEY (account_id)
        REFERENCES accounts (id)
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
        NOT VALID
);