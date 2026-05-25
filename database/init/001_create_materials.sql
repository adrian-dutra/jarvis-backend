CREATE TABLE IF NOT EXISTS materials (
    id SERIAL PRIMARY KEY,
    original_filename VARCHAR(255) NOT NULL,
    stored_filename VARCHAR(255) NOT NULL,
    subject VARCHAR(255),
    file_type VARCHAR(50),
    content_type VARCHAR(100),
    file_size BIGINT,
    file_path TEXT NOT NULL,
    extracted_text TEXT,
    indexed BOOLEAN DEFAULT FALSE,
    chunk_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'America/Campo_Grande'),
    updated_at TIMESTAMP DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'America/Campo_Grande')
);

CREATE TABLE IF NOT EXISTS material_chunks (
    id SERIAL PRIMARY KEY,
    material_id INTEGER NOT NULL REFERENCES materials(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    chunk_text TEXT NOT NULL,
    token_count INTEGER,
    created_at TIMESTAMP DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'America/Campo_Grande')
);

CREATE INDEX IF NOT EXISTS idx_materials_indexed ON materials(indexed);
CREATE INDEX IF NOT EXISTS idx_materials_subject ON materials(subject);
CREATE INDEX IF NOT EXISTS idx_material_chunks_material_id ON material_chunks(material_id);
