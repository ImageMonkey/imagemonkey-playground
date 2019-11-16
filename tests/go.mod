module github.com/bbernhard/imagemonkey-playground-tests

go 1.12

require (
	github.com/bbernhard/imagemonkey-playground/datastructures v0.0.0-00010101000000-000000000000
	github.com/go-resty/resty/v2 v2.1.0
	github.com/sirupsen/logrus v1.4.2
)

replace github.com/bbernhard/imagemonkey-playground/datastructures => ../src/datastructures
