package main

import (
    "bufio"
	"fmt"
	"image"
	_ "image/jpeg"
	_ "image/png"
	_ "image/gif"
	"io/ioutil"
	log "github.com/sirupsen/logrus"
	"os"
    tf "github.com/tensorflow/tensorflow/tensorflow/go"
    "mime/multipart"
    "github.com/disintegration/imaging"
    "flag"
    "github.com/garyburd/redigo/redis"
    "encoding/json"
    "time"
)

 	

type Predictor interface {
    Load(modelPath string, labelPath string) error
    Predict(file multipart.File) (TFResult, error)
    Close()
}

type TensorflowPredictor struct {
    labels []string
    graph *tf.Graph
    session *tf.Session
    modelInfo ModelInfo
}

func NewTensorflowPredictor() *TensorflowPredictor {
    return &TensorflowPredictor{} 
}

func (p *TensorflowPredictor) Load(basePath string) error{
	//read model info file
	modelInfoFile, err := ioutil.ReadFile((basePath + "model_info.json"))
    if err != nil {
        log.Debug("[Main] Couldn't read model info: ", err.Error())
        return err
	}

	var modelInfo ModelInfo
	err = json.Unmarshal(modelInfoFile, &modelInfo)
	if err != nil {
		log.Debug("[Main] Couldn't parse model info: ", err.Error())
		return err
	}
	p.modelInfo = modelInfo


	//read labels file
	labels, err := loadLabels((basePath + "labels.txt"))
	if err != nil {
		log.Debug("[Main] Couldn't get labels: ", err.Error())
		return err
	}
	p.labels = labels

    // Load the serialized GraphDef from a file.
	model, err := ioutil.ReadFile((basePath + "graph.pb"))
	if err != nil {
		log.Debug("[Main] Couldn't read model: ", err.Error())
		return err
	}

	// Construct an in-memory graph from the serialized form.
	p.graph = tf.NewGraph()
	if err := p.graph.Import(model, ""); err != nil {
		log.Debug("[Main] Couldn't construct graph: ", err.Error())
		return err
	}

	// Create a session for inference over graph.
	p.session, err = tf.NewSession(p.graph, nil)
	if err != nil {
		log.Debug("[Main] Couldn't start session: ", err.Error())
		return err
	}

	return nil
}


func (p *TensorflowPredictor) Predict(file string) (TFResult, error){
	var res TFResult
	res.Label = "";
	res.Score = 0;
	// For multiple images, session.Run() can be called in a loop (and
	// concurrently). Furthermore, images can be batched together since the
	// model accepts batches of image data as input.
	tensor, err := makeTensorFromImage(file)
	if err != nil {
		log.Debug("[Predicting Image Label] Couldn't create tensor from image: ", err.Error())
		return res, err
	}
	output, err := p.session.Run(
		map[tf.Output]*tf.Tensor{
			//graph.Operation("input").Output(0): tensor,
			p.graph.Operation("Mul").Output(0): tensor,
		},
		[]tf.Output{
			//graph.Operation("output").Output(0),
			p.graph.Operation("final_result").Output(0),
			
		},
		nil)
	if err != nil {
		log.Debug("[Predicting Image Label] Couldn't run image prediction: ", err.Error())
		return res, err
	}

	// output[0].Value() is a vector containing probabilities of
	// labels for each image in the "batch". The batch size was 1.
	// Find the most probably label index.
	probabilities := output[0].Value().([][]float32)[0]
	res = getBestLabel(probabilities, p.labels)
	return res, nil
}

func (p *TensorflowPredictor) Close(){
	p.session.Close()
}


func loadLabels(path string) ([]string, error){
	var labels []string
	file, err := os.Open(path)
	if err != nil {
		log.Debug("[Loading Labels] Couldn't open file: ", err)
		return labels, err
	}
	defer file.Close()
	scanner := bufio.NewScanner(file)
	for scanner.Scan() {
		labels = append(labels, scanner.Text())
	}
	if err := scanner.Err(); err != nil {
		log.Debug("[Loading Labels] Failed to read labels file: ", err.Error())
		return labels, err
	}

	return labels, nil
}

func getBestLabel(probabilities []float32, labels []string) TFResult{
	var result TFResult
	bestIdx := 0
	for i, p := range probabilities {
		if p > probabilities[bestIdx] {
			bestIdx = i
		}
	}

	result.Score = (probabilities[bestIdx] * 100.0)
	result.Label = labels[bestIdx]

	return result
} 

// Given an image, returns a Tensor which is suitable for
// providing the image data to the pre-defined model.
func makeTensorFromImage(file string) (*tf.Tensor, error) {
	const (
		// Some constants specific to the pre-trained model. 
		// - The model was trained with images scaled to 299x299 pixels.
		// - Mean = 128 
		// - Std = 128
		//
		// All values taken from retrain.py
		// If using a different model, the values will have to be adjusted.
		H, W = 299, 299
		Mean = 128
		Std  = 128
	)

	f, err := os.Open(file)
    if err != nil {
        panic(err.Error())
    }
    defer f.Close()

	img, _, err := image.Decode(f)
	if err != nil {
		return nil, err
	}

	//resize image to 299x299 (= size the model was trained on)
	//the image resize library in use might be slow when larger images are used
	//-> (see https://github.com/fawick/speedtest-resize for comparison)
	//Consider using a different image resizing library (but in that case we probably
	//need to write the image first to disk and read the resized image afterwards. 
	//Is that faster?)
	img = imaging.Resize(img, W, H, imaging.Box)

	sz := img.Bounds().Size()
	if sz.X != W || sz.Y != H {
		return nil, fmt.Errorf("input image is required to be %dx%d pixels, was %dx%d", W, H, sz.X, sz.Y)
	}

	// 4-dimensional input:
	// - 1st dimension: Batch size (the model takes a batch of images as
	//                  input, here the "batch size" is 1)
	// - 2nd dimension: Rows of the image
	// - 3rd dimension: Columns of the row
	// - 4th dimension: Colors of the pixel as (B, G, R)
	// Thus, the shape is [1, 299, 299, 3]
	var ret [1][H][W][3]float32
	for y := 0; y < H; y++ {
		for x := 0; x < W; x++ {
			px := x + img.Bounds().Min.X
			py := y + img.Bounds().Min.Y
			r, g, b, _ := img.At(px, py).RGBA()
			ret[0][y][x][0] = float32((int(b>>8) - Mean)) / Std
			ret[0][y][x][1] = float32((int(g>>8) - Mean)) / Std
			ret[0][y][x][2] = float32((int(r>>8) - Mean)) / Std
		}
	}
	return tf.NewTensor(ret)
}

var redisPool *redis.Pool

func main() {
	log.SetLevel(log.DebugLevel)

	log.Debug("[Main] Starting Playground Worker...")
	redisAddress := flag.String("redis-address", ":6379", "Address to the Redis server")
	redisMaxConnections := flag.Int("redis-max-connections", 10, "Max connections to Redis")
	maxWorkerQueueSize := flag.Int("max-worker-queue-size", 100, "The size of job queue")
	maxWorkers := flag.Int("max-workers", 5, "The number of workers to start")
	maxWorkersNSFW := flag.Int("max-workers-nsfw", 3, "The number of workers that operate on the NSFW model")

	flag.Parse()

	log.Debug("[Main] Starting ThreadPool...")

	redisPool = redis.NewPool(func() (redis.Conn, error) {
		c, err := redis.Dial("tcp", *redisAddress)

		if err != nil {
			return nil, err
		}

		return c, err
	}, *redisMaxConnections)
	defer redisPool.Close()

	log.Debug("[Main] Starting Dispatcher...")

	jobQueue := make(chan Job, *maxWorkerQueueSize)
	dispatcher := NewDispatcher(jobQueue, *maxWorkers, "/home/playground/training/models/")
	dispatcher.run()

	//NSFW job queue
	nsfwJobQueue := make(chan Job, *maxWorkerQueueSize)
	nsfwDispatcher := NewDispatcher(nsfwJobQueue, *maxWorkersNSFW, "/home/playground/training/models/nsfw/")
	nsfwDispatcher.run()


	for{
		var data []byte

		redisConn := redisPool.Get()

    	data, err := redis.Bytes(redisConn.Do("LPOP", "predictme"))
    	if err != nil {
    		redisConn.Close()
    		time.Sleep(time.Second) //nothing in queue, sleep for one sec
    		continue
    	}

    	log.Debug("[Main] Got a new request to process")

    	var predictionRequest PredictionRequest
    	err = json.Unmarshal(data, &predictionRequest)
    	if err != nil{
    		log.Debug("[Main] Couldn't unmarshal: ", err.Error())
    		redisConn.Close()
			continue
    	}

    	work := Job{PredictionRequest: predictionRequest}
    	if predictionRequest.Type == "classification" {
	    	jobQueue <- work
	    } else if predictionRequest.Type == "nsfw-classification" {
	    	nsfwJobQueue <- work
	    } else {
	    	log.Debug("[Main] Invalid classification type: ", predictionRequest.Type)
	    }

    	redisConn.Close()
	}


}