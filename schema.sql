CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS ps_cleared_course_view (
    roll_number VARCHAR(15) NOT NULL,
    name VARCHAR(150) NOT NULL,
    vertical_name VARCHAR(150) NOT NULL,
    course_name VARCHAR(150) NOT NULL,
    date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    venue_name VARCHAR(150) NOT NULL,
    status VARCHAR(50) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_ps_status ON ps_cleared_course_view (status);
CREATE INDEX IF NOT EXISTS idx_ps_vertical ON ps_cleared_course_view (vertical_name);
CREATE INDEX IF NOT EXISTS idx_ps_course ON ps_cleared_course_view (course_name);
CREATE INDEX IF NOT EXISTS idx_ps_roll ON ps_cleared_course_view (roll_number);

-- Optional semantic-search index. Run embed_index.py after importing the data.
CREATE TABLE IF NOT EXISTS course_embeddings (
    id BIGSERIAL PRIMARY KEY,
    vertical_name TEXT NOT NULL,
    course_name TEXT NOT NULL,
    embedding VECTOR(384) NOT NULL,
    UNIQUE (vertical_name, course_name)
);
