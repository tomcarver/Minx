Minx (Programming language)
===

NB: Minx is currently under development, i.e. not working.
Currently Minx can be parsed, but not validated or run.

### Goals:

- Maintainability (quick to refactor, hard to accidentally break)
- Readable but opinionated (good code easy to read, bad code hard)
- Dependency injection built in
- Ease/Speed of Learning (i.e. planning for high language turnover)
- Ease of refactoring

### Paradigms

- OOP without classes, inheritance, exceptions, events...
- Encourage functional approach, permit imperative approach
- Opt-out immutability and referential transparency
- Declarative subset (Minx Scope/Object Notation?)
- Static, Structural typing
- Algebraic data types, hopefully made accessible
- Minimalism in constructs
- Case insensitive

### Quick Reference:

## Overview

    # Scopes
    #----------------------------------------------
    # The fundamental data structure in Minx is the scope - a free-form version
    # of the "map" or "data structure" or "object" concepts in other languages.
    # A scope can be declared as
    # 1) comma separated name declarations/assignments, delimited by braces

    person = {firstName, surname}
    me = {firstName = "Tom", surname = "Carver"}

    # 2) an indented block after "=" or ":"

    another_person = 
      firstName
      surname

    me_again =
      firstName = "Tom"
      surname = "Carver"

    # 3) or a source-file like this one! To this point, a scope of type
    # {me, person, me_again, another_person} has been declared.

    # The "type" of a scope is also a scope (person and another_person are valid
    # types for both me_again and me). In fact any scope can be used as a type, 
    # with any values being used as defaults. The "as" and "hide" keywords 
    # are used for compile-time casts ("as" hides any names not specified). 
    # Scopes can be combined.

    a_to_e = {a = 1, b = 2, f = 4} as {a,b, c = 3, d = 4, e = 5}
    a_and_e = a_to_e hide {b,c,d}

    # Declarations can specify types, but most of the time it shouldn't be
    # necessary - the compiler should just work it out.

    myBrother_again person = {firstName string= "Hywel"} as me

    # Case / Union data types
    #----------------------------------------------
    # All other values are "atoms" - e.g. the strings we saw above.
    # "Symbols" are used to specify semantic data:

    reasonForFailure = `file_not_found

    # Minx also has union data types that allow for a given symbol to contain
    # multiple different types of data, while still ensuring type safety.

    list = `empty_list
         | {hd, tl list}

    # The above line defines a recursive type that is either an "empty list"
    # symbol or a scope defining a head and a tail.
    # We work with this data structure using a case expression. Here's a 
    # function for getting the item at an index in our list data structure:

    item = case list
           | {hd, tl} : case index
                        | 0: hd 
                        | else: item ({oldIndex = index} as {list = tl, index = oldIndex - 1})
           | else : `invalid_index

    5thItem = item {list = someList, index = 4}

    # This example will raise lots of questions to do with the way we just 
    # defined that function that I'll get onto soon.
    # The essentials to concentrate on are:
    # 1) The parameter "list" had multiple valid types, so we used a case
    #    expression to "pattern-match" the type we were interested in.
    # 2) In the first clause of the case, we have another case expression,
    #    this time on the "index" parameter, where we match the value only.
    # 3) Both "case" expressions specify an "else" to be used if none of the
    #    other clauses match. If "else" is omitted and pattern-matching is
    #    not exhaustive, the initial expression is returned instead (i.e. the
         symbol `empty_list would be returned instead of `invalid_index)

    # This example also shows well how symbols and union types are used to 
    # communicate failure of operations rather than exceptions.

    # The plan is to introduce a meta system where you can specify your own 
    # types as patterns for matching tokens. Then (e.g.) ints, floats,
    # imaginary numbers can be implemented via regexes matching "2", "2.0"
    # and "1.5_2.0i" respectively.

    # Functions
    #----------------------------------------------
    # Functions are just data structures with un-met dependencies. It is not
    # necessary to specify the parameters a function takes because these vary
    # depending on the way a function is being used. For example in the previous
    # examples, we have used the following symbols:
    #   0,1,2,3,4, string, -
    # In most other languages, these would be hard-coded dependencies. Not in
    # Minx - they are all parameters that need to be bound separately.

    # In practise no-one will lose any sleep over the "hard-coding" in these 
    # examples; but OOP has a big problem with this more generally. We are 
    # encouraged to start by grouping functionality into classes first, and so
    # off the bat we decide what data will be a field, what will be a 
    # parameter, what will be static etc. When these decisions are re-made, a 
    # lot of code needs to be re-written as a result.

    # Here is the much more flexible Minx equivalent:

    interface =
      function1
      function2
      function3 = function1

    functionSet = 
      function1 = ...
      function2 = ...

    fields = 
      field1
      field2
      field3 = "default"

    instance = (functionSet
      ({field1 = "mmm", field2 = ""} as fields))
      as interface



    # Operators
    #------------------------------------------
    # To implement infix operators, we start with the Haskell system:
    # A function whose name consists solely of special characters is an
    # infix operator. The operands are supplied as the names "lhs" and "rhs":

    + = case lhs
        | {hd, tl} : {old_tl= tl} as {tl = old_tl + rhs} as lhs
        | else : rhs

    plus = +
  
    using_op = [1,2,3] + [4,5,6]
    not_using_op = plus {lhs= [1,2,3], rhs= [4,5,6]}

    # Operator precedence is a messy issue. Can't live with it, can't live 
    # without it. To keep things simple, all operators in Minx are 
    # left-associative, and precedence is determined purely on the characters
    # making up the operator, with shorter operators having greater precedence
    # over longer ones (+ higher than ++). Function application 
    # (right-associative) is last. In decreasing precedence: ^*/%+-:><=&| 

    # equals 4:
    would_equal_10_in_C = 5 + 4 - 2 + 3

    equals_2 = 10 - 2 ^ 5 / 4 * 8 + 7

## Shelved

- Meta
- A theory of overloading - non-deterministic values?

## Alphabet:
    = assignment (mutable or immutable) (or as part of infix operators)
    : control flow (case) (or as part of infix operators)
    | divide case clauses/ union type clauses (or as part of infix operators)
    , list/scope dividers
    {} scope delimiters
    [] list delimiters
    () grouping
    " strings delimiters
    ' compile expression delimiters (meta)
    ! mutability
    ~ side effects on execution (results = function~ params)
    ` symbol
    @ member-access (person@name)
    # comments
    $ the current scope

    _a-zA-Z0-9?.  valid non-operator name characters
    ^*/%+-:><=&|   valid operator characters

    £;\           currently unused

## BNF:

    comment = "#", read-to-end-of-line

    source-file = whole-file-scope
    expression = group | meta | name | explicit-scope | list-value | "$" | case
           | function-application | operator-application | member-access | cast

    group = "(", union, ")"
    meta = "'", expression-to-compile, "'"
    union = expression, { "|", expression }

    name = operator-name | non-operator-name
    operator-name = block of ^*/%+-:><=&|
    non-operator-name = block of _a-zA-Z0-9?.!~

    string = """, any-sequence-other-than\", """   # {name} groups => function

    explicit-scope =   "{", [assign-or-declare, {"," , assign-or-declare}], "}"
    implicit-scope =   indent, assign-or-declare, {new-line assign-or-declare}, unindent
    whole-file-scope = file-start, assign-or-declare, {new-line assign-or-declare}, file-end

    assign-or-declare = single-assign-or-declare | multiple-assign
    multiple-assign = explicit-scope, "=", scope-valued-expression
    single-assign-or-declare = declaration, ["=", (implict-scope | union)]
    declaration = name | typed-declaration
    typed-declaration = name, union

    list-value = "[" [union , { "," , union }] "]" # sugar for {hd, tl}

    case = "case", expression, { "|", pattern, ":", (implicit-scope | expression) }
    pattern = explicit-scope | typed-declaration | atom-valued-name | "else"

    function-application = function-valued-expression, scope-valued-expression
    operator-application = expression, operator-name, expression

    member-access = scope-valued-expression, "@", name

    # either of these acceptable as the last line of an indented scope
    cast = expression, "as", expression
         | expression, "hide", scope-valued-expression


