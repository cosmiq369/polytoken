WITH inputs AS (
 SELECT 'samudra' AS company, chat_id, turn, role AS part, lang FROM company_systems.samudra__chats
 UNION ALL
 SELECT company, '__system__', 0, 'system_prompt', language FROM company_systems.samudra__bot_config
 UNION ALL
 SELECT 'swara' AS company, chat_id, turn, role AS part, lang FROM company_systems.swara__chats
 UNION ALL
 SELECT company, '__system__', 0, 'system_prompt', language FROM company_systems.swara__bot_config
 UNION ALL
 SELECT 'raitu' AS company, chat_id, turn, role AS part, lang FROM company_systems.raitu__chats
 UNION ALL
 SELECT company, '__system__', 0, 'system_prompt', language FROM company_systems.raitu__bot_config
 UNION ALL
 SELECT 'paisa' AS company, chat_id, turn, role AS part, lang FROM company_systems.paisa__chats
 UNION ALL
 SELECT company, '__system__', 0, 'system_prompt', language FROM company_systems.paisa__bot_config
), reference_coverage AS (
 SELECT lang_variant, COUNT(*) AS reference_sentences
 FROM company_systems.reference__sentences GROUP BY lang_variant
), price_coverage AS (
 SELECT COUNT(*) AS price_rows FROM polytoken_reference.prices
)
SELECT i.company, n.tokenizer_spec, i.part,
 COUNT(*) AS paired_items, SUM(n.tokens) AS native_tokens, SUM(e.tokens) AS english_tokens,
 CAST(SUM(n.tokens) AS DOUBLE) / SUM(e.tokens) AS native_to_english_ratio,
 r.reference_sentences AS native_reference_sentences,
 er.reference_sentences AS english_reference_sentences, p.price_rows
FROM inputs i
JOIN company_systems.measurements__latest_token_counts n
 ON n.company=i.company AND n.chat_id=i.chat_id AND n.turn=i.turn AND n.part=i.part AND n.lang_variant=i.lang
JOIN company_systems.measurements__latest_token_counts e
 ON e.company=n.company AND e.chat_id=n.chat_id AND e.turn=n.turn AND e.part=n.part
 AND e.tokenizer_spec=n.tokenizer_spec AND e.run_id=n.run_id AND e.lang_variant='en'
JOIN reference_coverage r ON r.lang_variant=i.lang
JOIN reference_coverage er ON er.lang_variant='en'
CROSS JOIN price_coverage p
GROUP BY i.company, n.tokenizer_spec, i.part, r.reference_sentences, er.reference_sentences, p.price_rows
ORDER BY i.company, n.tokenizer_spec, i.part
