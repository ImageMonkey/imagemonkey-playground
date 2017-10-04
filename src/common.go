package main

type TFResult struct {
    Label string `json:"label"`
    Score  float32 `json:"score"`
}

type PredictionRequest struct {
	Uuid string `json:"uuid"`
    Filename string `json:"filename"`
    Created int64 `json:"created"`
}

type PredictionResult struct {
    Uuid string `json:"uuid"`
    Result TFResult `json:"result"`
}