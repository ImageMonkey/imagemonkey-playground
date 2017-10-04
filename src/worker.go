package main

import (
	"encoding/json"
	log "github.com/sirupsen/logrus"
	"os"
)

// Job holds the attributes needed to perform unit of work.
type Job struct {
	PredictionRequest PredictionRequest
}

// NewWorker creates takes a numeric id and a channel w/ worker pool.
func NewWorker(id int, workerPool chan chan Job) Worker {
	return Worker{
		id:         id,
		jobQueue:   make(chan Job),
		workerPool: workerPool,
		quitChan:   make(chan bool),
	}
}

type Worker struct {
	id         int
	jobQueue   chan Job
	workerPool chan chan Job
	quitChan   chan bool
}

func (w Worker) start() {
	log.Debug("[Worker] Worker %d starting", w.id)
	//const (
		// Path to the pre-trained model and the labels file
	//	modelFile  = "/home/playground/training/models/graph.pb"
	//	labelsPath = "/home/playground/training/models/labels.txt"
	//)
	predictor := NewTensorflowPredictor()
	predictor.Load("/home/playground/training/models/")

	go func() {
		for {
			// Add my jobQueue to the worker pool.
			w.workerPool <- w.jobQueue

			select {
			case job := <-w.jobQueue:
				// Dispatcher has added a job to my jobQueue.
				tfResult, err := predictor.Predict(job.PredictionRequest.Filename)
				if err == nil {
					redisConn := redisPool.Get()

					var predictionResult PredictionResult
					predictionResult.Uuid = job.PredictionRequest.Uuid
					predictionResult.Result = tfResult
					predictionResult.ModelInfo = predictor.modelInfo

					serialized, err := json.Marshal(predictionResult)
					if err != nil{
						log.Debug("[Worker] Couldn't marshal prediction result: %s", err.Error())
					} else {
						//store result with an expiration time of 1hr...it doesn't make sense to store it longer
						//than that.
						_, err = redisConn.Do("SETEX", ("predict" + job.PredictionRequest.Uuid), 3600, serialized)
						if err != nil {
							log.Debug("[Worker] Couldn't set marshal result: %s", err.Error())
						} else { //successfully predicted, remove file
							err = os.Remove(job.PredictionRequest.Filename)
							if err != nil {
								log.Debug("[Worker] Couldn't remove file %s", err.Error())
							}
						}
					}
				} else {
					log.Debug("[Worker] Couln't predict: %s", err.Error())
				}

				

			case <-w.quitChan:
				// We have been asked to stop.
				log.Debug("[Worker] Worker %d stopping", w.id)
				return
			}
		}
	}()
}

func (w Worker) stop() {
	go func() {
		w.quitChan <- true
	}()
}

// NewDispatcher creates, and returns a new Dispatcher object.
func NewDispatcher(jobQueue chan Job, maxWorkers int) *Dispatcher {
	workerPool := make(chan chan Job, maxWorkers)

	return &Dispatcher{
		jobQueue:   jobQueue,
		maxWorkers: maxWorkers,
		workerPool: workerPool,
	}
}

type Dispatcher struct {
	workerPool chan chan Job
	maxWorkers int
	jobQueue   chan Job
}

func (d *Dispatcher) run() {
	for i := 0; i < d.maxWorkers; i++ {
		worker := NewWorker(i+1, d.workerPool)
		worker.start()
	}

	go d.dispatch()
}

func (d *Dispatcher) dispatch() {
	for {
		select {
		case job := <-d.jobQueue:
			go func() {
				//fmt.Printf("fetching workerJobQueue for: %s\n", job.id)
				workerJobQueue := <-d.workerPool
				//fmt.Printf("adding %s to workerJobQueue\n", job.Name)
				workerJobQueue <- job
			}()
		}
	}
}

