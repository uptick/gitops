# type: ignore
from textwrap import dedent

from invoke import MockContext
from pytest import fixture

import gitops.utils.apps as apps
from gitops import core


@fixture(autouse=True)
def mock_invoke_run(monkeypatch):
    monkeypatch.setattr(core, "run", lambda cmd: None)


@fixture(autouse=True)
def mock_get_account_id(monkeypatch):
    monkeypatch.setattr(apps, "get_account_id", lambda: "UNKNOWN")


@fixture
def confirm_yes(monkeypatch):
    monkeypatch.setattr(apps, "confirm", lambda: True)


@fixture
def sample_app(tmp_path, monkeypatch):
    monkeypatch.setattr(apps, "get_apps_directory", lambda: tmp_path)
    (tmp_path / "sample_app").mkdir(parents=True, exist_ok=True)
    (tmp_path / "sample_app/deployment.yml").write_text("{}")
    (tmp_path / "sample_app/secrets.yml").write_text("{}")
    return tmp_path / "sample_app/"


class TestMixin:
    @fixture
    def deployment_yml(self, sample_app):
        def _deployment_yml(content):
            content = dedent(content)
            path = sample_app / "deployment.yml"
            path.write_text(content)
            self.original_content = content
            self.deployment_yml_path = path
            return path

        return _deployment_yml

    def deployment_yml_is_unchanged(self):
        return self.original_content == self.deployment_yml_path.read_text()


class TestSetEnv(TestMixin):
    def test_setenv_should_not_overwrite_if_there_is_existing_variable(
        self,
        deployment_yml,
        confirm_yes,
    ):
        file = deployment_yml(  # noqa: F841
            """\
            namespace: test
            chart: test
            environment:
              ANOTHER: WORLD
              HELLO: PARTNER
            """
        )
        core.setenv(MockContext(), filter="all", values="HELLO=WORLD")
        assert self.deployment_yml_is_unchanged()

    def test_setenv_should_add_to_existing_environment(
        self,
        deployment_yml,
        confirm_yes,
    ):
        file = deployment_yml(
            """\
            namespace: test
            chart: test
            environment:
              ANOTHER: WORLD
            """
        )
        core.setenv(MockContext(), filter="all", values="HELLO=WORLD")
        assert file.read_text() == dedent(
            """\
                namespace: test
                chart: test
                environment:
                  ANOTHER: WORLD
                  HELLO: WORLD
            """
        )

    def test_setenv_should_create_environment_if_missing(
        self,
        deployment_yml,
        confirm_yes,
    ):
        file = deployment_yml(
            """\
            namespace: test
            chart: test
            """
        )
        core.setenv(MockContext(), filter="all", values="HELLO=WORLD")
        assert file.read_text() == dedent(
            """\
                namespace: test
                chart: test
                environment:
                  HELLO: WORLD
            """
        )

    def test_setenv_should_normalise_environment_with_inconsistent_order(
        self,
        deployment_yml,
        confirm_yes,
    ):
        file = deployment_yml(  # noqa: F841
            """\
            namespace: test
            chart: test
            environment:
              HELLO: WORLD
              ANOTHER: WORLD
            """
        )
        core.setenv(MockContext(), filter="all", values="HELLO=WORLD")
        assert file.read_text() == dedent(
            """\
                namespace: test
                chart: test
                environment:
                  ANOTHER: WORLD
                  HELLO: WORLD
            """
        )


class TestUnsetEnv(TestMixin):
    def test_unset_environment_variable_removes_matching_variables(
        self,
        deployment_yml,
        confirm_yes,
    ):
        file = deployment_yml(
            """\
            namespace: test
            chart: test
            environment:
              HELLO: WORLD
              ANOTHER: WORLD
            """
        )
        core.unsetenv(MockContext(), filter="all", values="HELLO")
        assert file.read_text() == dedent(
            """\
                namespace: test
                chart: test
                environment:
                  ANOTHER: WORLD
            """
        )

    def test_unset_nonexistent_environment_variable(
        self,
        deployment_yml,
        confirm_yes,
    ):
        file = deployment_yml(  # noqa: F841
            """\
            namespace: test
            chart: test
            environment:
              ANOTHER: WORLD
            """
        )
        core.unsetenv(MockContext(), filter="all", values="HELLO")
        assert self.deployment_yml_is_unchanged()

    def test_emptying_environment_variable_should_remove_environment(
        self,
        deployment_yml,
        confirm_yes,
    ):
        file = deployment_yml(
            """\
            namespace: test
            chart: test
            environment:
              HELLO: WORLD
            """
        )
        core.unsetenv(MockContext(), filter="all", values="HELLO")
        assert file.read_text() == dedent(
            """\
                namespace: test
                chart: test
            """
        )

    def test_unsetenv_should_not_add_environment_if_missing(
        self,
        deployment_yml,
        confirm_yes,
    ):
        file = deployment_yml(
            """\
            namespace: test
            chart: test
            """
        )
        core.unsetenv(MockContext(), filter="all", values="HELLO")
        assert file.read_text() == dedent(
            """\
                namespace: test
                chart: test
            """
        )

    def test_normalizes_empty_environment_variable(
        self,
        deployment_yml,
        confirm_yes,
    ):
        file = deployment_yml(  # noqa: F841
            """\
            namespace: test
            chart: test
            environment: {}
            """
        )
        core.unsetenv(MockContext(), filter="all", values="HELLO")
        assert file.read_text() == dedent(
            """\
                namespace: test
                chart: test
            """
        )

    def test_preserve_null_environment_variable(
        self,
        deployment_yml,
        confirm_yes,
    ):
        file = deployment_yml(  # noqa: F841
            """\
            namespace: test
            chart: test
            environment: null
            """
        )
        core.unsetenv(MockContext(), filter="all", values="HELLO")
        assert file.read_text() == dedent(
            """\
                namespace: test
                chart: test
            """
        )
