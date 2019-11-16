module github.com/bbernhard/imagemonkey-playground/predict

go 1.12

require (
	github.com/bbernhard/imagemonkey-playground/datastructures v0.0.0-00010101000000-000000000000
	github.com/disintegration/imaging v1.6.1
	github.com/garyburd/redigo v1.6.0
	github.com/sirupsen/logrus v1.4.2
	github.com/tensorflow/tensorflow v2.0.0+incompatible
)

replace github.com/bbernhard/imagemonkey-playground/datastructures => ../datastructures
