// Standalone native C++ test (no ESP-IDF or hardware required).
#include <cassert>
#include <cstring>
#include <string>
#include <vector>
#include <iostream>
#include "../components/muse/muse_tts_chunk.h"

static void check(const std::string &input, size_t limit) {
    size_t pos = 0;
    std::string restored;
    size_t segments = 0;
    while (pos < input.size()) {
        const size_t end = muse_tts_chunk_end(input.c_str(), pos, limit);
        assert(end > pos && end <= input.size());
        assert(end - pos <= limit);
        if (end < input.size()) {
            assert((static_cast<unsigned char>(input[end]) & 0xc0) != 0x80);
        }
        restored.append(input, pos, end - pos);
        pos = end;
        ++segments;
        assert(segments <= input.size());
    }
    assert(restored == input);
    if (input.empty()) assert(muse_tts_chunk_end(input.c_str(), 0, limit) == 0);
}

int main() {
    check("", 700);
    check("Hello Muse.", 700);
    check(std::string(4000, 'a'), 700);
    check(std::string(9000, 'x'), 700);
    std::string english;
    for (int i = 0; i < 600; ++i) english += "One. Two! Three? ";
    check(english, 700);
    std::string mixed;
    for (int i = 0; i < 500; ++i) mixed += "繁體中文測試 日本語こんにちは café 🚀 ";
    check(mixed, 700);
    check(mixed, 128);
    check(mixed, 4);
    assert(muse_tts_chunk_end("Hello", 0, 3) == 0);
    std::cout << "PASS: lossless UTF-8 chunking, sizes, order and boundaries\n";
}
