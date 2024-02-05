import yaml

import gitops.utils.kube as kube

template = """
apiVersion: batch/v1
kind: Job
metadata:
  name: {{ name }}
  labels:
    app: {{ app }}
spec:
  backoffLimit: 1
  activeDeadlineSeconds: 39600 # 60 * 60 * 11 (11 hours.)
  # https://kubernetes.io/docs/concepts/workloads/controllers/job/#ttl-mechanism-for-finished-jobs
  ttlSecondsAfterFinished: 100 # 100 seconds after a job is done/failed. Delete it
  template:
    metadata:
      name: {{ name }}
      labels:
        app: {{ app }}
    spec:
      restartPolicy: Never
      containers:
      - name: command
        image: "{{ image }}"
        command: {{ command }}
        tty: true
        stdin: true
"""


class TestRenderTemplate:
    def test_render_template_with_app_values(self):
        values = {
            "name": "name",
            "app": "app",
            "image": "image",
            "command": "command",
            "extra": "extra",
        }

        rendered_template = kube.render_template(template, values, None)

        assert yaml.safe_load(rendered_template) == yaml.safe_load(
            """
apiVersion: batch/v1
kind: Job
metadata:
  name: name
  labels:
    app: app
spec:
  backoffLimit: 1
  activeDeadlineSeconds: 39600 # 60 * 60 * 11 (11 hours.)
  # https://kubernetes.io/docs/concepts/workloads/controllers/job/#ttl-mechanism-for-finished-jobs
  ttlSecondsAfterFinished: 100 # 100 seconds after a job is done/failed. Delete it
  template:
    metadata:
      name: name
      labels:
        app: app
    spec:
      restartPolicy: Never
      containers:
      - name: command
        image: "image"
        command: command
        tty: true
        stdin: true
"""
        )

    def test_render_template_with_extra_labels(self):
        values = {
            "name": "name",
            "app": "app",
            "image": "image",
            "command": "command",
            "extra": "extra",
        }

        rendered_template = kube.render_template(template, values, extra_labels={"uptick/fargate": "true"})

        assert yaml.safe_load(rendered_template) == yaml.safe_load(
            """
apiVersion: batch/v1
kind: Job
metadata:
  name: name
  labels:
    app: app
spec:
  backoffLimit: 1
  activeDeadlineSeconds: 39600 # 60 * 60 * 11 (11 hours.)
  # https://kubernetes.io/docs/concepts/workloads/controllers/job/#ttl-mechanism-for-finished-jobs
  ttlSecondsAfterFinished: 100 # 100 seconds after a job is done/failed. Delete it
  template:
    metadata:
      name: name
      labels:
        uptick/fargate: "true"
        app: app
    spec:
      restartPolicy: Never
      containers:
      - name: command
        image: "image"
        command: command
        tty: true
        stdin: true
"""
        )

    def test_render_template_with_extra_resources(self):
        values = {
            "name": "name",
            "app": "app",
            "image": "image",
            "command": "command",
            "extra": "extra",
        }

        rendered_template = kube.render_template(
            template,
            values,
            container_resources={
                "limits": {"cpu": "1000m", "memory": "2000Mi"},
                "requests": {"cpu": "1000m", "memory": "2000Mi"},
            },
        )

        expected = yaml.safe_load(
            """
apiVersion: batch/v1
kind: Job
metadata:
  name: name
  labels:
    app: app
spec:
  backoffLimit: 1
  activeDeadlineSeconds: 39600 # 60 * 60 * 11 (11 hours.)
  # https://kubernetes.io/docs/concepts/workloads/controllers/job/#ttl-mechanism-for-finished-jobs
  ttlSecondsAfterFinished: 100 # 100 seconds after a job is done/failed. Delete it
  template:
    metadata:
      name: name
      labels:
        app: app
    spec:
      restartPolicy: Never
      containers:
      - name: command
        image: "image"
        command: command
        tty: true
        stdin: true
        resources:
          limits:
            cpu: 1000m
            memory: 2000Mi
          requests:
            cpu: 1000m
            memory: 2000Mi
"""
        )

        output = yaml.safe_load(rendered_template)

        assert expected == output
