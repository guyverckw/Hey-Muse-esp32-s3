#pragma once

// Split UTF-8 text without dropping bytes or dividing a multi-byte codepoint.
// Returns the exclusive end of the next chunk. Keeps whitespace in the chunk
// it originally belonged to, so concatenation reproduces the original exactly.
// No heap allocation or dependencies on ESP-IDF.
#include <cstddef>
#include <cstring>

static inline size_t muse_tts_chunk_end(const char *text, size_t start,
                                         size_t max_bytes)
{
    if (!text || max_bytes < 4) return start;
    const size_t len = std::strlen(text);
    if (start >= len) return len;
    size_t end = len - start <= max_bytes ? len : start + max_bytes;
    if (end == len) return end;

    // The end points to the next byte. Retreat over UTF-8 continuation bytes,
    // leaving a whole codepoint for the following chunk.
    while (end > start && (static_cast<unsigned char>(text[end]) & 0xc0) == 0x80)
        --end;
    if (end == start) return start; // impossible for valid UTF-8 with max>=4

    // Prefer a natural boundary in the last 40% of the chunk. Include its
    // trailing whitespace/punctuation in this chunk; do not lose any bytes.
    const size_t lower = start + (end - start) * 3 / 5;
    for (size_t j = end; j > lower; --j) {
        const unsigned char c = static_cast<unsigned char>(text[j - 1]);
        if (c == ' ' || c == '\n' || c == '\r' || c == '\t' ||
            c == '.' || c == '!' || c == '?' || c == ',' || c == ';' || c == ':') {
            return j;
        }
    }
    return end;
}
