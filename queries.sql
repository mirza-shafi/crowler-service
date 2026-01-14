-- View all content with key information
SELECT 
    id,
    source_type,
    source_identifier,
    title,
    word_count,
    is_indexed,
    crawl_timestamp,
    LEFT(text_content, 100) as content_preview
FROM content_manager
ORDER BY crawl_timestamp DESC;

-- Count by source type
SELECT 
    source_type, 
    COUNT(*) as count,
    SUM(word_count) as total_words
FROM content_manager
GROUP BY source_type;

-- View only file uploads
SELECT 
    id,
    title,
    source_identifier as filename,
    word_count,
    file_metadata->>'mime_type' as mime_type,
    crawl_timestamp
FROM content_manager
WHERE source_type = 'file'
ORDER BY crawl_timestamp DESC;

-- View only text entries
SELECT 
    id,
    title,
    source_identifier,
    word_count,
    LEFT(text_content, 200) as preview
FROM content_manager
WHERE source_type = 'text'
ORDER BY crawl_timestamp DESC;
