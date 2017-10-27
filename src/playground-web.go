package main

import (
	"fmt"
	"flag"
	"net/http"
    "github.com/gin-gonic/gin"
    log "github.com/sirupsen/logrus"
    "github.com/satori/go.uuid"
    "github.com/garyburd/redigo/redis"
    "time"
    "encoding/json"
    "os"
)


func main() {
	log.SetLevel(log.DebugLevel)

	releaseMode := flag.Bool("release", false, "Run in release mode")
	redisAddress := flag.String("redis-address", ":6379", "Address to the Redis server")
	redisMaxConnections := flag.Int("redis-max-connections", 50, "Max connections to Redis")
	predictionsDir := flag.String("predictions-dir", "../predictions/", "Location of the temporary saved images for predictions")

	flag.Parse()
	if(*releaseMode){
		fmt.Printf("[Main] Starting gin in release mode!\n")
		gin.SetMode(gin.ReleaseMode)
	}

	//creating predictions-dir if it not already exists
	//as predicitions are temporary the directory might not already exist (e.q if predictions are stored in /tmp and server reboots)
	if _, err := os.Stat(*predictionsDir); os.IsNotExist(err) {
		log.Debug("[Main] Creating directory for predictions as it doesn't exist")
		err := os.Mkdir(*predictionsDir, 0755)
		if err != nil {
			log.Debug("[Main] Couldn't create directory: ", err.Error())
			os.Exit(1)
		}
	}


	redisPool := redis.NewPool(func() (redis.Conn, error) {
		c, err := redis.Dial("tcp", *redisAddress)

		if err != nil {
			return nil, err
		}

		return c, err
	}, *redisMaxConnections)
	defer redisPool.Close()



	router := gin.Default()

	router.OPTIONS("/v1/predict", func(c *gin.Context) {
		c.Writer.Header().Set("Access-Control-Allow-Origin", "*")
	    c.Writer.Header().Set("Access-Control-Allow-Headers", "Content-Type, X-Requested-With, X-PINGOTHER, X-File-Name, Cache-Control")
	    c.Writer.Header().Set("Access-Control-Allow-Methods", "POST, OPTIONS, GET, PUT")
	    c.JSON(http.StatusOK, struct{}{})
	})

	router.POST("/v1/predict", func(c *gin.Context) {
		c.Writer.Header().Set("Access-Control-Allow-Origin", "*")
	    c.Writer.Header().Set("Access-Control-Allow-Headers", "Content-Type, X-Requested-With, X-PINGOTHER, X-File-Name, Cache-Control")
	    c.Writer.Header().Set("Access-Control-Allow-Methods", "POST, OPTIONS, GET, PUT")
	    c.Writer.Header().Set("Access-Control-Expose-Headers" ,"Location")

	    classificationType := c.PostForm("classification_type")

	    _, header, err := c.Request.FormFile("image")
		if(err != nil){
			c.JSON(400, gin.H{"error": "Picture is missing"})
			return
		}

		uuid := uuid.NewV4().String()
		c.SaveUploadedFile(header, (*predictionsDir + uuid))

		redisConn := redisPool.Get()
		defer redisConn.Close()

		//add a prediction request to the REDIS 'predictme' queue
		var predictionRequest PredictionRequest		
		predictionRequest.Uuid = uuid
		predictionRequest.Created = int64(time.Now().Unix())
		predictionRequest.Filename = (*predictionsDir + uuid)

		if classificationType == "nsfw" {
			predictionRequest.Type = "nsfw-classification"
		} else {
			predictionRequest.Type = "classification"
		}

		serialized, err := json.Marshal(predictionRequest)
		if err != nil {
			log.Debug("[Predicting] Couldn't accept request: ", err.Error())
			c.JSON(500, gin.H{"error": "Couldn't accept request - please try again later"})
			return
		}

		_, err = redisConn.Do("RPUSH", "predictme", serialized)
		if err != nil {
			log.Debug("[Predicting] Couldn't accept request: ", err.Error())
			c.JSON(500, gin.H{"error": "Couldn't accept request - please try again later"})
			return
		}

		c.Writer.Header().Set("Location", uuid)
		c.JSON(202, gin.H{})
	})

	router.GET("/v1/predict/:uuid", func(c *gin.Context) {
		c.Writer.Header().Set("Access-Control-Allow-Origin", "*")
	    c.Writer.Header().Set("Access-Control-Allow-Headers", "Content-Type, X-Requested-With, X-PINGOTHER, X-File-Name, Cache-Control")
	    c.Writer.Header().Set("Access-Control-Allow-Methods", "POST, OPTIONS, GET, PUT")

	    uuid := c.Param("uuid")
	    key := "predict" + uuid

	    redisConn := redisPool.Get()
		defer redisConn.Close()

		ok, err := redis.Bool(redisConn.Do("EXISTS", key))
	    if err != nil{
	    	log.Debug("[Predicting] Couldn't check status of request: ", err.Error())
			c.JSON(500, gin.H{"error": "Couldn't check status of request - please try again later"})
			return	
	    }

	    if(!ok) { //nothing available yet. Which means either the uuid is wrong or processing isn't finished. 
	    		  //at this point we don't care for the reason.
	    	c.JSON(200, gin.H{})
	    	return
	    }


	    var data []byte
	    var predictionResult PredictionResult
    	data, err = redis.Bytes(redisConn.Do("GET", key))
    	if err != nil{
    		log.Debug("[Predicting] Couldn't get status of request: ", err.Error())
			c.JSON(500, gin.H{"error": "Couldn't get status of request - please try again later"})
			return	
    	}

    	err = json.Unmarshal(data, &predictionResult)
    	if err != nil{
    		log.Debug("[Predicting] Couldn't unmarshal: ", err.Error())
			c.JSON(500, gin.H{"error": "Couldn't get status of request - please try again later"})
			return	
    	}

    	c.JSON(http.StatusOK, gin.H{"label": predictionResult.Result.Label, "score": predictionResult.Result.Score, 
    								"model_info": predictionResult.ModelInfo})
	})


	router.Run(":8081")
}