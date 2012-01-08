Readability
Dependency Injection
Ease/Speed of Learning
Encourage functional approach, permit imperative approach
declarative subset (MSON?)
Ease of refactoring

! mutability
~ side effects on execution
` symbol
¬ specifies a name that should *not* occur in a scope (i.e. because it would duplicate another)
= assignment
: control flow (case)
{} scope delimiters
[] list delimiters
() grouping
| divide case clauses
, list/scope dividers
@ member-access
# comments
" strings
$ the current scope
' compile expression (meta)

£;\
for names = _a-zA-Z0-9?.¬
for operators = *+-></^%&





comment = "#", read-to-end-of-line

#program = scope
expression = group | meta | atom-value | atom-type | case | union-type | scope | list-value | "$" | name | application | cast | member-access | operator-application

group = "(", expression, ")"
meta = "'", expression-to-compile, "'"

name = operator-name | non-operator-name
operator-name = block of *+-></^%&
non-operator-name = block of _a-zA-Z0-9?.!~¬

atom-value = int | decimal | string | symbol # bools are just symbols?
atom-type = "int" | "decimal" | "string" | "symbol"
symbol = "`", symbol-name
string = """, any-sequence-other-than\", """   # {name} groups turn it into a function

scope = "{", [assign-or-declare, {"," , assign-or-declare}], "}"
      | indent-after:or=, assign-or-declare, {new-line-at-same-initial-indentation assign-or-declare}, unindent
      | file-start, assign-or-declare, {new-line-with-no-indentation assign-or-declare}, file-end
assign-or-declare = single-assign-or-declare | multiple-assign
multiple-assign = "{", declaration, { "," , declaration}, "}", "=", scope-valued-expression
single-assign-or-declare = declaration, ["=", expression]
declaration = name | typed-declaration
typed-declaration = name, expression    # expression must not reduce to an atom-value

case = "case", expression, { "|", case-match, ":", expression } [ "|", "else", ":", expression ]   # case captures until a parent group is ended - unindent, ), }, ], etc
case-match = explicit-scope | typed-declaration | atom-value
union-type = case-type, {"|", case-type}
case-type = atom-valued-expression | atom-type-valued-expression | scope-valued-expression

list-value = "[" [expression , { "," , expression }] "]"    # type is just "list {itemType = __}
           | "[", int, "..", int, "]"     # sugar for int ranges.    # ???

application = expression, scope-valued-expression
operator-application = expression, operator-name, expression

member-access = scope-valued-expression, "@", name

# either of these acceptable as the last line of an indented scope
cast = expression, "as", expression   # scope declarations without values take values from the expression
     | expression, "hide", scope-valued-expression    # no values for scope declarations


while/for/lists or {head, tail}

case insensitive
Overloading is fudged by the integrator, but method names within a single namespace must be unique. 
Operator sugar: "1+2"  would essentially be   "plus {lhs: 1, rhs: 2}"
compile time metaprogramming...
generics = types that haven;t been supplied, even after usage
mutable values can only be bound to a scope if it reads it before writing to it.

method = function obj, result = method params    or   result = obj.method params


qsort = case list
    | {head, tail} :
        {matching, not-matching} = split {list = tail, condition = item < head}
        as (qsort {list = matching}) + ([middle] + qsort {list = not-matching})
    | else : `empty-list



functionWithSideEffects~ = 

me = {firstName = "Tom", surname = "Carver"}

me =
  firstName = "Tom"
  surname = "Carver"

currentUser = me as person   # compile time

functionWithValueBody = 4

functionWithScopeBody = [either of the me examples]

quadratic =
  sqrtDet = sqrt (b*b - 4*a*c)
  lowRoot = (-sqrtDet - b) / (2 * a)
  highRoot =  (sqrtDet - b) / (2 * a)
  as {lowRoot, highRoot}  # type
[or]
  hide {sqrtDet}   # type

{lowRoot,highRoot} = quadratic {a = 1, b = -2, c = 1}

case expression
    | {name, id} = do with object
    | val int = do with integer
    | else = do in fallthrough

case
    | expression = do on if
    | else = do on else

results = loop
    while~ = true
    do~ = case "var"
        | "var" = 5
        | else = 4

loop = case
    | while~ {} =
        head= do~ {}
        tail= loop {do~, while~}
    | else = `none

ValidRange=
  min _type
  max _type

# helper
times = (callback i) for i in [1..count]

isInRange = value <= max and value >= min

inRange = {value= 5}.isInRange {min= 3, max= 7}


import = [
  library = "Standard.dll"
  rules = [
    {import = "*"},
    {exclude = "System.StringHandling.UriEscaping"}
  ]
,
  library = "Alternative.dll"
  rules = [
    {exclude = "*"},
    {import = "Alternative.AlternativeUriEscaping"}
  ]
]

exclude = [
  namespaces = ["*"]
  rules = [{exclude = "*"}]
,
  namespaces = [
    "MyApp.Controller.*",
    "MyApp.UI.*",
    "MyApp.Logic.*",
    "MyApp.Database.*"
  ]
  rules = [{import = "*"}]
,
  namespaces = [
    "MyApp.UI.*",
    "MyApp.Logic.*",
    "MyApp.Database.*"
  ]
  rules = [{exclude = "MyApp.*"}]
,
  namespaces = ["MyApp.UI.*"]
  rules = [{import = "*"}]
,
  namespaces = ["MyApp.Logic.*"]
  rules = [{import = "*"}]
,
  namespaces = ["MyApp.Database.*"]
  rules = [{import = "*"}]
]


It is a compile error to specify rules in an order where later patterns are less specific than earlier patterns because of the effect on readability.


fields = 
  field1
  field2
  field3 = "default"

interface =
  method1
  method2
  method3 = method1

myClass = 
  method1 = function1
  method2 = function2
  as interface

instance = myClass
  field1 = "mmm"
  field2 = ""
  as fields




# static "methodMissing" that maps between two interfaces.
Interface1 = 
  name string,
  age int,
  address string

Interface2 = 
  getName -> string,
  getAge -> int,
  getAddress -> string

Interface1._methodName = ->
  return ~{ methodName.substring(3).toLower() }

Interface1.toString = 
  toString @obj


type = union-type | scope-type (some/none with values) | list-type | list-value


toString = case object
  | {atomic-value-string} : atomic-value
  | {atomic-type-name} : atomic-type-name
  | {union-type-
