CREATE TABLE IF NOT EXISTS learning_attempts (
    id SERIAL PRIMARY KEY,
    topic VARCHAR(255) NOT NULL,
    question TEXT NOT NULL,
    expected_answer TEXT NOT NULL,
    user_answer TEXT,
    classification VARCHAR(50),
    score DOUBLE PRECISION,
    feedback TEXT,
    created_at TIMESTAMP DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'America/Campo_Grande') NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_learning_attempts_topic ON learning_attempts(topic);
CREATE INDEX IF NOT EXISTS idx_learning_attempts_classification ON learning_attempts(classification);
CREATE INDEX IF NOT EXISTS idx_learning_attempts_created_at ON learning_attempts(created_at);
