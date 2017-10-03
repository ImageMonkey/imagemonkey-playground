from locust import HttpLocust, TaskSet, task

BASE_URL = "https://imagemonkey.io"

class ClassifyImageBehavior(TaskSet):
    def on_start(self):
        pass

    #def login(self):
    #    self.client.post("/login", {"username":"ellen_key", "password":"education"})

    @task(2)
    def index(self):
        self.client.get(BASE_URL)

    #@task(1)
    #def profile(self):
    #    self.client.get("/profile")

class Playground(HttpLocust):
    task_set = ClassifyImageBehavior
    min_wait = 5000
    max_wait = 9000