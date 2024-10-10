from gitops.common.app import App, Chart

from .utils import create_test_yaml


class TestMakeImage:
    def test_direct_image(self):
        app = App(
            "test",
            deployments={
                "image": "I0",
                "chart": "https://github.com/uptick/workforce",
                "namespace": "rofl",
            },
        )
        assert app.values["image"] == "I0"

    def test_image_tag(self):
        app = App(
            "test",
            deployments={
                "images": {"template": "image-template-{tag}"},
                "chart": "https://uptick.com/uptick/workforce",
                "image-tag": "I0",
                "namespace": "rofl",
            },
        )
        assert app.values["image"] == "image-template-I0"

    def test_image_prefix_is_parsed_properly(self):
        app = App(
            "test",
            deployments={
                "images": {"template": "docker.io/uptick:{tag}"},
                "chart": "https://uptick.com/uptick/workforce",
                "image-tag": "qa-server-1asd1",
                "namespace": "rofl",
            },
        )
        assert app.image_prefix == "qa-server"

    def test_no_image_tag_is_valid(self):
        app = App(
            "test",
            deployments={"chart": "https://uptick.com/uptick/workforce", "namespace": "rofl"},
        )
        assert app.values.get("image") is None

    def test_image_tag_from_yaml(self):
        path = create_test_yaml()
        app = App("test", path)
        assert app.values["image"] == "template-tag-myimagetag"

    def test_images_key_deleted(self):
        path = create_test_yaml()
        app = App("test", path)
        assert "images" not in app.values


class TestChart:
    def test_string_git_chart_is_parsed_properly_as_git(self):
        chart = Chart("https://github.com/uptick/workforce")

        assert chart.type == "git"
        assert chart.git_repo_url == "https://github.com/uptick/workforce"
        assert chart.git_sha is None

    def test_git_repo_url_sha_is_parsed_properly(self):
        chart = Chart("https://github.com/uptick/workforce@123")

        assert chart.type == "git"
        assert chart.git_repo_url == "https://github.com/uptick/workforce"
        assert chart.git_sha == "123"

    def test_git_repo_config_is_parsed_properly(self):
        chart = Chart({"type": "git", "git_repo_url": "https://github.com/uptick/workforce@123"})

        assert chart.type == "git"
        assert chart.git_repo_url == "https://github.com/uptick/workforce"
        assert chart.git_sha == "123"

    def test_helm_repo_is_parsed_properly(self):
        chart = Chart(
            {
                "type": "helm",
                "helm_repo": "brigade",
                "helm_repo_url": "https://brigade",
                "helm_chart": "brigade/brigade",
                "version": "1.3.2",
            }
        )

        assert chart.type == "helm"
        assert chart.helm_repo_url == "https://brigade"
        assert chart.helm_chart == "brigade/brigade"
        assert chart.version == "1.3.2"

    def test_local_repo_is_parsed_properly(self):
        chart = Chart(
            {
                "type": "local",
                "path": ".",
            }
        )

        assert chart.type == "local"
        assert chart.path == "."

    def test_app_namespace_property(self):
        path = create_test_yaml()
        app = App("test", path, encode_secrets=True)

        assert app.namespace

    def test_app_encode_secrets_works(self):
        path = create_test_yaml()
        app = App("test", path, encode_secrets=True)

        assert app.secrets["SNAPE"] != "KILLS_DUMBLEDORE"

        app_decoded = App("test", path, encode_secrets=False)
        assert app_decoded.secrets["SNAPE"] == "KILLS_DUMBLEDORE"
