package main

type TFResult struct {
    Label string `json:"label"`
    Score  float32 `json:"score"`
}

type ModelInfo struct {
	Build int32 `json:"build"`
    Created string `json:"created"`
    TrainedOn []string `json:"trained_on"`
    BasedOn string `json:"based_on"`
}

type PredictionRequest struct {
	Uuid string `json:"uuid"`
    Filename string `json:"filename"`
    Created int64 `json:"created"`
    Type string `json:"type"`
}

type PredictionResult struct {
    Uuid string `json:"uuid"`
    Result TFResult `json:"result"`
    ModelInfo ModelInfo `json:"model_info"`
}