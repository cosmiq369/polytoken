CREATE SCHEMA IF NOT EXISTS samudra;
CREATE TABLE IF NOT EXISTS samudra.bot_config (
 company TEXT PRIMARY KEY, language TEXT NOT NULL, system_prompt_native TEXT NOT NULL,
 system_prompt_en TEXT NOT NULL, model_in_use TEXT NOT NULL, monthly_chats BIGINT NOT NULL,
 latency_target_s DOUBLE PRECISION NOT NULL, review_status TEXT NOT NULL DEFAULT 'pending',
 role TEXT, channel TEXT, current_model TEXT, dataset_version TEXT
);
ALTER TABLE samudra.bot_config ADD COLUMN IF NOT EXISTS role TEXT;
ALTER TABLE samudra.bot_config ADD COLUMN IF NOT EXISTS channel TEXT;
ALTER TABLE samudra.bot_config ADD COLUMN IF NOT EXISTS current_model TEXT;
ALTER TABLE samudra.bot_config ADD COLUMN IF NOT EXISTS dataset_version TEXT;
CREATE TABLE IF NOT EXISTS samudra.chats (
 chat_id TEXT NOT NULL, turn INTEGER NOT NULL CHECK (turn > 0),
 role TEXT NOT NULL CHECK (role IN ('user', 'assistant')), text_native TEXT NOT NULL,
 text_en TEXT NOT NULL, lang TEXT NOT NULL, review_status TEXT NOT NULL DEFAULT 'pending',
 PRIMARY KEY (chat_id, turn)
);
CREATE SCHEMA IF NOT EXISTS swara;
CREATE TABLE IF NOT EXISTS swara.bot_config (
 company TEXT PRIMARY KEY, language TEXT NOT NULL, system_prompt_native TEXT NOT NULL,
 system_prompt_en TEXT NOT NULL, model_in_use TEXT NOT NULL, monthly_chats BIGINT NOT NULL,
 latency_target_s DOUBLE PRECISION NOT NULL, review_status TEXT NOT NULL DEFAULT 'pending',
 role TEXT, channel TEXT, current_model TEXT, dataset_version TEXT
);
ALTER TABLE swara.bot_config ADD COLUMN IF NOT EXISTS role TEXT;
ALTER TABLE swara.bot_config ADD COLUMN IF NOT EXISTS channel TEXT;
ALTER TABLE swara.bot_config ADD COLUMN IF NOT EXISTS current_model TEXT;
ALTER TABLE swara.bot_config ADD COLUMN IF NOT EXISTS dataset_version TEXT;
CREATE TABLE IF NOT EXISTS swara.chats (
 chat_id TEXT NOT NULL, turn INTEGER NOT NULL CHECK (turn > 0),
 role TEXT NOT NULL CHECK (role IN ('user', 'assistant')), text_native TEXT NOT NULL,
 text_en TEXT NOT NULL, lang TEXT NOT NULL, review_status TEXT NOT NULL DEFAULT 'pending',
 PRIMARY KEY (chat_id, turn)
);
CREATE SCHEMA IF NOT EXISTS raitu;
CREATE TABLE IF NOT EXISTS raitu.bot_config (
 company TEXT PRIMARY KEY, language TEXT NOT NULL, system_prompt_native TEXT NOT NULL,
 system_prompt_en TEXT NOT NULL, model_in_use TEXT NOT NULL, monthly_chats BIGINT NOT NULL,
 latency_target_s DOUBLE PRECISION NOT NULL, review_status TEXT NOT NULL DEFAULT 'pending',
 role TEXT, channel TEXT, current_model TEXT, dataset_version TEXT
);
ALTER TABLE raitu.bot_config ADD COLUMN IF NOT EXISTS role TEXT;
ALTER TABLE raitu.bot_config ADD COLUMN IF NOT EXISTS channel TEXT;
ALTER TABLE raitu.bot_config ADD COLUMN IF NOT EXISTS current_model TEXT;
ALTER TABLE raitu.bot_config ADD COLUMN IF NOT EXISTS dataset_version TEXT;
CREATE TABLE IF NOT EXISTS raitu.chats (
 chat_id TEXT NOT NULL, turn INTEGER NOT NULL CHECK (turn > 0),
 role TEXT NOT NULL CHECK (role IN ('user', 'assistant')), text_native TEXT NOT NULL,
 text_en TEXT NOT NULL, lang TEXT NOT NULL, review_status TEXT NOT NULL DEFAULT 'pending',
 PRIMARY KEY (chat_id, turn)
);
CREATE SCHEMA IF NOT EXISTS paisa;
CREATE TABLE IF NOT EXISTS paisa.bot_config (
 company TEXT PRIMARY KEY, language TEXT NOT NULL, system_prompt_native TEXT NOT NULL,
 system_prompt_en TEXT NOT NULL, model_in_use TEXT NOT NULL, monthly_chats BIGINT NOT NULL,
 latency_target_s DOUBLE PRECISION NOT NULL, review_status TEXT NOT NULL DEFAULT 'pending',
 role TEXT, channel TEXT, current_model TEXT, dataset_version TEXT
);
ALTER TABLE paisa.bot_config ADD COLUMN IF NOT EXISTS role TEXT;
ALTER TABLE paisa.bot_config ADD COLUMN IF NOT EXISTS channel TEXT;
ALTER TABLE paisa.bot_config ADD COLUMN IF NOT EXISTS current_model TEXT;
ALTER TABLE paisa.bot_config ADD COLUMN IF NOT EXISTS dataset_version TEXT;
CREATE TABLE IF NOT EXISTS paisa.chats (
 chat_id TEXT NOT NULL, turn INTEGER NOT NULL CHECK (turn > 0),
 role TEXT NOT NULL CHECK (role IN ('user', 'assistant')), text_native TEXT NOT NULL,
 text_en TEXT NOT NULL, lang TEXT NOT NULL, review_status TEXT NOT NULL DEFAULT 'pending',
 PRIMARY KEY (chat_id, turn)
);
CREATE SCHEMA IF NOT EXISTS reference;
CREATE SCHEMA IF NOT EXISTS measurements;
CREATE TABLE IF NOT EXISTS reference.sentences (
 id TEXT NOT NULL, lang_variant TEXT NOT NULL, domain TEXT NOT NULL, kind TEXT NOT NULL,
 text TEXT NOT NULL, review TEXT NOT NULL, PRIMARY KEY (id, lang_variant)
);
CREATE TABLE IF NOT EXISTS reference.prices (
 model TEXT NOT NULL, provider TEXT NOT NULL, tokenizer_spec TEXT NOT NULL,
 input_per_mtok_usd NUMERIC, output_per_mtok_usd NUMERIC,
 source_url TEXT NOT NULL, fetched_at TIMESTAMPTZ NOT NULL, verified BOOLEAN NOT NULL,
 PRIMARY KEY (provider, model)
);
CREATE TABLE IF NOT EXISTS measurements.batches (
 run_id TEXT NOT NULL, company TEXT NOT NULL, tokenizer_spec TEXT NOT NULL,
 status TEXT NOT NULL CHECK (status IN ('completed', 'skipped', 'failed')),
 reason TEXT, rows_written INTEGER NOT NULL, started_at TIMESTAMPTZ NOT NULL,
 finished_at TIMESTAMPTZ NOT NULL, source_query TEXT NOT NULL, fetched_at TIMESTAMPTZ NOT NULL,
 PRIMARY KEY (run_id, company, tokenizer_spec)
);
CREATE TABLE IF NOT EXISTS measurements.token_counts (
 company TEXT NOT NULL, chat_id TEXT NOT NULL, turn INTEGER NOT NULL,
 part TEXT NOT NULL CHECK (part IN ('system_prompt', 'user', 'assistant')),
 tokenizer_spec TEXT NOT NULL, lang_variant TEXT NOT NULL,
 tokens INTEGER NOT NULL CHECK (tokens >= 0),
 fragment_rate DOUBLE PRECISION NOT NULL CHECK (fragment_rate >= 0 AND fragment_rate <= 1),
 run_id TEXT NOT NULL, measured_at TIMESTAMPTZ NOT NULL,
 source TEXT NOT NULL, source_query TEXT NOT NULL, fetched_at TIMESTAMPTZ NOT NULL,
 time_window_start TIMESTAMPTZ NOT NULL, time_window_end TIMESTAMPTZ NOT NULL,
 PRIMARY KEY (company, chat_id, turn, part, tokenizer_spec, lang_variant, run_id)
);
CREATE OR REPLACE VIEW measurements.latest_token_counts AS
 WITH ranked AS (
   SELECT *, ROW_NUMBER() OVER (PARTITION BY company, tokenizer_spec ORDER BY finished_at DESC, run_id DESC) AS position
   FROM measurements.batches
 )
 SELECT t.* FROM measurements.token_counts t
 JOIN ranked b ON t.run_id=b.run_id AND t.company=b.company AND t.tokenizer_spec=b.tokenizer_spec
 WHERE b.position=1 AND b.status='completed';
CREATE OR REPLACE VIEW public.samudra__bot_config AS SELECT * FROM samudra.bot_config;
CREATE OR REPLACE VIEW public.samudra__chats AS SELECT * FROM samudra.chats;
CREATE OR REPLACE VIEW public.swara__bot_config AS SELECT * FROM swara.bot_config;
CREATE OR REPLACE VIEW public.swara__chats AS SELECT * FROM swara.chats;
CREATE OR REPLACE VIEW public.raitu__bot_config AS SELECT * FROM raitu.bot_config;
CREATE OR REPLACE VIEW public.raitu__chats AS SELECT * FROM raitu.chats;
CREATE OR REPLACE VIEW public.paisa__bot_config AS SELECT * FROM paisa.bot_config;
CREATE OR REPLACE VIEW public.paisa__chats AS SELECT * FROM paisa.chats;
CREATE OR REPLACE VIEW public.reference__sentences AS SELECT * FROM reference.sentences;
CREATE OR REPLACE VIEW public.reference__prices AS SELECT * FROM reference.prices;
CREATE OR REPLACE VIEW public.measurements__batches AS SELECT * FROM measurements.batches;
CREATE OR REPLACE VIEW public.measurements__token_counts AS SELECT * FROM measurements.token_counts;
CREATE OR REPLACE VIEW public.measurements__latest_token_counts AS SELECT * FROM measurements.latest_token_counts;
