#ifndef _TEMPLATE_TEST_H
#define _TEMPLATE_TEST_H

#include <stdint.h>

namespace my {

template <typename T, typename U, int32_t num>
class TemplateTest
{
public:
    /// \brief Default constructor.
    ///
    /// Construct a `TemplateTest` without arguments.
    TemplateTest();

    /// \brief Copy constructor.
    TemplateTest(const TemplateTest<T>& other);

    /// \brief Other template type test function.
    template <typename U>
    TemplateTest<U> template_function() const;
};

} // namespace my

#endif /* _TEMPLATE_TEST_H */
