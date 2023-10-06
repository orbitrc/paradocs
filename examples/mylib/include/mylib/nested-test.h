#ifndef _NESTED_TEST_H
#define _NESTED_TEST_H

namespace my {

/// \brief An enclosing class to test the `Nested` class.
///
/// \since 0.1
class Enclosing
{
public:
    class Nested
    {};

public:
    Enclosing();

    /// \brief Do something with `Nested` object.
    ///
    /// \since 0.1
    /// \param nested A `Nested` object.
    ///
    /// This function do something but nobody knows what is the something.
    void do_something(const Nested& nested);

    /// \brief Paradocs multiple params test.
    ///
    /// \param a First.
    /// \param b Second.
    ///
    /// A sample documented function for multiple params.
    void params_test(int a, int b) const;

    /// \brief Create a `Nested` object.
    static Nested create_nested();
};

} // namespace my

#endif /* _NESTED_TEST_H */
