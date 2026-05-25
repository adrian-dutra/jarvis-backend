CREATE TABLE IF NOT EXISTS agenda_events (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    event_type VARCHAR(50) NOT NULL,
    subject VARCHAR(255),
    location VARCHAR(255),
    start_at TIMESTAMP NOT NULL,
    end_at TIMESTAMP,
    all_day BOOLEAN DEFAULT FALSE,
    recurrence_type VARCHAR(20) DEFAULT 'none',
    recurrence_weekdays VARCHAR(20),
    recurrence_until DATE,
    created_at TIMESTAMP DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'America/Campo_Grande'),
    updated_at TIMESTAMP DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'America/Campo_Grande')
);

CREATE INDEX IF NOT EXISTS idx_agenda_events_start_at ON agenda_events(start_at);
CREATE INDEX IF NOT EXISTS idx_agenda_events_event_type ON agenda_events(event_type);
CREATE INDEX IF NOT EXISTS idx_agenda_events_subject ON agenda_events(subject);
CREATE INDEX IF NOT EXISTS idx_agenda_events_recurrence_type ON agenda_events(recurrence_type);
