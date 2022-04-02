module github.com/bbernhard/imagemonkey-playground/api

go 1.12

require (
	github.com/bbernhard/imagemonkey-playground/datastructures v0.0.0-00010101000000-000000000000
	github.com/certifi/gocertifi v0.0.0-20191021191039-0944d244cd40 // indirect
	github.com/garyburd/redigo v1.6.0
	github.com/getsentry/raven-go v0.2.0
	github.com/gin-gonic/gin v1.7.0
	github.com/gofrs/uuid v3.2.0+incompatible
	github.com/modern-go/concurrent v0.0.0-20180306012644-bacd9c7ef1dd // indirect
	github.com/modern-go/reflect2 v1.0.1 // indirect
	github.com/pkg/errors v0.8.1 // indirect
	github.com/sirupsen/logrus v1.4.2
	github.com/yrsh/simplify-go v0.0.0-20141205144220-b78647bd27f7
)

replace github.com/bbernhard/imagemonkey-playground/datastructures => ../datastructures
