from uuid import uuid4

import pendulum
import pydantic
import pytest
from fastapi import status

from prefect.server import models, schemas
from prefect.server.schemas import actions
from prefect.settings import PREFECT_EXPERIMENTAL_ENABLE_ARTIFACTS, temporary_settings


@pytest.fixture
async def artifact(flow_run, task_run, client):

    artifact_schema = actions.ArtifactCreate(
        key="voltaic",
        data=1,
        metadata_={"data": "opens many doors"},
        flow_run_id=flow_run.id,
        task_run_id=task_run.id,
    )
    response = await client.post(
        "/experimental/artifacts/", json=artifact_schema.dict(json_compatible=True)
    )
    assert response.status_code == status.HTTP_201_CREATED

    yield response.json()


@pytest.fixture
async def artifacts(flow_run, task_run, client):
    artifact1 = actions.ArtifactCreate(
        key="artifact-1", data=1, flow_run_id=flow_run.id, task_run_id=task_run.id
    ).dict(json_compatible=True)
    await client.post("/experimental/artifacts/", json=artifact1)

    artifact2 = actions.ArtifactCreate(
        key="artifact-2", flow_run_id=flow_run.id, task_run_id=task_run.id
    ).dict(json_compatible=True)
    await client.post("/experimental/artifacts/", json=artifact2)

    artifact3 = actions.ArtifactCreate(key="artifact-3", flow_run_id=flow_run.id).dict(
        json_compatible=True
    )
    await client.post("/experimental/artifacts/", json=artifact3)

    yield [artifact1, artifact2, artifact3]


@pytest.fixture(autouse=True)
def auto_enable_artifacts(enable_artifacts):
    """
    Enable artifacts for testing
    """
    assert PREFECT_EXPERIMENTAL_ENABLE_ARTIFACTS.value() is True


class TestEnableArtifactsFlag:
    async def test_flag_defaults_to_false(self):
        with temporary_settings(
            restore_defaults={PREFECT_EXPERIMENTAL_ENABLE_ARTIFACTS}
        ):
            assert PREFECT_EXPERIMENTAL_ENABLE_ARTIFACTS.value() is False

    async def test_404_when_flag_disabled(self, client):
        with temporary_settings(
            restore_defaults={PREFECT_EXPERIMENTAL_ENABLE_ARTIFACTS}
        ):
            response = await client.post(
                "/experimental/artifacts/", json=dict(key="black-lotus")
            )
            assert response.status_code == status.HTTP_404_NOT_FOUND


class TestCreateArtifact:
    async def test_create_artifact(self, flow_run, task_run, client):
        artifact = actions.ArtifactCreate(
            key="voltaic",
            data=1,
            metadata_={"data": "opens many doors"},
            flow_run_id=flow_run.id,
            task_run_id=task_run.id,
        ).dict(json_compatible=True)

        response = await client.post(
            "/experimental/artifacts/",
            json=artifact,
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["key"] == artifact["key"]
        assert response.json()["data"] == artifact["data"]
        assert response.json()["metadata_"] == artifact["metadata_"]
        assert response.json()["flow_run_id"] == str(flow_run.id)
        assert response.json()["task_run_id"] == str(task_run.id)

    async def test_create_artifact_raises_error_on_existing_key(
        self,
        artifact,
        client,
    ):

        data = actions.ArtifactCreate(
            key=artifact["key"],
            data=artifact["data"],
        ).dict(json_compatible=True)

        response = await client.post(
            "/experimental/artifacts/",
            json=data,
        )

        assert response.status_code == 409


class TestReadArtifact:
    async def test_read_artifact(self, artifact, client):
        artifact_id = artifact["id"]

        response = await client.get(f"/experimental/artifacts/{artifact_id}")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["key"] == artifact["key"]
        assert response.json()["data"] == artifact["data"]
        assert response.json()["metadata_"] == artifact["metadata_"]
        assert response.json()["flow_run_id"] == artifact["flow_run_id"]

    async def test_read_artifact_not_found(self, client):
        response = await client.get(f"/experimental/artifacts/{uuid4()}")
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestReadArtifacts:
    async def test_read_artifacts(self, artifacts, client):
        response = await client.post("/experimental/artifacts/filter")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) == 3

        assert {r["key"] for r in response.json()} == {a["key"] for a in artifacts}
        assert {r["data"] for r in response.json()} == {a["data"] for a in artifacts}
        assert {str(r["flow_run_id"]) for r in response.json()} == {
            a["flow_run_id"] for a in artifacts
        }

    async def test_read_artifacts_with_applies_filter(
        self, artifacts, flow_run, client
    ):
        artifact_filter = dict(
            artifacts=schemas.filters.ArtifactFilter(
                key=schemas.filters.ArtifactFilterKey(
                    any_=[artifacts[0]["key"], artifacts[1]["key"]]
                )
            ).dict(json_compatible=True)
        )
        response = await client.post(
            "/experimental/artifacts/filter", json=artifact_filter
        )
        assert response.status_code == status.HTTP_200_OK
        assert all(
            [item["flow_run_id"] == str(flow_run.id) for item in response.json()]
        )
        assert len(response.json()) == 2

    async def test_read_artifacts_with_flow_run_filter(
        self, artifacts, flow_run, client
    ):
        flow_run_filter = dict(
            artifacts=schemas.filters.ArtifactFilter(
                flow_run_id=schemas.filters.ArtifactFilterFlowRunId(any_=[flow_run.id])
            ).dict(json_compatible=True)
        )
        response = await client.post(
            "/experimental/artifacts/filter", json=flow_run_filter
        )
        assert response.status_code == status.HTTP_200_OK
        assert all(
            [item["flow_run_id"] == str(flow_run.id) for item in response.json()]
        )

    async def test_read_artifacts_with_task_run_filter(
        self, artifacts, task_run, client
    ):
        task_run_filter = dict(
            artifacts=schemas.filters.ArtifactFilter(
                task_run_id=schemas.filters.ArtifactFilterTaskRunId(any_=[task_run.id])
            ).dict(json_compatible=True)
        )
        response = await client.post(
            "/experimental/artifacts/filter", json=task_run_filter
        )
        assert response.status_code == status.HTTP_200_OK
        assert all(
            [item["task_run_id"] == str(task_run.id) for item in response.json()]
        )

    async def test_read_artifacts_with_multiple_filters(
        self, artifacts, flow_run, task_run, client
    ):
        multiple_filters = dict(
            artifacts=schemas.filters.ArtifactFilter(
                flow_run_id=schemas.filters.ArtifactFilterFlowRunId(any_=[flow_run.id]),
                task_run_id=schemas.filters.ArtifactFilterTaskRunId(any_=[task_run.id]),
            ).dict(json_compatible=True),
        )
        response = await client.post(
            "/experimental/artifacts/filter", json=multiple_filters
        )
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) == 2
        assert all(
            [item["flow_run_id"] == str(flow_run.id) for item in response.json()]
        )
        assert all(
            [item["task_run_id"] == str(task_run.id) for item in response.json()]
        )

    async def test_read_artifacts_with_limit(self, artifacts, client):
        response = await client.post(
            "/experimental/artifacts/filter", json={"limit": 1}
        )
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) == 1

    async def test_read_artifacts_with_offset(self, artifacts, client):
        response = await client.post(
            "/experimental/artifacts/filter",
            json={
                "offset": 1,
                "sort": schemas.sorting.ArtifactSort.KEY_DESC,
            },
        )
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) == 2
        assert [r["key"] for r in response.json()] == [
            artifacts[1]["key"],
            artifacts[0]["key"],
        ]
        assert [r["data"] for r in response.json()] == [
            artifacts[1]["data"],
            artifacts[0]["data"],
        ]
        assert [r["flow_run_id"] for r in response.json()] == [
            str(artifacts[1]["flow_run_id"]),
            str(artifacts[0]["flow_run_id"]),
        ]

    async def test_read_artifacts_with_sort(self, artifacts, client):
        response = await client.post(
            "/experimental/artifacts/filter",
            json=dict(sort=schemas.sorting.ArtifactSort.UPDATED_DESC),
        )
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) == 3
        assert [r["key"] for r in response.json()] == [
            artifacts[2]["key"],
            artifacts[1]["key"],
            artifacts[0]["key"],
        ]

    async def test_read_artifacts_returns_empty_list(self, client):
        response = await client.post("/experimental/artifacts/filter")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) == 0

    async def test_read_artifacts_with_applies_key_like_filter(
        self, artifacts, flow_run, client
    ):
        artifact_filter = dict(
            artifacts=schemas.filters.ArtifactFilter(
                key=schemas.filters.ArtifactFilterKey(like_=artifacts[0]["key"][:-1])
            ).dict(json_compatible=True)
        )
        response = await client.post(
            "/experimental/artifacts/filter", json=artifact_filter
        )
        assert response.status_code == status.HTTP_200_OK
        assert all(
            [item["flow_run_id"] == str(flow_run.id) for item in response.json()]
        )
        assert len(response.json()) == 3


class TestUpdateArtifact:
    async def test_update_artifact_succeeds(self, artifacts, client):
        response = await client.post("/experimental/artifacts/filter")
        now = pendulum.now("utc")
        assert response.status_code == status.HTTP_200_OK
        artifact_id = response.json()[0]["id"]
        artifact_key = response.json()[0]["key"]
        artifact_flow_run_id = response.json()[0]["flow_run_id"]

        response = await client.patch(
            f"/experimental/artifacts/{artifact_id}",
            json={"data": {"new": "data"}},
        )

        assert response.status_code == 204

        response = await client.get(f"/experimental/artifacts/{artifact_id}")
        updated_artifact = pydantic.parse_obj_as(schemas.core.Artifact, response.json())
        assert updated_artifact.data == {"new": "data"}
        assert updated_artifact.key == artifact_key
        assert str(updated_artifact.flow_run_id) == artifact_flow_run_id
        assert updated_artifact.created < now
        assert updated_artifact.updated > now

    async def test_update_artifact_does_not_update_if_fields_are_not_set(
        self, artifact, client
    ):
        now = pendulum.now("utc")
        artifact_id = artifact["id"]

        response = await client.patch(
            f"/experimental/artifacts/{artifact_id}",
            json={},
        )
        assert response.status_code == 204

        response = await client.get(f"/experimental/artifacts/{artifact_id}")
        updated_artifact = pydantic.parse_obj_as(schemas.core.Artifact, response.json())
        assert updated_artifact.data == artifact["data"]
        assert updated_artifact.key == artifact["key"]
        assert str(updated_artifact.flow_run_id) == artifact["flow_run_id"]
        assert updated_artifact.created < now
        assert updated_artifact.updated > now

    async def test_update_artifact_raises_error_if_artifact_not_found(
        self, artifacts, client
    ):
        response = await client.patch(
            f"/experimental/artifacts/{str(uuid4())}",
            json={"data": {"new": "data"}},
        )

        assert response.status_code == 404


class TestDeleteArtifact:
    async def test_delete_artifact_succeeds(self, artifact, session, client):
        artifact_id = artifact["id"]
        response = await client.delete(f"/experimental/artifacts/{artifact_id}")
        assert response.status_code == 204

        artifact = await models.artifacts.read_artifact(
            session=session, artifact_id=artifact_id
        )
        assert artifact is None

        response = await client.get(f"/experimental/artifacts/{artifact_id}")
        assert response.status_code == 404

    async def test_delete_artifact_returns_404_if_does_not_exist(self, client):
        response = await client.delete(f"/experimental/artifacts/{str(uuid4())}")
        assert response.status_code == 404
