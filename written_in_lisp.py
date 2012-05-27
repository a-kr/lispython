# coding: lispython
(class MegaTest (object)
    (def __init__ (self a)
        (= self.items (range a (* a 2)))
    )
    (def inner_test (self)
        (= sq (lambda (x) (* x x)))
        (= bee (list))
        (for (i) self.items
            (bee.append (+ (sq i) (test_fun i 5)))
        )
        (return (sum bee))
    )
    (def test (self) (print (% "hello, world %d" (self.inner_test))) )
)
(def test_fun (a b)
    (if (> a b)
        ((print "greater")
         (return 1)
        )
        ((print "lesser") (return 0))
    )
)
(= megatest (MegaTest 4))

