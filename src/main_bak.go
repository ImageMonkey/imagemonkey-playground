package main

import (
    "bufio"
	"fmt"
	"image"
	_ "image/jpeg"
	"io/ioutil"
	"log"
	"os"
    tf "github.com/tensorflow/tensorflow/tensorflow/go"
)


func printBestLabel(probabilities []float32, labelsFile string) (float32, string) {
	bestIdx := 0
	for i, p := range probabilities {
		if p > probabilities[bestIdx] {
			bestIdx = i
		}
	}
	// Found a best match, now read the string from the labelsFile where
	// there is one line per label.
	file, err := os.Open(labelsFile)
	if err != nil {
		log.Fatal(err)
	}
	defer file.Close()
	scanner := bufio.NewScanner(file)
	var labels []string
	for scanner.Scan() {
		labels = append(labels, scanner.Text())
	}
	if err := scanner.Err(); err != nil {
		log.Printf("ERROR: failed to read %s: %v", labelsFile, err)
	}
	// fmt.Printf("BEST MATCH: (%2.2f%% likely) %s\n", probabilities[bestIdx]*100.0, labels[bestIdx])
	// fmt.Printf("Result_Score_1: %2.2f%%,Result_Label_1:%s\n", probabilities[bestIdx]*100.0, labels[bestIdx])

	Result_Score_1 := (probabilities[bestIdx] * 100.0)
	// tempB := strconv.FormatFloat(float64(tempA), 'f', 3, 64)
	Result_Label_1 := labels[bestIdx]
	// mapD := map[string]string{"Result_Score_1": tempB, "Result_Label_1": tempC}
	// mapB, _ := json.Marshal(mapD)

	return Result_Score_1, Result_Label_1
}

// Given an image stored in filename, returns a Tensor which is suitable for
// providing the image data to the pre-defined model.
func makeTensorFromImageForInception(filename string) (*tf.Tensor, error) {
	const (
		// Some constants specific to the pre-trained model at:
		// https://storage.googleapis.com/download.tensorflow.org/models/inception5h.zip
		//
		// - The model was trained after with images scaled to 224x224 pixels.
		// - The colors, represented as R, G, B in 1-byte each were converted to
		//   float using (value - Mean)/Std.
		//
		// If using a different pre-trained model, the values will have to be adjusted.
		H, W = 299, 299
		Mean = 128//117
		Std  = 128//float32(1)
	)
	file, err := os.Open(filename)
	if err != nil {
		return nil, err
	}
	defer file.Close()
	img, _, err := image.Decode(file)
	if err != nil {
		return nil, err
	}
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
	// Thus, the shape is [1, 224, 224, 3]
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

func main() {

    const (
		// Path to a pre-trained inception model.
		// The two files are extracted from a zip archive as so:
		/*
		   curl -L https://storage.googleapis.com/download.tensorflow.org/models/inception5h.zip -o /tmp/inception5h.zip
		   unzip /tmp/inception5h.zip -d /tmp
		*/
		modelFile  = "/home/playground/training/models/output_graph.pb"
		labelsFile = "/home/playground/training/models/output_labels.txt"
		   //modelFile  = "/tmp/tensorflow_inception_graph.pb"
			//labelsFile = "/tmp/imagenet_comp_graph_label_strings.txt"

		// Image file to "recognize".
		testImageFilename = "/home/playground/cat5.jpg"
	)

	// Load the serialized GraphDef from a file.
	model, err := ioutil.ReadFile(modelFile)
	if err != nil {
		log.Fatal(err)
	}

	// Construct an in-memory graph from the serialized form.
	graph := tf.NewGraph()
	if err := graph.Import(model, ""); err != nil {
		log.Fatal(err)
	}

	// Create a session for inference over graph.
	session, err := tf.NewSession(graph, nil)
	if err != nil {
		log.Fatal(err)
	}
	defer session.Close()


	// Run inference on testImageFilename.
	// For multiple images, session.Run() can be called in a loop (and
	// concurrently). Furthermore, images can be batched together since the
	// model accepts batches of image data as input.
	tensor, err := makeTensorFromImageForInception(testImageFilename)
	if err != nil {
		log.Fatal(err)
	}
	output, err := session.Run(
		map[tf.Output]*tf.Tensor{
			//graph.Operation("input").Output(0): tensor,
			graph.Operation("Mul").Output(0): tensor,
		},
		[]tf.Output{
			//graph.Operation("output").Output(0),
			graph.Operation("final_result").Output(0),
			
		},
		nil)
	if err != nil {
		log.Fatal(err)
	}

	// output[0].Value() is a vector containing probabilities of
	// labels for each image in the "batch". The batch size was 1.
	// Find the most probably label index.
	probabilities := output[0].Value().([][]float32)[0]
	_,label := printBestLabel(probabilities, labelsFile)
	fmt.Printf("Label = %s\n", label)
}