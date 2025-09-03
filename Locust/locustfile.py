from locust import HttpUser, task, between

class HelloLambdaUser(HttpUser):
    wait_time = between(1, 3)  # seconds between requests

    @task
    def call_api(self):
        response = self.client.get("/")
        if response.status_code == 200:
            print("Success:", response.json())
        else:
            print("Failed with status:", response.status_code)
