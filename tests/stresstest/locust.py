from locust import HttpLocust, TaskSet, task

class ClassifyImageBehavior(TaskSet):
    def on_start(self):
        pass

    @task(1)
    def predict(self):
        print "predict"
        self.client.post("/v1/predict")
        #r = self.client.post("/v1/predict", files={'image': 'dog.jpg'})


class Playground(HttpLocust):
    host = 'https://playground.imagemonkey.io'
    task_set = ClassifyImageBehavior
    min_wait = 5000
    max_wait = 9000