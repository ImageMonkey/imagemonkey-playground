module github.com/bbernhard/imagemonkey-playground/api

go 1.12

require (
	github.com/bbernhard/imagemonkey-playground/commons v0.0.0-00010101000000-000000000000
	github.com/garyburd/redigo v1.6.0
	github.com/gin-gonic/gin v1.4.0
	github.com/gofrs/uuid v3.2.0+incompatible
	github.com/sirupsen/logrus v1.4.2
	github.com/yrsh/simplify-go v0.0.0-20141205144220-b78647bd27f7
)

replace github.com/bbernhard/imagemonkey-playground/commons => ../commons
