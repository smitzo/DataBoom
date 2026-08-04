CREATE TABLE patients (
    id bigint PRIMARY KEY,
    medical_record_number text NOT NULL,
    first_name text NOT NULL,
    last_name text NOT NULL,
    gender text NOT NULL,
    blood_type text NOT NULL,
    age integer NOT NULL,
    insurance_provider text
);

CREATE TABLE encounters (
    id bigint PRIMARY KEY,
    patient_id bigint NOT NULL REFERENCES patients(id),
    diagnosis_code text NOT NULL,
    diagnosis text NOT NULL,
    status text NOT NULL,
    visit_at timestamp NOT NULL
);

CREATE TABLE vitals (
    id bigint PRIMARY KEY,
    patient_id bigint NOT NULL REFERENCES patients(id),
    heart_rate integer NOT NULL,
    systolic integer NOT NULL,
    diastolic integer NOT NULL,
    height_cm numeric(5, 1) NOT NULL,
    weight_kg numeric(5, 1) NOT NULL,
    recorded_at timestamp NOT NULL
);
