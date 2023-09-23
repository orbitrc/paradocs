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

    /// \brief Enum with documentation.
    ///
    /// This enum class is for testing brief and detail
    /// descriptions.
    enum class DetailedEnum {
        /// \brief HTML is a markup language.
        Html,
        /// \brief CSS is a stylesheet language.
        Css,
        /// \brief JavaScript is a bad script language.
        JavaScript,
    };

public:
    void set_type(Type type);
};

} // namespace my

#endif /* _ENUM_TEST_H */
