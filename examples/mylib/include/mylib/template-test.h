#ifndef _TEMPLATE_TEST_H
#define _TEMPLATE_TEST_H

#include <stdint.h>

#include <functional>

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

    /// \brief std::function param test.
    void call_function(std::function<void(int32_t)> func);
};

} // namespace my

#endif /* _TEMPLATE_TEST_H */
