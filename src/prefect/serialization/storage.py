from typing import Any

from marshmallow import fields, post_load

from prefect.storage import (
    GCS,
    S3,
    Azure,
    Docker,
    Local,
    Storage,
    GitHub,
    GitLab,
    Bitbucket,
    CodeCommit,
    Webhook,
)
from prefect.utilities.serialization import JSONCompatible, ObjectSchema, OneOfSchema


class BaseStorageSchema(ObjectSchema):
    class Meta:
        object_class = Storage

    flows = fields.Dict(key=fields.Str(), values=fields.Str())
    secrets = fields.List(fields.Str(), allow_none=True)

    @post_load
    def create_object(self, data: dict, **kwargs: Any) -> Storage:
        flows = data.pop("flows", {})
        base_obj = super().create_object(data, **kwargs)
        base_obj.flows = flows
        return base_obj


class AzureSchema(BaseStorageSchema):
    class Meta:
        object_class = Azure

    container = fields.String(allow_none=False)
    blob_name = fields.String(allow_none=True)
    stored_as_script = fields.Bool(allow_none=True)


class DockerSchema(BaseStorageSchema):
    class Meta:
        object_class = Docker

    registry_url = fields.String(allow_none=True)
    image_name = fields.String(allow_none=True)
    image_tag = fields.String(allow_none=True)
    path = fields.Str(allow_none=True)
    stored_as_script = fields.Bool(allow_none=True)
    prefect_version = fields.String(allow_none=False)


class GCSSchema(BaseStorageSchema):
    class Meta:
        object_class = GCS

    bucket = fields.Str(allow_none=False)
    key = fields.Str(allow_none=True)
    project = fields.Str(allow_none=True)
    stored_as_script = fields.Bool(allow_none=True)


class LocalSchema(BaseStorageSchema):
    class Meta:
        object_class = Local

    directory = fields.Str(allow_none=False)
    path = fields.Str(allow_none=True)
    stored_as_script = fields.Bool(allow_none=True)

    @post_load
    def create_object(self, data: dict, **kwargs: Any) -> Storage:
        return super().create_object({"validate": False, **data}, **kwargs)


class S3Schema(BaseStorageSchema):
    class Meta:
        object_class = S3

    bucket = fields.String(allow_none=False)
    key = fields.String(allow_none=True)
    stored_as_script = fields.Bool(allow_none=True)
    client_options = fields.Dict(
        key=fields.Str(), values=JSONCompatible(), allow_none=True
    )


class GitHubSchema(BaseStorageSchema):
    class Meta:
        object_class = GitHub

    repo = fields.String(allow_none=False)
    ref = fields.String(allow_none=True)
    path = fields.String(allow_none=False)
    access_token_secret = fields.String(allow_none=True)


class GitLabSchema(BaseStorageSchema):
    class Meta:
        object_class = GitLab

    repo = fields.String(allow_none=False)
    path = fields.String(allow_none=True)
    host = fields.String(allow_none=True)
    ref = fields.String(allow_none=True)
    access_token_secret = fields.String(allow_none=True)


class BitbucketSchema(BaseStorageSchema):
    class Meta:
        object_class = Bitbucket

    project = fields.String(allow_none=False)
    repo = fields.String(allow_none=False)
    host = fields.String(allow_none=True)
    path = fields.String(allow_none=True)
    ref = fields.String(allow_none=True)
    access_token_secret = fields.String(allow_none=True)


class CodeCommitSchema(BaseStorageSchema):
    class Meta:
        object_class = CodeCommit

    repo = fields.String(allow_none=False)
    path = fields.String(allow_none=True)
    commit = fields.String(allow_none=True)
    client_options = fields.Dict(
        key=fields.Str(), values=JSONCompatible(), allow_none=True
    )


class WebhookSchema(BaseStorageSchema):
    class Meta:
        object_class = Webhook

    build_request_kwargs = fields.Dict(key=fields.Str, allow_none=False)
    build_request_http_method = fields.String(allow_none=False)
    get_flow_request_kwargs = fields.Dict(key=fields.Str, allow_none=False)
    get_flow_request_http_method = fields.String(allow_none=False)
    stored_as_script = fields.Bool(allow_none=True)


class StorageSchema(OneOfSchema):
    """
    Field that chooses between several nested schemas
    """

    # map class name to schema
    type_schemas = {
        "Azure": AzureSchema,
        "Docker": DockerSchema,
        "GCS": GCSSchema,
        "Local": LocalSchema,
        "Storage": BaseStorageSchema,
        "S3": S3Schema,
        "GitHub": GitHubSchema,
        "GitLab": GitLabSchema,
        "Bitbucket": BitbucketSchema,
        "CodeCommit": CodeCommitSchema,
        "Webhook": WebhookSchema,
    }
