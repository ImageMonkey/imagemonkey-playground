package tests

import (
	"bytes"
	datastructures "github.com/bbernhard/imagemonkey-playground/datastructures"
	"github.com/go-resty/resty/v2"
	"io/ioutil"
	"testing"
	"time"
)

func testPostGrabcut(t *testing.T, imageUuid string, pathToGrabcutMask string) string {
	url := "http://127.0.0.1:8079/v1/grabcut"

	imgBytes, err := ioutil.ReadFile(pathToGrabcutMask)
	ok(t, err)

	client := resty.New()
	resp, err := client.R().
		SetFileReader("image", "grabcut.png", bytes.NewReader(imgBytes)).
		SetFormData(map[string]string{
			"uuid": imageUuid,
		}).Post(url)

	ok(t, err)
	equals(t, resp.StatusCode(), 202) //request always succeeds with status code 202. grabcut processing happens asynchronously

	if _, ok := resp.Header()["Location"]; ok {
		h := resp.Header()["Location"]
		if len(h) == 1 {
			return h[0]
		}
		t.FailNow()
	}

	t.FailNow()
	return ""
}

type GrabcutMeResult struct {
	Result datastructures.GrabcutMeResult `json:"result"`
	Error  string                         `json:"error"`
}

func testGetGrabcut(t *testing.T, uuid string) GrabcutMeResult {
	var res GrabcutMeResult

	url := "http://127.0.0.1:8079/v1/grabcut/" + uuid

	client := resty.New()
	resp, err := client.R().
		SetResult(&res).
		Get(url)

	ok(t, err)
	equals(t, resp.StatusCode(), 200)

	return res
}

func testPostPredict(t *testing.T, predictionType string, pathToImage string) string {
	url := "http://127.0.0.1:8079/v1/predict"

	imgBytes, err := ioutil.ReadFile(pathToImage)
	ok(t, err)

	client := resty.New()
	resp, err := client.R().
		SetFileReader("image", "predict.png", bytes.NewReader(imgBytes)).
		Post(url)

	ok(t, err)
	equals(t, resp.StatusCode(), 202) //request always succeeds with status code 202. predict happens asynchronously

	if _, ok := resp.Header()["Location"]; ok {
		h := resp.Header()["Location"]
		if len(h) == 1 {
			return h[0]
		}
		t.FailNow()
	}

	t.FailNow()
	return ""
}

func testGetPredict(t *testing.T, uuid string) datastructures.PredictMeResult {
	var res datastructures.PredictMeResult

	url := "http://127.0.0.1:8079/v1/predict/" + uuid

	client := resty.New()
	resp, err := client.R().
		SetResult(&res).
		Get(url)

	ok(t, err)
	equals(t, resp.StatusCode(), 200)

	return res
}

func TestGrabcutFailsDueToNotExistingImage(t *testing.T) {
	uuid := testPostGrabcut(t, "not-existing.jpeg", "./images/grabcut/apple.png")
	
	//grabcut takes a few seconds
	time.Sleep(5 * time.Second)

	res := testGetGrabcut(t, uuid)
	equals(t, res.Error, "Couldn't process request (Image /home/imagemonkey-playground/donations/not-existing.jpeg doesn't exist!)")
}

func TestGrabcutSucceeds(t *testing.T) {
	uuid := testPostGrabcut(t, "apple1.jpeg", "./images/grabcut/apple.png")
	
	//grabcut takes a few seconds
	time.Sleep(5 * time.Second)

	res := testGetGrabcut(t, uuid)
	equals(t, res.Error, "")
	notEquals(t, len(res.Result.Points), 0)
}

func TestPredict(t *testing.T) {
	uuid := testPostPredict(t, "", "./images/apple1.jpeg")
	notEquals(t, uuid, "")

	//prediction takes a few seconds
	time.Sleep(5 * time.Second)

	predictionResult := testGetPredict(t, uuid)
	equals(t, predictionResult.Label, "apple")
}
