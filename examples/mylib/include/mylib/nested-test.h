#ifndef _NESTED_TEST_H
#define _NESTED_TEST_H

namespace my {

class Enclosing
{
public:
    class Nested
    {};

public:
    Enclosing();

    /// \brief Do something with `Nested` object.
    void do_something(const Nested& nested);

    /// \brief Create a `Nested` object.
    static Nested create_nested();
};

} // namespace my

#endif /* _NESTED_TEST_H */
