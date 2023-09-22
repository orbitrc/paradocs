#ifndef _ENUM_TEST_H
#define _ENUM_TEST_H

#include <stdint.h>

namespace my {

class EnumTest
{
public:
    using CType = int32_t;

public:
    enum class Type {
        Boolean,
        Int,
        Float,
    };

public:
    void set_type(Type type);
};

} // namespace my

#endif /* _ENUM_TEST_H */
